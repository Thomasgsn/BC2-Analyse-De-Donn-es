import numpy as np
import pytest
from rncp_bc2.metrics import binary_metrics,bh_adjust,threshold_on_validation

def test_rare_class_constant_baseline_exposes_no_recall():
    m=binary_metrics([0]*98+[1]*2,[.02]*100)
    assert m['tn']==98 and m['fn']==2 and m['recall']==0 and m['precision'] is None
    assert m['roc_auc']==.5 and m['pr_auc_average_precision']==.02

def test_confusion_and_missing_class_are_explicit():
    m=binary_metrics([0,0,1,1],[.1,.9,.8,.2]);assert (m['tp'],m['fp'],m['tn'],m['fn'])==(1,1,1,1)
    assert m['f1']==.5 and m['brier']==pytest.approx(.375)
    m=binary_metrics([0,0],[.1,.2]);assert m['roc_auc'] is None and m['recall'] is None and m['pr_auc_average_precision'] is None

@pytest.mark.parametrize('y,s',[([],[]),([2],[.2]),([1],[float('nan')]),([1],[1.1]),([1,0],[.5])])
def test_invalid_metrics_fail(y,s):
    with pytest.raises(ValueError):binary_metrics(y,s)

def test_bh_unsorted_known_values_and_invalid_values():
    assert bh_adjust([.04,.001,.02])==pytest.approx([.04,.003,.03])
    with pytest.raises(ValueError):bh_adjust([-.1])

def test_threshold_uses_supplied_validation_only():
    best,all_rows=threshold_on_validation([0,0,1,1],[.1,.25,.3,.8]);assert best['fn']==0 and best['fp']==0 and len(all_rows)==19
