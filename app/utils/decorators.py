from functools import wraps
from flask import abort, flash, redirect, request, url_for
from flask_login import current_user


def admin_required(f):
    """
    Exige que o usuário esteja autenticado e tenha perfil de 'admin'.
    Caso não esteja logado, redireciona para a tela de login guardando next.
    Caso esteja logado com outro perfil, exibe mensagem e retorna erro 403.
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            return redirect(url_for('auth.login', next=request.path))
        if not current_user.is_admin:
            flash('Acesso restrito ao professor/administrador.', 'warning')
            abort(403)
        return f(*args, **kwargs)
    return decorated_function


def aluno_required(f):
    """
    Exige que o usuário esteja autenticado e tenha perfil de 'aluno'.
    Caso não esteja logado, redireciona para a tela de login guardando next.
    Caso esteja logado com outro perfil, exibe mensagem e retorna erro 403.
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            return redirect(url_for('auth.login', next=request.path))
        if not current_user.is_aluno:
            flash('Acesso restrito ao painel do aluno.', 'warning')
            abort(403)
        return f(*args, **kwargs)
    return decorated_function
