import os
import re
from flask import Flask, render_template, url_for
from werkzeug.middleware.proxy_fix import ProxyFix
from .extensions import db, login_manager, migrate, csrf
from config import config

# Imports no nível do módulo: além de evitar importações tardias, garantem que
# o empacotador do Vercel inclua models, blueprints e utils no bundle da função.
from .models import (Usuario, Aluno, MetaAluno, Turma, TurmaAluno,
                     Exercicio, Aula, AulaExercicio, Presenca,
                     Avaliacao, AvaliacaoNota, Depoimento,
                     ConfiguracaoSite, Plano, Conquista, TrofeuAluno,
                     Modalidade, GaleriaItem, MensagemContato,
                     Partida, PontoPartida)
from .blueprints.public.routes import public_bp
from .blueprints.auth.routes import auth_bp
from .blueprints.admin.routes import admin_bp
from .blueprints.aluno.routes import aluno_bp


def create_app(config_name=None):
    if config_name is None:
        config_name = os.environ.get('FLASK_ENV', 'default')

    app = Flask(__name__)
    app.config.from_object(config[config_name])

    # Em produção, falha cedo com mensagem clara em vez de erro obscuro do SQLAlchemy
    if config_name == 'production':
        if not app.config.get('SECRET_KEY'):
            raise RuntimeError(
                'SECRET_KEY não definida. Configure a variável de ambiente SECRET_KEY '
                'com uma chave aleatória antes de iniciar em produção.'
            )
        if not app.config.get('SQLALCHEMY_DATABASE_URI'):
            raise RuntimeError(
                'DATABASE_URL não definida. Configure a string de conexão do PostgreSQL '
                '(Neon/Vercel, Supabase ou Railway) antes de iniciar em produção.'
            )
        # Vercel/Render terminam o TLS no proxy; confia em um proxy para
        # reconstruir o esquema/host corretos (cookies Secure, url_for externo).
        app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1)

    # Inicializa extensões
    db.init_app(app)
    login_manager.init_app(app)
    migrate.init_app(app, db)
    csrf.init_app(app)

    # Cria diretório de uploads caso não exista
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

    # Registra Blueprints
    app.register_blueprint(public_bp)
    app.register_blueprint(auth_bp, url_prefix='/auth')
    app.register_blueprint(admin_bp, url_prefix='/admin')
    app.register_blueprint(aluno_bp, url_prefix='/aluno')

    # Injeção de variáveis globais nos templates
    @app.context_processor
    def inject_site_data():
        nao_lidas = 0
        partidas_pendentes = 0
        try:
            from .models import MensagemContato
            nao_lidas = MensagemContato.query.filter_by(lida=False).count()
        except Exception:
            try:
                db.session.rollback()
            except Exception:
                pass

        try:
            from .models import Partida
            partidas_pendentes = Partida.query.filter_by(status='pendente').count()
        except Exception:
            try:
                db.session.rollback()
            except Exception:
                pass

        return {
            'total_mensagens_nao_lidas': nao_lidas,
            'total_partidas_pendentes': partidas_pendentes
        }

    # Comandos de linha de comando para preparar o banco em produção
    @app.cli.command('init-db')
    def init_db_command():
        """Cria as tabelas que ainda não existem (fallback sem migrations)."""
        db.create_all()
        print('Tabelas verificadas/criadas com sucesso.')

    @app.cli.command('seed')
    def seed_command():
        """Cria/atualiza os dados iniciais do site de forma idempotente."""
        from seed import seed_database
        seed_database()

    @app.cli.command('set-admin-password')
    def set_admin_password_command():
        """Redefine a senha do admin usando ADMIN_EMAIL e ADMIN_PASSWORD."""
        import os
        import click
        from .models import Usuario

        email = os.environ.get('ADMIN_EMAIL', 'professor@beachtennis.com').strip().lower()
        senha = os.environ.get('ADMIN_PASSWORD')
        if not senha or len(senha) < 6:
            raise click.ClickException('Defina ADMIN_PASSWORD com pelo menos 6 caracteres.')
        usuario = Usuario.query.filter_by(email=email).first()
        if not usuario:
            raise click.ClickException(f'Admin não encontrado: {email}')
        usuario.set_senha(senha)
        db.session.commit()
        click.echo(f'Senha do admin {email} atualizada.')

    # Headers de Segurança
    @app.after_request
    def set_security_headers(response):
        response.headers['X-Content-Type-Options'] = 'nosniff'
        response.headers['X-Frame-Options'] = 'SAMEORIGIN'
        response.headers['X-XSS-Protection'] = '1; mode=block'
        response.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'
        return response

    # Filtros úteis no Jinja
    @app.template_filter('somente_numeros')
    def somente_numeros(valor):
        if not valor:
            return ''
        return re.sub(r'\D', '', str(valor))

    @app.template_filter('nl2br')
    def nl2br_filter(s):
        if not s:
            return ''
        from markupsafe import Markup, escape
        return Markup('<br>'.join(escape(s).splitlines()))

    @app.template_global()
    def upload_url(valor):
        """URL de uma imagem: aceita nome local ou URL completa (Vercel Blob/S3)."""
        if not valor:
            return ''
        valor = str(valor)
        if valor.startswith(('http://', 'https://')):
            return valor
        return url_for('static', filename=f'uploads/{valor}')

    # Handlers de Erro
    @app.errorhandler(404)
    def page_not_found(e):
        return render_template('erros/404.html'), 404

    @app.errorhandler(403)
    def forbidden(e):
        return render_template('erros/403.html'), 403

    @app.errorhandler(500)
    def internal_server_error(e):
        return render_template('erros/500.html'), 500

    return app
