"""Artefacts atomiques et garde-fous de chemins du projet local."""
from pathlib import Path
from datetime import datetime, timezone
import hashlib,json,math,os,re,tempfile
import numpy as np

ROOT=Path(os.environ.get('BC2_ROOT','.')).resolve()

def now():return datetime.now(timezone.utc).isoformat()
def digest(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def clean(value):
    if isinstance(value,dict):return {str(k):clean(v) for k,v in value.items()}
    if isinstance(value,(list,tuple,np.ndarray)):return [clean(v) for v in value]
    if isinstance(value,np.generic):return clean(value.item())
    if isinstance(value,float) and not math.isfinite(value):return None
    if isinstance(value,Path):return str(value)
    return value

def save(path,value):
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    content=json.dumps(clean(value),ensure_ascii=False,indent=2,allow_nan=False)+'\n'
    with tempfile.NamedTemporaryFile('w',encoding='utf-8',dir=path.parent,delete=False) as f:
        tmp=Path(f.name)
        try:f.write(content);f.flush();os.fsync(f.fileno())
        except BaseException:tmp.unlink(missing_ok=True);raise
    os.replace(tmp,path)

def run_path(run):
    if not re.fullmatch(r'[A-Za-z0-9_-]{1,60}',run):raise ValueError('Identifiant de run invalide')
    return ROOT/'exports'/run

def latest():
    entry=json.loads((ROOT/'exports/latest.json').read_text())
    path=run_path(entry['run_id'])
    if digest(path/'manifest.json')!=entry['manifest_sha256']:raise ValueError('Manifeste différent du pointeur publié')
    manifest=json.loads((path/'manifest.json').read_text())
    if manifest['status']!='complete':raise ValueError('Run incomplet')
    return path,manifest
