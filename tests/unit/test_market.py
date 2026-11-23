import pandas as pd
import pytest
from rncp_bc2.market import parse,indicators

def test_returns_and_drawdown_known_fixture():
    # Données fictives unitaires identifiées, jamais présentées comme cotations.
    x=indicators(pd.DataFrame({'close':[100.,120.,90.,108.]}))
    assert x.base100.tolist()==[100.,120.,90.,108.]
    assert x['return'].iloc[1]==pytest.approx(.2)
    assert x.drawdown.iloc[2]==pytest.approx(-.25)
    assert x.volatility20_annualized.isna().all()

def test_quota_payload_is_not_data():
    with pytest.raises(ValueError,match='quotas?|quota|schéma'):parse({'Information':'limit'})

@pytest.mark.parametrize('prices',[[0.,1.],[-1.,1.],[float('nan'),1.]])
def test_invalid_prices_do_not_become_returns(prices):
    with pytest.raises(ValueError):indicators(pd.DataFrame({'close':prices}))
