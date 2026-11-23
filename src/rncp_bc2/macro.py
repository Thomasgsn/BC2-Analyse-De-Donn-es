"""Contexte macro-économique du crédit : séries publiques FRED, sans jointure individuelle.

Les séries situent la période observée de la cohorte UCI (avril à septembre 2005)
dans un historique long. Elles ne sont jamais rattachées à un client.
"""
from pathlib import Path
import io,json,re,urllib.request
import numpy as np,pandas as pd
from .storage import ROOT,save,digest,now

FRED_URL='https://fred.stlouisfed.org/graph/fredgraph.csv?id={}'
COHORT_START,COHORT_END='2005-04-01','2005-09-30'
SERIES=[
    {'id':'DRCCLACBS','label':'Retards de paiement sur cartes de crédit (banques US)','unit':'% des encours','frequency':'trimestrielle','publisher':'Board of Governors of the Federal Reserve System'},
    {'id':'CORCCACBS','label':'Pertes sur cartes de crédit (banques US)','unit':'% annualisé des encours','frequency':'trimestrielle','publisher':'Board of Governors of the Federal Reserve System'},
    {'id':'TERMCBCCALLNS','label':'Taux d’intérêt des cartes de crédit','unit':'%','frequency':'trimestrielle','publisher':'Board of Governors of the Federal Reserve System'},
    {'id':'DEXTAUS','label':'Dollar taïwanais pour 1 dollar US','unit':'TWD/USD','frequency':'quotidienne','publisher':'Board of Governors of the Federal Reserve System (H.10)'},
    {'id':'DGS10','label':'Taux d’État US à 10 ans','unit':'%','frequency':'quotidienne','publisher':'Board of Governors of the Federal Reserve System (H.15)'},
]
IDS=[s['id'] for s in SERIES]

def parse(content,series_id):
    """CSV FRED : en-tête exact, dates croissantes uniques, valeurs manquantes conservées."""
    if series_id not in IDS:raise ValueError('Série non prévue')
    frame=pd.read_csv(io.BytesIO(content),dtype=str,keep_default_na=False)
    if list(frame.columns)!=['observation_date',series_id]:raise ValueError('En-tête FRED inattendu pour '+series_id)
    dates=pd.to_datetime(frame.observation_date,format='%Y-%m-%d',errors='raise')
    raw=frame[series_id].str.strip()
    if not raw.str.fullmatch(r'(-?\d+(\.\d+)?)|\.|').all():raise ValueError('Valeur non numérique dans '+series_id)
    values=pd.to_numeric(raw.replace({'.':np.nan,'':np.nan}))
    result=pd.DataFrame({'date':dates,'value':values})
    if not result.date.is_monotonic_increasing or not result.date.is_unique:raise ValueError('Dates non croissantes ou dupliquées')
    if result.value.notna().sum()<30:raise ValueError('Série trop courte : '+series_id)
    return result

def value_at(frame,date):
    """Dernière valeur connue à une date, sans interpolation ni valeur future."""
    known=frame.loc[(frame.date<=pd.Timestamp(date))&frame.value.notna()]
    return None if known.empty else float(known.value.iloc[-1])

def summary(frame,spec):
    valid=frame.loc[frame.value.notna()]
    last=valid.iloc[-1];last_date=last.date
    window=valid.loc[valid.date.between(COHORT_START,COHORT_END)]
    cohort_mean=None if window.empty else float(window.value.mean())
    def change(years):
        past=value_at(valid,last_date-pd.DateOffset(years=years))
        return None if past is None else float(last.value-past)
    return {'id':spec['id'],'label':spec['label'],'unit':spec['unit'],'frequency':spec['frequency'],
            'first_date':valid.date.iloc[0].date().isoformat(),'last_date':last_date.date().isoformat(),'observations':int(len(valid)),'missing_values_kept':int(frame.value.isna().sum()),
            'last_value':float(last.value),'long_run_mean':float(valid.value.mean()),
            'cohort_window_observations':int(len(window)),'cohort_window_mean':cohort_mean,
            'cohort_mean_percentile_in_history':None if cohort_mean is None else float((valid.value<=cohort_mean).mean()),
            'change_1y_points':change(1),'change_5y_points':change(5)}

