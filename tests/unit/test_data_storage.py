import hashlib,json
import numpy as np,pandas as pd,pytest
from rncp_bc2.storage import save,run_path
from rncp_bc2.data import assign_splits,FEATURES,load_source

def test_group_split_keeps_duplicate_predictors_together():
    # Fixture synthétique de partition, pas un substitut aux données bancaires.
    rng=np.random.default_rng(2);n=1200
    frame=pd.DataFrame({c:rng.normal(size=n) for c in FEATURES});frame['group_id']=[str(i//2) for i in range(n)];frame['y']=np.tile([0,1],n//2)
    splits=assign_splits(frame)
    assert pd.DataFrame({'g':frame.group_id,'s':splits}).groupby('g').s.nunique().max()==1
    assert set(splits)=={'train','validation','test'}
    assert splits.equals(assign_splits(frame))

def test_source_digest_is_checked_before_parsing(tmp_path):
    p=tmp_path/'tampered.xls';p.write_bytes(b'not the official workbook')
    with pytest.raises(ValueError,match='Empreinte'):load_source(p)

def test_json_serialization_failure_preserves_previous_artifact(tmp_path):
    p=tmp_path/'report.json';save(p,{'n':1});original=p.read_bytes()
    with pytest.raises(TypeError):save(p,{'unserializable':object()})
    assert p.read_bytes()==original

@pytest.mark.parametrize('name',['../secret','a/b','','x'*61])
def test_run_path_cannot_escape_project(name):
    with pytest.raises(ValueError):run_path(name)
