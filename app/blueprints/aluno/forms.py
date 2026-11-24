from datetime import date
from flask_wtf import FlaskForm
from wtforms import (StringField, TextAreaField, SelectField, DateField,
                     IntegerField, PasswordField, SubmitField)
from wtforms.validators import DataRequired, Length, Optional, EqualTo


class EditarDadosAlunoForm(FlaskForm):
    """Formulário para o aluno preencher ou atualizar seus dados pessoais opcionais."""
    telefone = StringField('Telefone / WhatsApp', validators=[
        Optional(),
        Length(max=20, message='O telefone deve ter no máximo 20 caracteres.')
    ])
    data_nascimento = DateField('Data de Nascimento', format='%Y-%m-%d', validators=[
        Optional()
    ])
    submit_dados = SubmitField('Salvar Meus Dados')


class AlterarSenhaForm(FlaskForm):
    """Formulário para o aluno alterar sua senha de acesso."""
    senha_atual = PasswordField('Senha Atual *', validators=[
        DataRequired(message='Informe sua senha atual.')
    ])
    nova_senha = PasswordField('Nova Senha *', validators=[
        DataRequired(message='Informe a nova senha.'),
        Length(min=6, message='A nova senha deve ter no mínimo 6 caracteres.')
    ])
    confirmar_senha = PasswordField('Confirmar Nova Senha *', validators=[
        DataRequired(message='Confirme a nova senha.'),
        EqualTo('nova_senha', message='A confirmação de senha não confere com a nova senha.')
    ])
    submit = SubmitField('Salvar Nova Senha')


class AlunoPartidaForm(FlaskForm):
    """Formulário para o aluno registrar uma partida jogada."""
    titulo = StringField('Título da Partida / Confronto *', default='Partida de Beach Tennis', validators=[
        DataRequired(message='Informe o título.'),
        Length(max=150)
    ])
    data = DateField('Data do Jogo *', default=date.today, validators=[DataRequired(message='Informe a data.')])
    torneio = StringField('Torneio / Evento', default='Treino Competitivo', validators=[Optional(), Length(max=150)])
    categoria = SelectField('Categoria', choices=[
        ('Masculina D', 'Masculina D'),
        ('Masculina C', 'Masculina C'),
        ('Masculina B', 'Masculina B'),
        ('Masculina A', 'Masculina A'),
        ('Mista D', 'Mista D'),
        ('Mista C', 'Mista C'),
        ('Mista B', 'Mista B'),
        ('Open', 'Open'),
        ('Iniciante', 'Iniciante'),
    ], default='Masculina C')
    fase = StringField('Fase (ex: Fase de Grupos, Semifinal, Final, Treino)', default='Treino', validators=[Optional(), Length(max=50)])
    local = StringField('Local / Quadra', default='Arena Itabuna', validators=[Optional(), Length(max=150)])

    # Duplas
    parceiro_nome = StringField('Seu Parceiro de Dupla (Nome) *', validators=[
        DataRequired(message='Informe o nome do seu parceiro de dupla.'),
        Length(max=100)
    ])
    jogador3_nome = StringField('Adversário 1 (Nome) *', validators=[
        DataRequired(message='Informe o nome do primeiro adversário.'),
        Length(max=100)
    ])
    jogador4_nome = StringField('Adversário 2 (Nome) *', validators=[
        DataRequired(message='Informe o nome do segundo adversário.'),
        Length(max=100)
    ])

    # Placares dos Sets
    set1_dupla1 = IntegerField('Set 1 - Minha Dupla', default=0)
    set1_dupla2 = IntegerField('Set 1 - Adversários', default=0)
    set2_dupla1 = IntegerField('Set 2 - Minha Dupla', default=0)
    set2_dupla2 = IntegerField('Set 2 - Adversários', default=0)
    set3_dupla1 = IntegerField('Set 3 / Tiebreak - Minha Dupla', default=0)
    set3_dupla2 = IntegerField('Set 3 / Tiebreak - Adversários', default=0)

    placar_detalhado = StringField('Placar Detalhado (ex: 6x4 | 4x6 | 10x8)', validators=[Optional(), Length(max=100)])
    dupla_vencedora = SelectField('Resultado da Partida', choices=[
        (1, 'Vitória da Minha Dupla'),
        (2, 'Vitória dos Adversários')
    ], coerce=int, default=1)
    duracao_minutos = IntegerField('Duração estimada (minutos)', default=60, validators=[Optional()])
    observacoes = TextAreaField('Suas observações / relato do jogo (como você se sentiu, pontos que funcionaram e dificuldades)', validators=[Optional()])

    submit = SubmitField('Submeter Partida para Avaliação')
