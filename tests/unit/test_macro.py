import numpy as np
import pandas as pd
import pytest
from rncp_bc2.macro import parse,summary,quarterly,value_at,SERIES

# Séries fictives unitaires identifiées, jamais présentées comme données FRED réelles.
def csv(series_id,rows):
    return ('observation_date,'+series_id+'\n'+'\n'.join(f'{d},{v}' for d,v in rows)+'\n').encode()

def quarterly_rows(start='2000-01-01',n=40,base=2.0):
    dates=pd.date_range(start,periods=n,freq='QS')
    return [(d.date().isoformat(),f'{base+i*0.1:.2f}') for i,d in enumerate(dates)]

def test_parse_keeps_missing_values_without_filling():
    rows=quarterly_rows();rows[3]=(rows[3][0],'.')
    frame=parse(csv('DRCCLACBS',rows),'DRCCLACBS')
    assert frame.value.isna().sum()==1 and len(frame)==40

@pytest.mark.parametrize('content,error',[(b'date,X\n2000-01-01,1\n','En-tête'),(csv('DGS10',[('2000-01-02','1'),('2000-01-01','2')]*20),'croissantes'),(csv('DGS10',[('2000-01-01','abc')]),'numérique')])
def test_parse_rejects_invalid_payloads(content,error):
    with pytest.raises(ValueError,match=error):parse(content,'DGS10')

def test_unknown_series_is_refused():
    with pytest.raises(ValueError):parse(csv('SP500',quarterly_rows()),'SP500')

def test_value_at_never_uses_future_observation():
    frame=pd.DataFrame({'date':pd.to_datetime(['2005-01-01','2005-07-01']),'value':[1.0,2.0]})
    assert value_at(frame,'2005-06-30')==1.0
    assert value_at(frame,'2004-12-31') is None

def test_summary_reports_cohort_window_and_changes():
    frame=parse(csv('DRCCLACBS',quarterly_rows()),'DRCCLACBS')
    s=summary(frame,SERIES[0])
    assert s['cohort_window_observations']==2  # 2005-04-01 et 2005-07-01
    assert s['cohort_window_mean']==pytest.approx((2.0+21*0.1+2.0+22*0.1)/2)
    assert s['change_1y_points']==pytest.approx(0.4)
    assert 0<s['cohort_mean_percentile_in_history']<1

def test_quarterly_changes_align_series():
    a=pd.DataFrame({'date':pd.date_range('2000-01-01',periods=8,freq='QS'),'value':np.arange(8.)})
    b=pd.DataFrame({'date':pd.date_range('2000-01-03',periods=500,freq='D'),'value':np.linspace(1,2,500)})
    levels,changes=quarterly({'A':a,'B':b})
    assert list(levels.columns)==['A','B'] and len(changes)==len(levels)-1
