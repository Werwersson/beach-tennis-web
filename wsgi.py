import os
import re
import traceback

from flask import Flask, jsonify

app = Flask(__name__)


def _redigir(texto):
    return re.sub(r'postgres(?:ql)?(?:\+\w+)?://[^\s"\']+', 'postgresql://***', str(texto))


@app.route('/', defaults={'path': ''})
@app.route('/<path:path>')
def diagnostico(path):
    import importlib.util
    import platform

    status = {
        'etapa': 'inicio',
        'secret_key': bool(os.environ.get('SECRET_KEY')),
        'database_url': bool(os.environ.get('DATABASE_URL')),
        'blob_store_id': bool(os.environ.get('BLOB_STORE_ID')),
        'vercel': bool(os.environ.get('VERCEL')),
        'python': platform.python_version(),
        'psycopg2': importlib.util.find_spec('psycopg2') is not None,
        'vercel_blob': importlib.util.find_spec('vercel') is not None,
    }
    try:
        from app import create_app
        status['etapa'] = 'app_importado'
        real = create_app('production')
        status['etapa'] = 'app_criado'

        from sqlalchemy import text
        from app.extensions import db
        with real.app_context():
            with db.engine.connect() as conexao:
                conexao.execute(text('SELECT 1'))
        status['etapa'] = 'banco_ok'
        status['status'] = 'ok'
        return jsonify(status), 200
    except Exception as exc:
        status['status'] = 'erro'
        status['erro'] = _redigir(f'{type(exc).__name__}: {exc}')
        status['trace'] = _redigir(traceback.format_exc())[-1800:]
        return jsonify(status), 500
