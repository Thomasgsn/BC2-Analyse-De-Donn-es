"""Comparaison bornée et choix figé avant test, avec coûts et parité de relecture."""
import hashlib,json,time,resource
from pathlib import Path
import joblib,numpy as np,pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.pipeline import Pipeline
from sklearn.impute import SimpleImputer
from sklearn.preprocessing import StandardScaler,OneHotEncoder
from sklearn.linear_model import LogisticRegression
from sklearn.tree import DecisionTreeClassifier
from sklearn.ensemble import RandomForestClassifier
from sklearn.dummy import DummyClassifier
from sklearn.model_selection import StratifiedGroupKFold,cross_validate
from sklearn.calibration import calibration_curve
from threadpoolctl import threadpool_limits
from .data import NUMERIC,CATEGORICAL,FEATURES
from .metrics import binary_metrics,threshold_on_validation
from .storage import save,digest,now

def pipeline(model):
    numeric=Pipeline([('impute',SimpleImputer(strategy='median')),('scale',StandardScaler())])
    categorical=Pipeline([('impute',SimpleImputer(strategy='most_frequent')),('encode',OneHotEncoder(handle_unknown='ignore',sparse_output=False))])
    pre=ColumnTransformer([('numeric',numeric,NUMERIC),('categorical',categorical,CATEGORICAL)],remainder='drop')
    return Pipeline([('preprocess',pre),('model',model)])

def fit_compare(train,val,test,out,modeldir,seed=42):
    modeldir.mkdir(parents=True,exist_ok=False)
    cv=list(StratifiedGroupKFold(n_splits=3,shuffle=True,random_state=seed).split(train[FEATURES],train.y,train.group_id))
    for a,b in cv:assert set(train.group_id.iloc[a]).isdisjoint(set(train.group_id.iloc[b]))
    families={'logistic':[{'C':.1},{'C':1.0}], 'tree':[{'max_depth':4},{'max_depth':8}], 'forest':[{'max_depth':6},{'max_depth':12}]}
    def estimator(name,param):
        if name=='logistic':return LogisticRegression(**param,max_iter=1200,random_state=seed)
        if name=='tree':return DecisionTreeClassifier(**param,min_samples_leaf=30,random_state=seed)
        if name=='forest':return RandomForestClassifier(**param,n_estimators=80,min_samples_leaf=20,n_jobs=2,random_state=seed)
        return DummyClassifier(strategy='prior',random_state=seed)
    fits={};records={};trials=[]
    with threadpool_limits(limits=2):
        for family in ['dummy',*families]:
            start=time.monotonic();cpu=time.process_time();options=families.get(family,[{}]);evaluated=[]
            for param in options:
                if family=='dummy':mean=None;cv_record={}
                else:
                    scores=cross_validate(pipeline(estimator(family,param)),train[FEATURES],train.y,cv=cv,scoring={'ap':'average_precision','roc':'roc_auc'},n_jobs=1,return_train_score=True,error_score='raise')
                    mean=float(scores['test_ap'].mean());cv_record={k:v.tolist() for k,v in scores.items()};trials.append({'family':family,'parameters':param,'cv':cv_record})
                evaluated.append((mean if mean is not None else -1,param,cv_record))
            _,chosen,cv_record=max(evaluated,key=lambda r:r[0])
            fitted=pipeline(estimator(family,chosen));fitted.fit(train[FEATURES],train.y)
            if family=='forest':fitted.set_params(model__n_jobs=1)  # Somme des arbres dans un ordre fixe à l'inférence.
            score=fitted.predict_proba(val[FEATURES])[:,1];best,thresholds=threshold_on_validation(val.y,score)
            trainm=binary_metrics(train.y,fitted.predict_proba(train[FEATURES])[:,1],best['threshold'])
            fits[family]=fitted;records[family]={'parameters':chosen,'validation':best,'train':trainm,'validation_threshold_search':thresholds,'cv':cv_record,'fit_and_cv_wall_seconds':time.monotonic()-start,'cpu_seconds':time.process_time()-cpu,'memory_peak_mib_process':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss/1024,'inference_threads':1 if family=='forest' else None,'energy':'Not measured; CPU time and cumulative process peak memory are proxies, not CO2 measurements'}
        selected=max(records,key=lambda k:(records[k]['validation']['pr_auc_average_precision'],-records[k]['fit_and_cv_wall_seconds']))
        frozen={'selected':selected,'threshold':records[selected]['validation']['threshold'],'criterion':'Highest validation average precision; thresholds maximize F2 on validation; no test used','created_at_utc':now(),'seed':seed,'features':FEATURES}
        save(out/'selection-before-test.json',frozen);frozen_sha=digest(out/'selection-before-test.json')
        predictions=test[['ID','y','group_id','SEX','MARRIAGE']].copy()
        fairness={}
        for name,fitted in fits.items():
            threshold=records[name]['validation']['threshold'];score=fitted.predict_proba(test[FEATURES])[:,1]
            records[name]['test']=binary_metrics(test.y,score,threshold)
            records[name]['calibration']={'prediction_bin_mean':[],'observed_fraction':[]}
            true,mean=calibration_curve(test.y,score,n_bins=8,strategy='quantile')
            records[name]['calibration']={'prediction_bin_mean':mean.tolist(),'observed_fraction':true.tolist()}
            path=modeldir/(name+'.joblib');joblib.dump(fitted,path)
            restored=joblib.load(path);assert np.array_equal(score,restored.predict_proba(test[FEATURES])[:,1])
            records[name]['artifact']={'sha256':digest(path),'bytes':path.stat().st_size,'reload_predictions_exact':True}
            predictions[name+'_score']=score
            fairness[name]={str(level):binary_metrics(test.loc[idx,'y'],score[idx],threshold) for level in sorted(test.SEX.unique()) if (idx:=np.flatnonzero(test.SEX.to_numpy()==level)).size>=50}
        assert digest(out/'selection-before-test.json')==frozen_sha
    # Bootstrap de groupes sur le test : modèle et seuil fixés, pas de sélection.
    rng=np.random.default_rng(seed);groups=[g.index.to_numpy() for _,g in predictions.reset_index(drop=True).groupby('group_id')];boot=[]
    for _ in range(150):
        idx=np.concatenate([groups[i] for i in rng.integers(0,len(groups),size=len(groups))]);m=binary_metrics(test.y.to_numpy()[idx],predictions[selected+'_score'].to_numpy()[idx],frozen['threshold']);boot.append(m)
    ci={k:[float(np.quantile([v[k] for v in boot if v[k] is not None],q)) for q in [.025,.975]] for k in ['roc_auc','pr_auc_average_precision','recall','precision','f1']}
    predictions.to_parquet(out/'test-predictions.parquet',index=False)
    result={'selection':frozen,'selection_record_sha256':frozen_sha,'models':records,'trials':trials,'test_bootstrap_95_percent':{'method':'150 resamples of identical-input groups, fixed model and threshold','intervals':ci},'sex_group_audit':fairness,'excluded_sensitive_predictors':['SEX','MARRIAGE'],'qualification':'AGE retained; omission of two variables does not establish fairness. Historical snapshot, no temporal generalization proof. No stakeholder validation invented.'}
    save(out/'models.json',result)
    return result
