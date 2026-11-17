import os
from app import create_app
from app.extensions import db
from app.utils.schema_migration import garantir_esquema_banco

app = create_app(os.environ.get('FLASK_ENV', 'production'))

# Garante que novas tabelas e colunas (como 'partidas.status', 'pontos_partida', etc.)
# sejam criadas e migradas automaticamente no PostgreSQL remoto (Neon / Supabase / Vercel Postgres).
with app.app_context():
    try:
        garantir_esquema_banco()
    except Exception as e:
        app.logger.warning(f"Aviso ao verificar tabelas/colunas do banco no startup: {e}")


