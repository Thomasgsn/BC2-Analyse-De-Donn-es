"""Acquisition UCI350 vérifiée, sans écrasement d'une source différente."""
from pathlib import Path
from zipfile import ZipFile
import hashlib,io,urllib.request
from .storage import ROOT,save,now,digest
from .data import SOURCE_SHA
URL='https://archive.ics.uci.edu/static/public/350/default%2Bof%2Bcredit%2Bcard%2Bclients.zip'
ZIP_SHA='56c885f84457f6680f8438f02bfcdac9579323d8a94465ee5f26e32baa727602'

def acquire():
    root=ROOT/'data/raw';root.mkdir(parents=True,exist_ok=True)
    zip_path=root/'uci350-original.zip';candidate=ROOT/'data/candidates/uci350-original.zip'
    if zip_path.exists():blob=zip_path.read_bytes();mode='verified existing archive'
    elif candidate.exists():blob=candidate.read_bytes();mode='verified previously researched official candidate'
    else:
        with urllib.request.urlopen(URL,timeout=90) as r:blob=r.read(10_000_001)
        mode='live official HTTPS acquisition'
    if len(blob)>10_000_000 or hashlib.sha256(blob).hexdigest()!=ZIP_SHA:raise ValueError('Archive UCI différente du verrouillage')
    with ZipFile(io.BytesIO(blob)) as z:
        if z.namelist()!=['default of credit card clients.xls'] or z.testzip() is not None:raise ValueError('Structure/CRC ZIP invalide')
        xls=z.read(z.namelist()[0])
    if hashlib.sha256(xls).hexdigest()!=SOURCE_SHA:raise ValueError('Empreinte XLS invalide')
    for path,content in [(zip_path,blob),(root/'uci350-original.xls',xls)]:
        if path.exists():
            if path.read_bytes()!=content:raise FileExistsError('Source existante différente : '+path.name)
        else:
            with path.open('xb') as f:f.write(content)
    report={'at_utc':now(),'url':URL,'mode':mode,'zip_sha256':ZIP_SHA,'xls_sha256':SOURCE_SHA,'license':'CC BY 4.0','attribution':'I-Cheng Yeh, UCI Default of Credit Card Clients, DOI 10.24432/C55S3H','source_unchanged':True}
    save(ROOT/'docs/evidence/pipeline/source-acquisition.json',report);return report
