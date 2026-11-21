from datetime import datetime
from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_user, logout_user, login_required, current_user
from app.extensions import db
from app.models import Usuario
from .forms import LoginForm

auth_bp = Blueprint('auth', __name__)


@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        if current_user.is_admin:
            return redirect(url_for('admin.dashboard'))
        return redirect(url_for('aluno.painel'))

    form = LoginForm()
    if form.validate_on_submit():
        email_limpo = form.email.data.lower().strip()
        senha_digitada = form.senha.data
        usuario = Usuario.query.filter_by(email=email_limpo).first()
        if usuario and usuario.ativo and (usuario.check_senha(senha_digitada) or usuario.check_senha(senha_digitada.strip())):
            login_user(usuario, remember=form.lembrar.data)
            usuario.ultimo_login = datetime.utcnow()
            db.session.commit()
            flash(f'Olá, {usuario.nome}! Login realizado com sucesso.', 'success')
            next_page = request.args.get('next')
            if next_page:
                from urllib.parse import urlsplit
                parsed = urlsplit(next_page)
                if not parsed.netloc and not parsed.scheme and next_page.startswith('/') and not next_page.startswith(('//', '/\\')):
                    return redirect(next_page)
            if usuario.is_admin:
                return redirect(url_for('admin.dashboard'))
            return redirect(url_for('aluno.painel'))
        flash('E-mail ou senha inválidos. Verifique suas credenciais e tente novamente.', 'danger')

    return render_template('auth/login.html', form=form)


@auth_bp.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Você saiu da sua conta com sucesso. Até logo!', 'info')
    return redirect(url_for('auth.login'))
