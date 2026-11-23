"""Exploration du train et projections ACP/AFD, sans sélection sur test."""
import numpy as np
import pandas as pd
from scipy import stats
from sklearn.impute import SimpleImputer
from sklearn.preprocessing import StandardScaler
from sklearn.decomposition import PCA
from sklearn.discriminant_analysis import LinearDiscriminantAnalysis
from .data import NUMERIC,PAY
from .metrics import bh_adjust
from .storage import save

def exploratory(train,out):
    stats1=train[NUMERIC].describe(percentiles=[.25,.5,.75]).T
    stats1['variance']=train[NUMERIC].var(ddof=1)
    stats1['iqr']=stats1['75%']-stats1['25%']
    stats1['missing']=train[NUMERIC].isna().sum();stats1.to_csv(out/'univariate.csv',index_label='variable')
    cats=['SEX','EDUCATION','MARRIAGE',*PAY]
    counts=[];tests=[]
    for name in cats:
        table=pd.crosstab(train[name].astype(str),train.y).reindex(columns=[0,1],fill_value=0)
        chi,p,dof,expected=stats.chi2_contingency(table)
        good=bool((expected>=5).all())
        tests.append({'variable':name,'test':'chi_square','statistic':chi,'df':dof,'p_value':p if good else None,'expected_below_5':int((expected<5).sum()),'cramers_v':float(np.sqrt(chi/(table.to_numpy().sum()*min(table.shape[0]-1,table.shape[1]-1)))),'qualification':'asymptotic test' if good else 'small expected cells, p-value withheld'})
        for level,row in table.iterrows():counts.append({'variable':name,'level':level,'n':int(row.sum()),'defaults':int(row[1]),'rate':float(row[1]/row.sum())})
    for name in NUMERIC:
        a=train.loc[train.y==0,name].to_numpy();b=train.loc[train.y==1,name].to_numpy()
        stat,p=stats.ttest_ind(a,b,equal_var=False)
        pooled=np.sqrt(((len(a)-1)*a.var(ddof=1)+(len(b)-1)*b.var(ddof=1))/(len(a)+len(b)-2))
        tests.append({'variable':name,'test':'welch_t','statistic':float(stat),'p_value':float(p),'mean_nondefault':float(a.mean()),'mean_default':float(b.mean()),'standardized_difference':float((b.mean()-a.mean())/pooled),'qualification':'independent clients assumed; same-profile groups and historical selection limit interpretation'})
    samples=[g.LIMIT_BAL.to_numpy() for _,g in train.groupby('EDUCATION') if len(g)>=5]
    stat,p=stats.f_oneway(*samples,equal_var=False)
    tests.append({'variable':'LIMIT_BAL by EDUCATION','test':'welch_anova','statistic':float(stat),'p_value':float(p),'groups':len(samples),'qualification':'unequal variances allowed; no causal interpretation'})
    for family in ['chi_square','welch_t','welch_anova']:
        items=[t for t in tests if t['test']==family and t['p_value'] is not None]
        for item,adjusted in zip(items,bh_adjust([t['p_value'] for t in items])):item['p_adjusted_bh']=adjusted
    correlations={method:train[NUMERIC].corr(method=method).to_dict() for method in ['pearson','spearman']}
    for method in correlations:pd.DataFrame(correlations[method]).to_csv(out/(method+'.csv'))
    report={'scope':'Training split only; multiple-test correction within test families; associations not causes','rows':len(train),'univariate':stats1.reset_index(names='variable').to_dict('records'),'categorical':counts,'tests':tests,'correlations':correlations}
    save(out/'eda.json',report)
    return report

def projections(train,val,out,seed=42):
    imputer=SimpleImputer(strategy='median');scaler=StandardScaler()
    x=scaler.fit_transform(imputer.fit_transform(train[NUMERIC]));v=scaler.transform(imputer.transform(val[NUMERIC]))
    pca=PCA(svd_solver='full');z=pca.fit_transform(x);zv=pca.transform(v)
    lda=LinearDiscriminantAnalysis(solver='eigen',shrinkage='auto',n_components=1);l=lda.fit_transform(x,train.y);lv=lda.transform(v)
    reconstruction=pca.inverse_transform(z)
    assert np.allclose(x,reconstruction,rtol=1e-8,atol=1e-8)
    rng=np.random.default_rng(seed);indices=rng.choice(len(train),size=min(600,len(train)),replace=False)
    points=[{'pc1':float(z[i,0]),'pc2':float(z[i,1]),'lda1':float(l[i,0]),'y':int(train.y.iloc[i])} for i in indices]
    report={'fit_split':'train only','numeric_features':NUMERIC,'train_rows':len(train),'validation_rows':len(val),'explained_variance_ratio':pca.explained_variance_ratio_.tolist(),'components_for_90_percent':int(np.searchsorted(np.cumsum(pca.explained_variance_ratio_),.90)+1),'components':pca.components_.tolist(),'full_reconstruction_max_error':float(np.abs(reconstruction-x).max()),'lda_axes':int(l.shape[1]),'lda_class_means_train':{str(y):float(l[train.y.to_numpy()==y].mean()) for y in [0,1]},'lda_class_means_validation':{str(y):float(lv[val.y.to_numpy()==y].mean()) for y in [0,1]},'points':points,'sample_scope':'600 deterministic training points for display; no test projection fitted','qualification':'PCA on quantitative variables; AFD supervised single axis for binary target, not a 2D discriminant map'}
    save(out/'projections.json',report)
    return report
