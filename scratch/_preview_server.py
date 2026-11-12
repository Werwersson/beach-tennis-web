"""Servidor temporário de pré-visualização (auto-login) para conferência visual.

Não faz parte da aplicação: é usado apenas para gerar screenshots de validação.
"""
import os
import sys

BASE = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, BASE)

from flask_login import login_user
from flask import redirect
from app import create_app
from app.models import Usuario, Aluno

app = create_app('development')
app.config['WTF_CSRF_ENABLED'] = False


@app.route('/__preview/aluno')
def preview_aluno():
    usuario = Usuario.query.filter_by(email='aluno@beachtennis.com').first()
    login_user(usuario)
    return redirect('/aluno/evolucao')


@app.route('/__preview/admin/<int:aluno_id>')
def preview_admin(aluno_id):
    usuario = Usuario.query.filter_by(email='professor@beachtennis.com').first()
    login_user(usuario)
    return redirect(f'/admin/alunos/{aluno_id}')


@app.route('/__preview/health')
def health():
    with app.app_context():
        aluno = Aluno.query.order_by(Aluno.id).first()
        avals = len(aluno.avaliacoes) if aluno else 0
    return f'ok aluno={aluno.id if aluno else None} avaliacoes={avals}'


if __name__ == '__main__':
    app.run(host='127.0.0.1', port=5057, debug=False, use_reloader=False)
