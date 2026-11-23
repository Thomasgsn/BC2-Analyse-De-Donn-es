"""Archive locale bornée, sources publiques/documentation/preuves sans bruts ni poids."""
from pathlib import Path
import hashlib,json,zipfile
from datetime import datetime,timezone
ROOT=Path(__file__).resolve().parents[1]
files=[]
for name in ['README.md','AGENTS.md','.env.example','.gitignore','.dockerignore','compose.yml','requirements.in','requirements.lock']:
 files.append(ROOT/name)
for directory in ['src','tests','scripts','infra','docs','output/pdf','output/presentations']:
 for p in (ROOT/directory).rglob('*'):
  if p.is_file() and not any(x in p.parts for x in ['__pycache__','.pytest_cache','node_modules']) and p.suffix not in ['.pyc','.zip']:files.append(p)
files=sorted(set(files));manifest={'scope':'Local BC2 source, documentation and aggregate proofs; no raw client/market files, weights, models, credentials or Git history','files':{p.relative_to(ROOT).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in files}}
output=ROOT/'output';output.mkdir(exist_ok=True);(output/'delivery-manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n')
archive=output/f"bc2-rendu-{datetime.now(timezone.utc):%Y%m%d}.zip"
if archive.exists():raise SystemExit(f'{archive.name} existe déjà : archive non écrasée')
with zipfile.ZipFile(archive,'w',compression=zipfile.ZIP_DEFLATED) as z:
 for p in files:z.write(p,'bc2/'+p.relative_to(ROOT).as_posix())
 z.write(output/'delivery-manifest.json','bc2/output/delivery-manifest.json')
with zipfile.ZipFile(archive) as z:
 assert z.testzip() is None
 for name in z.namelist():
  parts=Path(name).parts
  assert not any(x in parts[1:2] for x in ['data','models','exports','tmp','.git'])
 assert len(z.namelist())==len(files)+1
print(json.dumps({'archive':str(archive),'files':len(files)+1,'bytes':archive.stat().st_size,'sha256':hashlib.sha256(archive.read_bytes()).hexdigest(),'crc':'passed'}))