def quarterly(series):
    """Moyenne trimestrielle de chaque série, puis variations d’un trimestre à l’autre."""
    columns={k:v.set_index('date').value.resample('QE').mean() for k,v in series.items()}
    levels=pd.DataFrame(columns).dropna()
    return levels,levels.diff().dropna()

def acquire_series(spec,cache_dir):
    cache=Path(cache_dir)/(spec['id']+'.csv')
    if cache.exists():content=cache.read_bytes();mode='existing immutable local cache'
    else:
        with urllib.request.urlopen(FRED_URL.format(spec['id']),timeout=60) as response:content=response.read(5_000_001)
        if len(content)>5_000_000:raise ValueError('Réponse trop volumineuse')
        parse(content,spec['id']);cache.parent.mkdir(parents=True,exist_ok=True)
        with cache.open('xb') as f:f.write(content)
        mode='live HTTPS FRED download'
    return parse(content,spec['id']),{'id':spec['id'],'url':FRED_URL.format(spec['id']),'mode':mode,'cache_sha256':digest(cache)}

def build(snapshot_id,cache_dir=None):
    if not re.fullmatch(r'[A-Za-z0-9_-]{1,60}',snapshot_id):raise ValueError('Identifiant de snapshot invalide')
    out=ROOT/'exports/macro'/snapshot_id;out.mkdir(parents=True,exist_ok=False)
    series,sources=[],[];frames={}
    for spec in SERIES:
        frame,source=acquire_series(spec,cache_dir or ROOT/'data/raw/fred')
        frames[spec['id']]=frame;sources.append(source);series.append(frame.assign(series=spec['id']))
    pd.concat(series).to_parquet(out/'series.parquet',index=False)
    levels,changes=quarterly(frames);levels.reset_index(names='quarter').to_parquet(out/'quarterly.parquet',index=False)
    report={'snapshot_id':snapshot_id,'created_at_utc':now(),'cohort_window':{'start':COHORT_START,'end':COHORT_END,'basis':'Historique de paiement UCI d’avril à septembre 2005'},
            'series':[summary(frames[s['id']],s) for s in SERIES],'sources':sources,
            'quarterly_common_period':{'start':levels.index[0].date().isoformat(),'end':levels.index[-1].date().isoformat(),'quarters':int(len(levels))},
            'spearman_quarterly_changes':changes.corr(method='spearman').round(6).to_dict(),
            'no_customer_join':True,
            'qualifications':['Séries US et taux de change : contexte sectoriel et monétaire, pas la situation des clients taïwanais','Corrélations sur variations trimestrielles : association, pas causalité','Valeurs manquantes FRED conservées, jamais remplies','Données brutes exclues de l’archive ; réutilisation selon les conditions FRED/Réserve fédérale']}
    save(out/'macro.json',report)
    save(ROOT/'exports/macro-latest.json',{'snapshot_id':snapshot_id,'report_sha256':digest(out/'macro.json')})
    save(ROOT/'docs/evidence/macro'/(snapshot_id+'.json'),report)
    return report

def latest_macro():
    """Snapshot publié, ou None si aucun contexte macro n’a été construit."""
    pointer=ROOT/'exports/macro-latest.json'
    if not pointer.exists():return None
    entry=json.loads(pointer.read_text());out=ROOT/'exports/macro'/entry['snapshot_id']
    if digest(out/'macro.json')!=entry['report_sha256']:raise ValueError('Rapport macro différent du pointeur publié')
    return json.loads((out/'macro.json').read_text()),pd.read_parquet(out/'series.parquet')
