"""Relire les modèles et artefacts réels, sans réentraîner ni régler sur test."""
import json
import numpy as np,pandas as pd,joblib
from rncp_bc2.storage import latest,digest,ROOT,save,now
from rncp_bc2.data import FEATURES
path,manifest=latest()
for name,sha in manifest['files'].items():assert digest(path/name)==sha,name
frame=pd.read_parquet(path/'cohort.parquet');test=frame.loc[frame.split=='test'].reset_index(drop=True);pred=pd.read_parquet(path/'test-predictions.parquet')
models=json.loads((path/'models.json').read_text());quality=json.loads((path/'quality.json').read_text());proj=json.loads((path/'projections.json').read_text())
assert len(frame)==30000 and len(test)==6000 and len(pred)==6000
assert frame.groupby('group_id').split.nunique().max()==1
assert digest(path/'selection-before-test.json')==models['selection_record_sha256']
assert not {'ID','SEX','MARRIAGE','y','split','group_id'}&set(FEATURES)
checks={}
for name,entry in models['models'].items():
    p=ROOT/'models'/manifest['run_id']/(name+'.joblib');assert digest(p)==entry['artifact']['sha256']
    model=joblib.load(p);score=model.predict_proba(test[FEATURES])[:,1]
    assert np.array_equal(score,pred[name+'_score'].to_numpy())
    assert pred.ID.tolist()==test.ID.tolist() and pred.y.tolist()==test.y.tolist()
    checks[name]={'rows':len(score),'scores_sha256':__import__('hashlib').sha256(score.tobytes()).hexdigest(),'exact':True}
assert proj['lda_axes']==1 and abs(sum(proj['explained_variance_ratio'])-1)<1e-9
assert sum(q['rows'] for q in quality['splits'].values())==len(frame)
market=pd.read_parquet(path/'market.parquet');assert len(market)==100 and market.date.is_unique
r={'at_utc':now(),'event':'real_pipeline_verified','run_id':manifest['run_id'],'all_manifest_files_verified':len(manifest['files']),'group_overlap':0,'models_reloaded':checks,'pca_variance_sum':sum(proj['explained_variance_ratio']),'lda_axes':1,'market_rows':len(market),'test_not_retuned':True}
save(ROOT/'docs/evidence/pipeline/runtime-verification.json',r);print(json.dumps(r))
