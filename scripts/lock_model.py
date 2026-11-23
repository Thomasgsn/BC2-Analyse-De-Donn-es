"""Épingler le modèle public réellement acquis dans le volume autonome BC2."""
from pathlib import Path
import json,urllib.request,hashlib
base='http://ollama:11434';name='qwen3:1.7b'
with urllib.request.urlopen(base+'/api/tags',timeout=10) as r:models=json.load(r)['models']
m=next(x for x in models if x['name']==name)
with urllib.request.urlopen(urllib.request.Request(base+'/api/show',data=json.dumps({'model':name}).encode(),headers={'Content-Type':'application/json'}),timeout=15) as r:details=json.load(r)
existing=Path('infra/llm.lock.json')
if existing.exists() and json.loads(existing.read_text())['digest']!=m['digest']:raise ValueError('Digest du modèle différent du verrouillage livré : acquisition refusée')
license=details.get('license','')
if 'Apache License' not in license:raise ValueError('Licence attendue non retrouvée dans le modèle acquis')
lock={'model':name,'digest':m['digest'],'bytes':m['size'],'details':m.get('details'),'license':'Apache License 2.0','license_sha256':hashlib.sha256(license.encode()).hexdigest(),'source':'Actual local Ollama /api/tags and /api/show after provider pull; model card https://huggingface.co/Qwen/Qwen3-1.7B','scope':'Public weights only, no BC1 runtime/volume/keys reused'}
Path('exports/llm.lock.json').write_text(json.dumps(lock,indent=2)+'\n');Path('exports/llm-license.txt').write_text(license)
print(json.dumps({'event':'model_lock_ready','model':name,'digest':m['digest'],'bytes':m['size']}))
