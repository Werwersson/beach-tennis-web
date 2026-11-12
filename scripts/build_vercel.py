"""Copia os arquivos estáticos para public/ no build do Vercel.

O Vercel serve arquivos estáticos a partir de public/**, e não do
app.static_folder do Flask. Este script mantém o CSS, JS e imagens em
public/static sem duplicar os uploads locais.
"""
import importlib.util
import json
import os
import shutil
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
ORIGEM = RAIZ / 'app' / 'static'
DESTINO = RAIZ / 'public' / 'static'


def main():
    if not ORIGEM.exists():
        raise SystemExit(f'Pasta de estáticos não encontrada: {ORIGEM}')

    if DESTINO.exists():
        shutil.rmtree(DESTINO)
    DESTINO.parent.mkdir(parents=True, exist_ok=True)

    shutil.copytree(
        ORIGEM,
        DESTINO,
        ignore=shutil.ignore_patterns('uploads', '__pycache__', '*.pyc'),
    )

    # Diagnóstico temporário: apenas booleanos, sem expor valores.
    try:
        import sqlalchemy
        sqlalchemy_versao = sqlalchemy.__version__
    except Exception:
        sqlalchemy_versao = 'indisponivel'
    status = {
        'secret_key': bool(os.environ.get('SECRET_KEY')),
        'database_url': bool(os.environ.get('DATABASE_URL')),
        'blob_store_id': bool(os.environ.get('BLOB_STORE_ID')),
        'vercel': bool(os.environ.get('VERCEL')),
        'psycopg2': importlib.util.find_spec('psycopg2') is not None,
        'vercel_blob': importlib.util.find_spec('vercel') is not None,
        'sqlalchemy': sqlalchemy_versao,
    }
    (RAIZ / 'public' / 'env-status.json').write_text(
        json.dumps(status, ensure_ascii=False), encoding='utf-8'
    )

    print(f'Estáticos copiados para {DESTINO}')
    print('Diagnóstico:', status)


if __name__ == '__main__':
    main()
