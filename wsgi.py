import os
from app import create_app
from app.extensions import db

app = create_app(os.environ.get('FLASK_ENV', 'production'))

# Garante que novas tabelas (como 'partidas' e 'pontos_partida') sejam criadas automaticamente
# no PostgreSQL remoto (Neon / Supabase / Vercel Postgres) sem travar caso a conexão oscile.
with app.app_context():
    try:
        db.create_all()
    except Exception as e:
        app.logger.warning(f"Aviso ao verificar tabelas do banco no startup: {e}")

