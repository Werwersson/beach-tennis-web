from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, BooleanField, SubmitField
from wtforms.validators import DataRequired, Length, Regexp


class LoginForm(FlaskForm):
    email = StringField('E-mail', validators=[
        DataRequired(message='Informe o e-mail.'),
        Regexp(r'^[^@\s]+@[^@\s]+\.[^@\s]+$', message='Informe um e-mail válido.')
    ])
    senha = PasswordField('Senha', validators=[
        DataRequired(message='Informe a senha.'),
        Length(min=6, message='Senha deve ter pelo menos 6 caracteres.')
    ])
    lembrar = BooleanField('Lembrar de mim')
    submit = SubmitField('Entrar')
