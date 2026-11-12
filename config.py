import os
from datetime import timedelta

basedir = os.path.abspath(os.path.dirname(__file__))


def normalizar_database_url(url):
    """Força o driver psycopg2 (já instalado) em URLs PostgreSQL.

    Sem o sufixo +psycopg2, versões novas do SQLAlchemy podem tentar usar
    psycopg 3, que não está nas dependências do projeto.
    """
    if not url:
        return url
    if url.startswith('postgres://'):
        return 'postgresql+psycopg2://' + url[len('postgres://'):]
    if url.startswith('postgresql://'):
        return 'postgresql+psycopg2://' + url[len('postgresql://'):]
    return url


class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY', 'dev-secret-mude-em-producao')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    WTF_CSRF_ENABLED = True
    MAX_CONTENT_LENGTH = 5 * 1024 * 1024  # 5MB
    upload_env = os.environ.get('UPLOAD_FOLDER')
    UPLOAD_FOLDER = upload_env if upload_env else os.path.join(basedir, 'app', 'static', 'uploads')
    ALLOWED_EXTENSIONS = {'jpg', 'jpeg', 'png', 'gif', 'webp'}
    PERMANENT_SESSION_LIFETIME = timedelta(days=30)
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'
    REMEMBER_COOKIE_HTTPONLY = True
    REMEMBER_COOKIE_SAMESITE = 'Lax'

class DevelopmentConfig(Config):
    DEBUG = True
    SESSION_COOKIE_SECURE = False
    REMEMBER_COOKIE_SECURE = False
    db_url = os.environ.get('DATABASE_URL', f'sqlite:///{os.path.join(basedir, "beach_tennis.db")}')
    db_url = normalizar_database_url(db_url)
    SQLALCHEMY_DATABASE_URI = db_url

class ProductionConfig(Config):
    DEBUG = False
    SESSION_COOKIE_SECURE = True
    REMEMBER_COOKIE_SECURE = True
    PREFERRED_URL_SCHEME = 'https'

    SECRET_KEY = os.environ.get('SECRET_KEY', '')
    database_url = os.environ.get('DATABASE_URL', '')
    database_url = normalizar_database_url(database_url)
    SQLALCHEMY_DATABASE_URI = database_url

    # Evita conexões mortas em bancos gerenciados (Neon/Supabase) que suspendem
    # por inatividade. O pool recicla antes do timeout típico.
    SQLALCHEMY_ENGINE_OPTIONS = {
        'pool_pre_ping': True,
        'pool_recycle': 280,
    }

config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'default': DevelopmentConfig,
}
