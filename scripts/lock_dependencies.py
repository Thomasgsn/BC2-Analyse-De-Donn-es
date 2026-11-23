"""Verrouiller les versions installées et empreintes des roues publiées PyPI."""
from importlib.metadata import distributions
from pathlib import Path
import json,re,urllib.request
rows=[];inventory=[]
for d in sorted(distributions(),key=lambda d:d.metadata['Name'].lower()):
    name=d.metadata['Name'];version=d.version
    if name.lower()=='pip':continue
    if not re.fullmatch(r'[A-Za-z0-9_.-]+',name+version):raise ValueError('Nom/version inattendu')
    url=f'https://pypi.org/pypi/{name}/{version}/json'
    with urllib.request.urlopen(url,timeout=30) as r:x=json.load(r)
    hashes=sorted({v['digests']['sha256'] for v in x['urls'] if v['filename'].endswith('.whl')})
    if not hashes:raise ValueError('Aucune roue publiée pour '+name)
    rows.append(name+'=='+version+' \\\n'+ ' \\\n'.join('    --hash=sha256:'+h for h in hashes))
    inventory.append({'name':name,'version':version,'source':url,'wheel_hash_count':len(hashes)})
Path('/project/exports/requirements.lock').write_text('# Python 3.12, complete resolved dependency set; wheel SHA256 from official PyPI release metadata\n'+'\n'.join(rows)+'\n')
Path('/project/docs/evidence/pipeline/dependencies.json').write_text(json.dumps(inventory,indent=2)+'\n')
print(json.dumps({'event':'dependency_lock_created','distributions':len(rows)}))
