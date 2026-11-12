import os
import re
import traceback

from flask import Flask, jsonify


def _redigir(texto):
    return re.sub(r'postgres(?:ql)?(?:\+\w+)?://[^\s"\']+', 'postgresql://***', str(texto))


try:
    from app import create_app
    from app.extensions import db

    app = create_app(os.environ.get('FLASK_ENV', 'production'))

    @app.route('/__diag')
    def _diag():
        status = {
            'status': 'app_ok',
            'secret_key': bool(os.environ.get('SECRET_KEY')),
            'database_url': bool(os.environ.get('DATABASE_URL')),
            'blob_store_id': bool(os.environ.get('BLOB_STORE_ID')),
            'vercel': bool(os.environ.get('VERCEL')),
        }
        try:
            from sqlalchemy import text
            with db.engine.connect() as conexao:
                conexao.execute(text('SELECT 1'))
            status['database'] = 'ok'
        except Exception as exc:
            status['database'] = _redigir(f'{type(exc).__name__}: {exc}')
        return jsonify(status)

except Exception as exc:
    _erro = _redigir(f'{type(exc).__name__}: {exc}')
    _trace = _redigir(traceback.format_exc())[-1800:]

    app = Flask(__name__)

    @app.route('/', defaults={'path': ''})
    @app.route('/<path:path>')
    def _diagnostico(path):
        return jsonify({
            'status': 'erro_importacao',
            'erro': _erro,
            'trace': _trace,
            'secret_key': bool(os.environ.get('SECRET_KEY')),
            'database_url': bool(os.environ.get('DATABASE_URL')),
            'blob_store_id': bool(os.environ.get('BLOB_STORE_ID')),
            'vercel': bool(os.environ.get('VERCEL')),
        }), 500
