"""Contrat UCI350, catégories conservées et lots par empreinte sans fuite."""
from pathlib import Path
import hashlib,json
import numpy as np
import pandas as pd
from sklearn.model_selection import StratifiedGroupKFold
from .storage import ROOT,digest

SOURCE_SHA='30c6be3abd8dcfd3e6096c828bad8c2f011238620f5369220bd60cfc82700933'
NUMERIC=['LIMIT_BAL','AGE']+[f'BILL_AMT{i}' for i in range(1,7)]+[f'PAY_AMT{i}' for i in range(1,7)]
PAY=['PAY_0']+[f'PAY_{i}' for i in range(2,7)]
CATEGORICAL=['EDUCATION']+PAY
FEATURES=NUMERIC+CATEGORICAL
SOURCE_COLUMNS=['ID','LIMIT_BAL','SEX','EDUCATION','MARRIAGE','AGE']+PAY+[f'BILL_AMT{i}' for i in range(1,7)]+[f'PAY_AMT{i}' for i in range(1,7)]+['default payment next month']

def load_source(path=None):
    path=Path(path or ROOT/'data/raw/uci350-original.xls')
    if digest(path)!=SOURCE_SHA:raise ValueError('Empreinte du dataset inattendue ; pas de substitution silencieuse')
    raw=pd.read_excel(path,header=1,engine='xlrd')
    if list(raw.columns)!=SOURCE_COLUMNS or raw.shape!=(30000,25):raise ValueError('Schéma UCI350 inattendu')
    if raw.isna().any().any() or not np.isfinite(raw.to_numpy(dtype=float)).all():raise ValueError('Valeurs absentes/non finies inattendues dans la source verrouillée')
    if not raw.ID.is_unique or set(raw.iloc[:,-1].unique())!={0,1}:raise ValueError('Identifiants ou cible incohérents')
    frame=raw.rename(columns={'default payment next month':'y'}).copy()
    for name in ['ID','AGE','SEX','EDUCATION','MARRIAGE',*PAY,'y']:frame[name]=frame[name].astype('int64')
    frame['EDUCATION']=frame.EDUCATION.map({1:'graduate',2:'university',3:'high_school',4:'other'}).fillna('unknown_code')
    for name in PAY:frame[name]=frame[name].map(lambda value:f'code_{value}')
    # SEX et MARRIAGE sont réservés à la description/audit, exclus du modèle.
    group=frame[FEATURES].apply(lambda r:hashlib.sha256(json.dumps(r.tolist(),ensure_ascii=True,separators=(',',':')).encode()).hexdigest(),axis=1)
    frame['group_id']=group
    return raw,frame

def assign_splits(frame,seed=42):
    folds=np.full(len(frame),-1,dtype=int)
    splitter=StratifiedGroupKFold(n_splits=5,shuffle=True,random_state=seed)
    for fold,(_,holdout) in enumerate(splitter.split(frame[FEATURES],frame.y,frame.group_id)):folds[holdout]=fold
    result=pd.Series(np.where(folds==0,'test',np.where(folds==1,'validation','train')),index=frame.index,name='split')
    if (folds<0).any():raise AssertionError('Partition incomplète')
    check=pd.DataFrame({'group':frame.group_id,'split':result})
    if check.groupby('group')['split'].nunique().max()!=1:raise AssertionError('Groupe partagé entre lots')
    for label in ['train','validation','test']:
        y=frame.loc[result==label,'y']
        if len(y)<100 or y.value_counts().min()<20 or y.nunique()!=2:raise ValueError('Lot trop petit ou une classe absente')
    return result

def quality_report(raw,frame,splits):
    return {'source_sha256':SOURCE_SHA,'rows':len(frame),'source_columns':len(raw.columns),'source_explanatory_variables':23,'model_predictors':FEATURES,'excluded':['ID','SEX','MARRIAGE','y','group_id','split'],'target_counts':frame.y.value_counts().to_dict(),'default_rate':float(frame.y.mean()),'missing_raw_cells':int(raw.isna().sum().sum()),'negative_bill_cells':int((raw[[f'BILL_AMT{i}' for i in range(1,7)]]<0).sum().sum()),'extra_duplicates_without_id':int(raw.drop(columns='ID').duplicated().sum()),'unknown_education_codes':raw.loc[~raw.EDUCATION.isin([1,2,3,4]),'EDUCATION'].value_counts().to_dict(),'marriage_code_zero':int((raw.MARRIAGE==0).sum()),'rules':['No row removed; original preserved','EDUCATION 0/5/6 mapped to explicit unknown_code, raw retained','Repayment codes kept as nominal code labels without invented meaning','Negative bill amounts retained and counted, not presumed errors','SEX and MARRIAGE excluded from prediction, retained for audit','Groups are SHA256 of actual modeling inputs excluding target; no chronological interpretation of ID'],'splits':{s:{'rows':int((splits==s).sum()),'positives':int(frame.loc[splits==s,'y'].sum()),'groups':int(frame.loc[splits==s,'group_id'].nunique())} for s in ['train','validation','test']},'group_overlap':0,'scope':'One historical Taiwanese cohort, no temporal out-of-sample validation; teacher approval of changed target not provided'}
