#!/usr/bin/env python3
"""Instala somente ferramentas opcionais dentro de .tools, sem configuração global."""
import base64
import hashlib
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tarfile
import urllib.request

ROOT=Path(__file__).resolve().parents[1]
TARGET=ROOT/'.tools'
(TARGET/'tmp').mkdir(parents=True,exist_ok=True)
env={**os.environ,'TMPDIR':str(TARGET/'tmp')}
subprocess.run([sys.executable,'-m','pip','install','--no-cache-dir','--target',str(TARGET/'python'),'reportlab==5.1.0','python-pptx==1.0.2'],check=True,env=env)
version='1.64.1'
with urllib.request.urlopen(f'https://registry.npmjs.org/playwright-core/{version}',timeout=30) as response:metadata=json.load(response)
with urllib.request.urlopen(metadata['dist']['tarball'],timeout=60) as response:archive=response.read()
expected=metadata['dist']['integrity']
actual='sha512-'+base64.b64encode(hashlib.sha512(archive).digest()).decode()
if expected!=actual:raise SystemExit('Integridade do pacote Playwright inválida')
(TARGET/'browser').mkdir(exist_ok=True)
with tarfile.open(fileobj=io.BytesIO(archive),mode='r:gz') as bundle:bundle.extractall(TARGET/'browser',filter='data')
print('Ferramentas disponíveis em .tools. Nada foi instalado globalmente.')
