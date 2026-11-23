import pytest
from rncp_bc2.generation import validate_output,template
FACTS={k:{'value':'fixture synthétique'} for k in ['a','b','c','d']}

def test_classic_template_is_deterministic_and_references_only_supplied_facts():
    assert template(FACTS,'portfolio')==template(FACTS,'portfolio')

@pytest.mark.parametrize('change',[{'summary':'Le client doit payer 500 euros, nous en sommes absolument certains.'},{'limits':'Tout va bien et les résultats sont fiables.'},{'evidence_ids':['a','b','made_up']},{'evidence_ids':['a','a','b']},{'summary':'Ce mauvais payeur est irresponsable et il faut refuser le crédit immédiatement.'}])
def test_hallucination_or_missing_limits_are_rejected(change):
    output=template(FACTS,'portfolio')|change
    with pytest.raises(ValueError):validate_output(output,FACTS)
