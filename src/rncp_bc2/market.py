"""Cotations brutes Alpha Vantage, contrôles OHLCV et indicateurs explicites."""
from pathlib import Path
from datetime import datetime
import json,urllib.request
import numpy as np,pandas as pd
from .storage import ROOT,save,digest,now
URL='https://www.alphavantage.co/query?function=TIME_SERIES_DAILY&symbol=IBM&apikey=demo'

def parse(payload):
    if 'Time Series (Daily)' not in payload or payload.get('Meta Data',{}).get('2. Symbol')!='IBM':raise ValueError('Pas de cotations IBM : réponse erreur/quota ou schéma invalide')
    rows=[]
    for date,v in payload['Time Series (Daily)'].items():
        datetime.strptime(date,'%Y-%m-%d')
        row={'date':date,**{name:float(v[key]) for name,key in [('open','1. open'),('high','2. high'),('low','3. low'),('close','4. close')]},'volume':int(v['5. volume'])}
        values=[row[k] for k in ['open','high','low','close']]
        if not np.isfinite(values).all() or min(values)<=0 or row['volume']<0 or row['high']<max(values) or row['low']>min(values):raise ValueError('OHLCV incohérent')
        rows.append(row)
    frame=pd.DataFrame(rows).sort_values('date').reset_index(drop=True)
    if len(frame)<30 or not frame.date.is_unique:raise ValueError('Série insuffisante ou dates dupliquées')
    return frame

def indicators(frame):
    frame=frame.copy();close=frame.close
    if close.empty or (close<=0).any() or not np.isfinite(close).all():raise ValueError('Cours positifs finis requis')
    frame['return']=close.pct_change();frame['log_return']=np.log(close/close.shift(1));frame['base100']=100*close/close.iloc[0]
    frame['volatility20_annualized']=frame.log_return.rolling(20,min_periods=20).std(ddof=1)*np.sqrt(252)
    frame['drawdown']=close/close.cummax()-1
    return frame

def acquire(out,cache_path=None):
    cache=Path(cache_path or ROOT/'data/raw/market-ibm-demo.json')
    if cache.exists():content=cache.read_bytes();mode='existing immutable local cache'
    else:
        with urllib.request.urlopen(URL,timeout=30) as response:content=response.read(2_000_001)
        if len(content)>2_000_000:raise ValueError('Réponse trop volumineuse')
        parse(json.loads(content));cache.parent.mkdir(parents=True,exist_ok=True)
        with cache.open('xb') as f:f.write(content)
        mode='live HTTPS demo endpoint'
    payload=json.loads(content);frame=indicators(parse(payload));frame.to_parquet(out/'market.parquet',index=False)
    report={'source':URL,'retrieved_or_checked_at_utc':now(),'mode':mode,'cache_sha256':digest(cache),'symbol':'IBM','rows':len(frame),'first_date':frame.date.iloc[0],'last_date':frame.date.iloc[-1],'timezone_of_session':payload['Meta Data'].get('5. Time Zone'),'currency':None,'currency_note':'Currency not present in this response; do not invent a currency label','price_type':'Raw daily OHLCV, not dividend-adjusted total return','annualization':'Sample standard deviation of 20 log returns times sqrt(252), convention not measured trading calendar','max_drawdown':float(frame.drawdown.min()),'period_price_return':float(frame.close.iloc[-1]/frame.close.iloc[0]-1),'return_volume_spearman':float(frame[['return','volume']].corr(method='spearman').iloc[0,1]),'no_customer_join':True,'rights':'Provider personal/non-commercial research terms, raw data excluded from delivery archive; no public hosting','qualifications':['Daily historical snapshot, not real-time feed','2026 quotation window has no temporal join to the 2005 client cohort','Missing market dates are not forward-filled','Demo key is the provider public example, not a private API credential']}
    save(out/'market.json',report);return report
