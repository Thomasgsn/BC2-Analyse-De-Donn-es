"""Commandes reproductibles du BC2, artefacts datés et publication en dernier."""
import argparse,json,platform,time,os
from pathlib import Path
import importlib.metadata
import numpy as np,pandas as pd
from .storage import ROOT,save,now,digest,run_path

def run_pipeline(run_id):
    from .data import load_source,assign_splits,quality_report,NUMERIC,PAY,FEATURES
    from .analysis import exploratory,projections
    from .modeling import fit_compare
    from .market import acquire
    started=time.monotonic();out=run_path(run_id);out.mkdir(parents=True,exist_ok=False)
    save(out/'manifest.json',{'run_id':run_id,'status':'running','created_at_utc':now()})
    try:
        raw,frame=load_source();frame['split']=assign_splits(frame)
        quality=quality_report(raw,frame,frame['split']);save(out/'quality.json',quality)
        frame.to_parquet(out/'cohort.parquet',index=False)
        dictionary=[]
        for name in raw.columns:
            role='target' if name==raw.columns[-1] else 'identifier' if name=='ID' else 'feature'
            kind='quantitative' if name in NUMERIC else 'ordinal code with ambiguous special levels' if name in PAY else 'nominal category' if role=='feature' else role
            dictionary.append({'variable':name,'source_dtype':str(raw[name].dtype),'statistical_type':kind,'role':role,'used_in_model':name in FEATURES})
        pd.DataFrame(dictionary).to_csv(out/'dictionary.csv',index=False)
        subsets={s:frame.loc[frame.split==s].reset_index(drop=True) for s in ['train','validation','test']}
        print(json.dumps({'event':'prepared','run_id':run_id,'splits':quality['splits']}),flush=True)
        exploratory(subsets['train'],out);projections(subsets['train'],subsets['validation'],out)
        print(json.dumps({'event':'eda_and_projections_completed','scope':'train only'}),flush=True)
        models=fit_compare(subsets['train'],subsets['validation'],subsets['test'],out=out,modeldir=ROOT/'models'/run_id)
        print(json.dumps({'event':'models_completed','selection':models['selection'],'test':models['models'][models['selection']['selected']]['test']}),flush=True)
        acquire(out)
        manifest={'run_id':run_id,'status':'complete','finished_at_utc':now(),'elapsed_seconds':time.monotonic()-started,'python':platform.python_version(),'platform':platform.platform(),'seed':42,'threads':2,'versions':{p:importlib.metadata.version(p) for p in ['numpy','pandas','scipy','scikit-learn','dash','plotly','pyarrow','psutil','xlrd']},'files':{p.name:digest(p) for p in sorted(out.iterdir()) if p.is_file() and p.name!='manifest.json'}}
        save(out/'manifest.json',manifest);save(ROOT/'exports/latest.json',{'run_id':run_id,'manifest_sha256':digest(out/'manifest.json')})
        evidence=ROOT/'docs/evidence/pipeline'/run_id;evidence.mkdir(parents=True,exist_ok=False)
        for name in ['manifest','quality','eda','projections','models','market','selection-before-test']:
            source=out/(name+'.json');save(evidence/(name+'.json'),json.loads(source.read_text()))
        print(json.dumps({'event':'pipeline_complete','run_id':run_id,'elapsed_seconds':manifest['elapsed_seconds'],'selected':models['selection']['selected']}),flush=True)
    except BaseException as error:
        save(out/'failure.json',{'event':'pipeline_failed','error_type':type(error).__name__,'message':str(error),'at_utc':now(),'elapsed_seconds':time.monotonic()-started});raise

def main():
    p=argparse.ArgumentParser(description=__doc__);sub=p.add_subparsers(dest='command',required=True)
    a=sub.add_parser('run');a.add_argument('--run-id',required=True)
    sub.add_parser('health');sub.add_parser('acquire');sub.add_parser('evaluate-genai')
    m=sub.add_parser('macro');m.add_argument('--snapshot-id',required=True)
    args=p.parse_args()
    if args.command=='run':run_pipeline(args.run_id)
    elif args.command=='acquire':
        from .acquisition import acquire
        print(json.dumps(acquire()))
    elif args.command=='evaluate-genai':
        from .generation import evaluation
        r=evaluation();print(json.dumps({'event':'genai_evaluated','cases':len(r['cases']),'valid_llm':sum(c.get('valid',False) for c in r['cases'] if c['method']=='llm')}))
    elif args.command=='macro':
        from .macro import build
        r=build(args.snapshot_id);print(json.dumps({'event':'macro_built','snapshot_id':r['snapshot_id'],'series':[s['id'] for s in r['series']],'quarters':r['quarterly_common_period']['quarters']}))
    elif args.command=='health':
        from .storage import latest
        path,manifest=latest();print(json.dumps({'status':manifest['status'],'run_id':manifest['run_id']}))
if __name__=='__main__':main()
