import os
from dotenv import load_dotenv

# Garante o carregamento do .env local do projeto Beach_Tennis_Web
basedir = os.path.abspath(os.path.dirname(__file__))
load_dotenv(os.path.join(basedir, '.env'), override=True)

from app import create_app
from app.extensions import db
from app.models import Usuario

app = create_app(os.environ.get('FLASK_ENV', 'development'))

# Garante que o usuário professor admin e dados iniciais da vitrine existam
with app.app_context():
    try:
        db.create_all()
        from app.utils.schema_migration import garantir_esquema_banco
        garantir_esquema_banco()
    except Exception as e:
        print(f">> Aviso na verificação inicial: {e}")

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
