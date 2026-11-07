#!/usr/bin/env python3
"""Empacota apenas arquivos de entrega, sem banco de trabalho ou dependências de QA."""
from pathlib import Path
import zipfile

ROOT=Path(__file__).resolve().parents[1]
DEST=ROOT/'artifacts'/'entrega-controle-vendas.zip'
required=['README.txt','Makefile','iniciar.sh','Dockerfile','compose.yaml','.dockerignore','docs/relatorio-tecnico.pdf','docs/apresentacao.pptx','docs/apresentacao.pdf','data/exemplo.db','artifacts/test-results.json','artifacts/ui-test-results.json','artifacts/sanitizer-test-results.json']
for name in required:
    if not (ROOT/name).is_file():raise SystemExit('Entrega incompleta: falta '+name)
files=[]
for folder in ['src','include','vendor','web/src','docs','scripts','tests']:
    for item in (ROOT/folder).rglob('*'):
        if item.is_file() and not any(p in {'.runtime','__pycache__'} for p in item.relative_to(ROOT).parts) and item.suffix!='.zip':files.append(item)
for item in (ROOT/'artifacts').iterdir():
    if item.is_file() and item.suffix in {'.png','.json','.pdf','.csv','.txt'}:files.append(item)
qa_names = [
    'test-results.json', 'sanitizer-test-results.json', 'ui-test-results.json',
    '02-produtos.png', '03-nova-venda.png', '04-relatorios.png',
    '05-validacao.png', '06-comprovante.png', '07-celular.png',
]
for name in qa_names:
    item = ROOT / 'artifacts' / 'qa' / name
    if item.is_file():
        files.append(item)
for name in ['README.md','README.txt','Makefile','iniciar.sh','Dockerfile','compose.yaml','.dockerignore','THIRD_PARTY_NOTICES.txt','Projeto_Pratico_C_4_Pontos.pdf','data/exemplo.db','.gitignore']:
    files.append(ROOT/name)
files.extend(ROOT/'web'/name for name in ['angular.json','package.json','package-lock.json','tsconfig.json'])
with zipfile.ZipFile(DEST,'w',zipfile.ZIP_DEFLATED,compresslevel=6) as bundle:
    for item in sorted(set(files)):bundle.write(item,Path('controle-vendas')/item.relative_to(ROOT))
print(f'Pacote criado: {DEST.relative_to(ROOT)} ({DEST.stat().st_size:,} bytes; {len(set(files))} arquivos)')
