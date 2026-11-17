from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileAllowed
from datetime import date
from wtforms import (StringField, TextAreaField, SelectField, SelectMultipleField,
                     DateField, TimeField, DateTimeLocalField, IntegerField, FloatField,
                     BooleanField, PasswordField, SubmitField)
from wtforms.validators import DataRequired, Length, Optional, ValidationError, Regexp, NumberRange
from app.extensions import db
from app.models import Usuario
from app.models.exercicio import CATEGORIAS_EXERCICIO, NIVEIS_EXERCICIO
from app.models.avaliacao import CRITERIOS_AVALIACAO
from app.models.categoria import CATEGORIAS_BEACH_TENNIS


NIVEIS = [('iniciante', 'Iniciante'), ('intermediario', 'Intermediário'), ('avancado', 'Avançado')]
LADOS = [('destro', 'Destro'), ('canhoto', 'Canhoto')]
OBJETIVOS = [('lazer', 'Lazer'), ('competicao', 'Competição'), ('condicionamento', 'Condicionamento Físico')]

DIAS_SEMANA_CHOICES = [
    ('0', 'Segunda-feira'),
    ('1', 'Terça-feira'),
    ('2', 'Quarta-feira'),
    ('3', 'Quinta-feira'),
    ('4', 'Sexta-feira'),
    ('5', 'Sábado'),
    ('6', 'Domingo'),
]

NIVEIS_TURMA = [
    ('iniciante', 'Iniciante'),
    ('intermediario', 'Intermediário'),
    ('avancado', 'Avançado'),
    ('kids', 'Kids')
]


class AlunoForm(FlaskForm):
    nome = StringField('Nome completo', validators=[
        DataRequired(message='O nome é obrigatório.'),
        Length(max=120, message='Máximo de 120 caracteres.')
    ])
    email = StringField('E-mail', validators=[
        DataRequired(message='O e-mail é obrigatório.'),
        Regexp(r'^[^@\s]+@[^@\s]+\.[^@\s]+$', message='Informe um e-mail válido.'),
        Length(max=120, message='Máximo de 120 caracteres.')
    ])
    telefone = StringField('Telefone / WhatsApp', validators=[Optional(), Length(max=20)])
    data_nascimento = DateField('Data de Nascimento', validators=[Optional()])
    senha = PasswordField('Senha de acesso', validators=[
        Optional(),
        Length(min=6, message='A senha deve ter no mínimo 6 caracteres.')
    ])
    nivel = SelectField('Nível de Habilidade', choices=NIVEIS, default='iniciante')
    categoria = SelectField('Categoria Competitiva', choices=CATEGORIAS_BEACH_TENNIS, default='D')
    lado_dominante = SelectField('Lado Dominante', choices=LADOS, default='destro')
    objetivo = SelectField('Objetivo Principal', choices=OBJETIVOS, default='lazer')
    observacoes = TextAreaField('Observações Médicas / Técnicas', validators=[Optional()])
    foto = FileField('Foto do Aluno', validators=[
        Optional(),
        FileAllowed(['jpg', 'jpeg', 'png', 'gif', 'webp'], 'Apenas imagens (JPG, PNG, GIF, WEBP)!')
    ])
    ativo = BooleanField('Aluno Ativo', default=True)
    submit = SubmitField('Salvar Aluno')

    def __init__(self, aluno_id=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._aluno_id = aluno_id

    def validate_email(self, field):
        from app.models import Aluno
        q = Usuario.query.filter_by(email=field.data.lower().strip())
        if self._aluno_id:
            aluno = db.session.get(Aluno, self._aluno_id)
            if aluno and aluno.usuario_id:
                q = q.filter(Usuario.id != aluno.usuario_id)
        if q.first():
            raise ValidationError('Este e-mail já está em uso por outro usuário.')


class ExercicioForm(FlaskForm):
    titulo = StringField('Título do Exercício', validators=[
        DataRequired(message='O título é obrigatório.'),
        Length(max=150, message='Máximo de 150 caracteres.')
    ])
    categoria = SelectField('Categoria', choices=CATEGORIAS_EXERCICIO, validators=[
        DataRequired(message='Selecione uma categoria.')
    ])
    nivel = SelectField('Nível Indicado', choices=NIVEIS_EXERCICIO, default='todos')
    duracao_minutos = IntegerField('Duração Estimada (minutos)', default=10, validators=[
        DataRequired(message='Informe a duração.'),
        NumberRange(min=1, max=180, message='Duração deve ser entre 1 e 180 minutos.')
    ])
    num_participantes = StringField('Participantes (ex: 2-4, Em duplas, Individual)', validators=[
        Optional(),
        Length(max=30, message='Máximo de 30 caracteres.')
    ])
    materiais = TextAreaField('Materiais Necessários (bolinhas, cones, fitas...)', validators=[Optional()])
    descricao = TextAreaField('Passo a Passo / Execução', validators=[
        DataRequired(message='A descrição do exercício é obrigatória.')
    ])
    objetivo_tecnico = TextAreaField('Objetivo Técnico / Tático', validators=[Optional()])
    variacoes = TextAreaField('Variações e Progressões', validators=[Optional()])
    erros_comuns = TextAreaField('Erros Comuns e Correções', validators=[Optional()])
    link_video = StringField('Link de Vídeo (YouTube)', validators=[
        Optional(),
        Length(max=300, message='Máximo de 300 caracteres.')
    ])
    imagem = FileField('Imagem Ilustrativa', validators=[
        Optional(),
        FileAllowed(['jpg', 'jpeg', 'png', 'gif', 'webp'], 'Apenas imagens (JPG, PNG, GIF, WEBP)!')
    ])
    ativo = BooleanField('Exercício Ativo', default=True)
    submit = SubmitField('Salvar Exercício')


class TurmaForm(FlaskForm):
    nome = StringField('Nome da Turma', validators=[
        DataRequired(message='O nome da turma é obrigatório.'),
        Length(max=100, message='Máximo de 100 caracteres.')
    ])
    nivel = SelectField('Nível da Turma', choices=NIVEIS_TURMA, default='iniciante')
    dias_semana = SelectMultipleField('Dias da Semana', choices=DIAS_SEMANA_CHOICES, validators=[
        DataRequired(message='Selecione pelo menos um dia da semana.')
    ])
    horario_inicio = TimeField('Horário de Início', validators=[
        DataRequired(message='Informe o horário de início.')
    ])
    horario_fim = TimeField('Horário de Término', validators=[
        DataRequired(message='Informe o horário de término.')
    ])
    local = StringField('Local / Quadra', validators=[
        DataRequired(message='O local/quadra é obrigatório.'),
        Length(max=150, message='Máximo de 150 caracteres.')
    ])
    vagas = IntegerField('Capacidade de Vagas', default=8, validators=[
        DataRequired(message='Informe a quantidade de vagas.'),
        NumberRange(min=1, max=50, message='Vagas devem ser entre 1 e 50.')
    ])
    alunos_ids = SelectMultipleField('Vincular Alunos à Turma', coerce=int, validators=[Optional()])
    ativa = BooleanField('Turma Ativa', default=True)
    submit = SubmitField('Salvar Turma')


class AulaForm(FlaskForm):
    turma_id = SelectField('Turma', coerce=int, validators=[DataRequired(message='Selecione a turma.')])
    data_hora = DateTimeLocalField('Data e Horário', format='%Y-%m-%dT%H:%M', validators=[
        DataRequired(message='Informe a data e horário da aula.')
    ])
    duracao_minutos = IntegerField('Duração da Aula (minutos)', default=60, validators=[
        DataRequired(message='Informe a duração.'),
        NumberRange(min=15, max=300, message='Duração deve ser entre 15 e 300 minutos.')
    ])
    objetivo = TextAreaField('Objetivo Principal da Aula', validators=[Optional()])
    observacoes = TextAreaField('Observações Gerais do Professor', validators=[Optional()])
    submit = SubmitField('Salvar Aula')


class GerarAulasRecorrentesForm(FlaskForm):
    turma_id = SelectField('Turma', coerce=int, validators=[DataRequired(message='Selecione a turma.')])
    data_inicio = DateField('Data Inicial', validators=[DataRequired(message='Informe a data de início.')])
    data_fim = DateField('Data Final', validators=[DataRequired(message='Informe a data final.')])
    duracao_minutos = IntegerField('Duração de cada aula (minutos)', default=60, validators=[
        DataRequired(), NumberRange(min=15, max=300)
    ])
    objetivo_padrao = StringField('Objetivo Padrão (opcional)', validators=[Optional()])
    submit = SubmitField('Gerar Grade de Aulas Recorrentes')


class CancelarAulaForm(FlaskForm):
    aviso_cancelamento = TextAreaField('Motivo do Cancelamento (visível aos alunos)', validators=[
        DataRequired(message='Informe o motivo do cancelamento para os alunos.')
    ])
    submit = SubmitField('Confirmar Cancelamento da Aula')


class RemarcarAulaForm(FlaskForm):
    nova_data_hora = DateTimeLocalField('Nova Data e Horário', format='%Y-%m-%dT%H:%M', validators=[
        DataRequired(message='Informe a nova data e horário.')
    ])
    motivo = TextAreaField('Motivo da Remarcação (visível aos alunos)', validators=[Optional()])
    submit = SubmitField('Confirmar Remarcação')


class AulaExercicioForm(FlaskForm):
    exercicio_id = SelectField('Exercício da Biblioteca', coerce=int, validators=[
        DataRequired(message='Selecione um exercício.')
    ])
    duracao_minutos = IntegerField('Duração neste Treino (minutos)', default=10, validators=[
        DataRequired(message='Informe a duração.'),
        NumberRange(min=1, max=120, message='Duração entre 1 e 120 minutos.')
    ])
    observacao = TextAreaField('Foco / Observação Técnica Específica', validators=[Optional()])
    submit = SubmitField('Adicionar ao Plano')


class AvaliacaoForm(FlaskForm):
    aluno_id = SelectField('Aluno Avaliado', coerce=int, validators=[
        DataRequired(message='Selecione o aluno.')
    ])
    categoria = SelectField('Categoria Avaliada', choices=CATEGORIAS_BEACH_TENNIS, default='D', validators=[
        DataRequired(message='Selecione a categoria da avaliação.')
    ])
    data = DateField('Data da Avaliação', validators=[
        DataRequired(message='Informe a data da avaliação.')
    ])
    
    # 11 Critérios Técnicos (Notas de 1 a 10)
    nota_saque = FloatField('Saque', default=5.0, validators=[DataRequired(), NumberRange(min=1, max=10)])
    nota_forehand = FloatField('Forehand', default=5.0, validators=[DataRequired(), NumberRange(min=1, max=10)])
    nota_backhand = FloatField('Backhand', default=5.0, validators=[DataRequired(), NumberRange(min=1, max=10)])
    nota_voleio = FloatField('Voleio', default=5.0, validators=[DataRequired(), NumberRange(min=1, max=10)])
    nota_smash = FloatField('Smash', default=5.0, validators=[DataRequired(), NumberRange(min=1, max=10)])
    nota_bandeja_defesa = FloatField('Bandeja / Defesa', default=5.0, validators=[DataRequired(), NumberRange(min=1, max=10)])
    nota_deslocamento = FloatField('Deslocamento e Mobilidade', default=5.0, validators=[DataRequired(), NumberRange(min=1, max=10)])
    nota_posicionamento_dupla = FloatField('Posicionamento em Dupla', default=5.0, validators=[DataRequired(), NumberRange(min=1, max=10)])
    nota_leitura_jogo = FloatField('Leitura de Jogo e Tomada de Decisão', default=5.0, validators=[DataRequired(), NumberRange(min=1, max=10)])
    nota_condicionamento = FloatField('Condicionamento Físico e Resistência', default=5.0, validators=[DataRequired(), NumberRange(min=1, max=10)])
    nota_mental_foco = FloatField('Aspecto Mental e Foco', default=5.0, validators=[DataRequired(), NumberRange(min=1, max=10)])

    # Pareceres descritivos
    pontos_fortes = TextAreaField('Pontos Fortes do Atleta', validators=[Optional()])
    pontos_melhorar = TextAreaField('Pontos a Desenvolver / Oportunidades', validators=[Optional()])
    metas_proximo_ciclo = TextAreaField('Metas para o Próximo Ciclo de Treinos', validators=[Optional()])
    comentarios = TextAreaField('Observações Gerais do Professor', validators=[Optional()])
    link_video_analise = StringField('Link de Vídeo para Análise de Movimento (YouTube)', validators=[
        Optional(),
        Length(max=300, message='Máximo de 300 caracteres.')
    ])
    submit = SubmitField('Salvar Avaliação Periódica')


# ── FORMS DO SITE PÚBLICO ──────────────────────────────────────────────
class ConfiguracaoSiteForm(FlaskForm):
    nome_professor = StringField('Nome do Professor', validators=[
        DataRequired(message='Informe o nome do professor.'),
        Length(max=120)
    ])
    idade_professor = StringField('Idade / Formação (ex: 22 anos. Estudante de Sistemas de Informação)', validators=[
        Optional(), Length(max=150)
    ])
    subtitulo_hero = StringField('Subtítulo do Hero', validators=[
        Optional(), Length(max=200)
    ])
    sobre_texto = TextAreaField('Texto "Sobre o Professor"', validators=[
        DataRequired(message='Informe o texto de apresentação.')
    ])
    whatsapp = StringField('WhatsApp para Contato (ex: 73999998888)', validators=[
        Optional(), Length(max=30)
    ])
    whatsapp_mensagem = StringField('Mensagem Padrão do WhatsApp', validators=[
        Optional(), Length(max=250)
    ])
    instagram = StringField('Instagram (@perfil ou link)', validators=[
        Optional(), Length(max=100)
    ])
    nome_quadra = StringField('Nome da Quadra / Arena', validators=[
        Optional(), Length(max=150)
    ])
    endereco = StringField('Endereço Completo', validators=[
        Optional(), Length(max=250)
    ])
    cidade = StringField('Cidade / UF', validators=[
        Optional(), Length(max=100)
    ])
    link_google_maps = StringField('Link do Google Maps', validators=[
        Optional(), Length(max=500)
    ])
    foto_professor = FileField('Foto do Professor', validators=[
        Optional(),
        FileAllowed(['jpg', 'jpeg', 'png', 'webp'], 'Apenas imagens JPG, PNG ou WEBP!')
    ])
    submit = SubmitField('Salvar Configurações do Site')


class ConquistaForm(FlaskForm):
    ano = IntegerField('Ano da Conquista', validators=[
        DataRequired(message='Informe o ano.'),
        NumberRange(min=2000, max=2100)
    ])
    colocacao = SelectField('Colocação', choices=[
        ('campeao', 'Campeão (1º Lugar)'),
        ('vice', 'Vice-campeão (2º Lugar)'),
        ('3_lugar', '3º Lugar')
    ], validators=[DataRequired()])
    categoria = StringField('Categoria (ex: Masculina B, Mista B, Open Masc A/B)', validators=[
        DataRequired(message='Informe a categoria.'),
        Length(max=100)
    ])
    titulo = StringField('Título / Descrição (ex: Campeão Masc B)', validators=[
        DataRequired(message='Informe o título.'),
        Length(max=150)
    ])
    torneio = StringField('Torneio / Circuito (ex: Circuito AIBT)', default='Circuito AIBT', validators=[
        Optional(), Length(max=150)
    ])
    destaque = BooleanField('Destacar na Linha do Tempo', default=False)
    ordem = IntegerField('Ordem de Exibição', default=0)
    submit = SubmitField('Salvar Conquista')


class TrofeuForm(FlaskForm):
    ano = IntegerField('Ano', default=date.today().year, validators=[
        DataRequired(message='Informe o ano.'),
        NumberRange(min=2000, max=2100)
    ])
    colocacao = SelectField('Colocação', choices=[
        ('campeao', 'Campeão (1º Lugar)'),
        ('vice', 'Vice-campeão (2º Lugar)'),
        ('3_lugar', '3º Lugar')
    ], validators=[DataRequired()])
    categoria = StringField('Categoria', validators=[
        DataRequired(message='Informe a categoria.'),
        Length(max=100)
    ])
    titulo = StringField('Título / Descrição', validators=[
        DataRequired(message='Informe o título.'),
        Length(max=150)
    ])
    torneio = StringField('Torneio / Circuito', default='Circuito AIBT', validators=[
        Optional(), Length(max=150)
    ])
    destaque = BooleanField('Destacar no perfil do aluno', default=False)
    ordem = IntegerField('Ordem de Exibição', default=0)
    submit = SubmitField('Salvar Troféu')


class ModalidadeForm(FlaskForm):
    nome = StringField('Nome da Modalidade (ex: Individual, Dupla, Turma, Kids)', validators=[
        DataRequired(message='Informe o nome da modalidade.'),
        Length(max=100)
    ])
    descricao = TextAreaField('Descrição dos Treinos', validators=[
        DataRequired(message='Informe a descrição.')
    ])
    icone = StringField('Ícone Bootstrap (ex: bi-person-fill, bi-people-fill, bi-emoji-smile)', default='bi-tsunami', validators=[
        Optional(), Length(max=50)
    ])
    publico_alvo = StringField('Público-alvo / Nível Indicado', validators=[
        Optional(), Length(max=150)
    ])
    duracao_estimada = StringField('Duração Estimada (ex: 60 min)', default='60 min', validators=[
        Optional(), Length(max=50)
    ])
    destaque = BooleanField('Destacar Card', default=False)
    ativo = BooleanField('Modalidade Ativa', default=True)
    ordem = IntegerField('Ordem de Exibição', default=0)
    submit = SubmitField('Salvar Modalidade')


class PlanoForm(FlaskForm):
    nome = StringField('Nome do Plano (ex: Mensal 2x na Semana, Avulso)', validators=[
        DataRequired(message='Informe o nome do plano.'),
        Length(max=100)
    ])
    descricao = TextAreaField('Itens / Descrição (cada linha um benefício)', validators=[
        Optional()
    ])
    preco = FloatField('Preço (R$)', validators=[
        DataRequired(message='Informe o valor do plano.')
    ])
    periodo = SelectField('Periodicidade', choices=[
        ('mensal', 'Mensal'),
        ('trimestral', 'Trimestral'),
        ('semestral', 'Semestral'),
        ('avulso', 'Aula Avulsa')
    ], default='mensal')
    aulas_por_semana = IntegerField('Aulas por Semana (opcional)', validators=[
        Optional(), NumberRange(min=1, max=7)
    ])
    destaque = BooleanField('Destacar Plano (Recomendado)', default=False)
    ativo = BooleanField('Plano Ativo', default=True)
    ordem = IntegerField('Ordem de Exibição', default=0)
    submit = SubmitField('Salvar Plano')


class DepoimentoForm(FlaskForm):
    nome = StringField('Nome do Aluno', validators=[
        DataRequired(message='Informe o nome.'),
        Length(max=100)
    ])
    texto = TextAreaField('Depoimento / Feedback', validators=[
        DataRequired(message='Informe o depoimento.')
    ])
    foto = FileField('Foto do Aluno (opcional)', validators=[
        Optional(),
        FileAllowed(['jpg', 'jpeg', 'png', 'webp'], 'Apenas imagens JPG, PNG ou WEBP!')
    ])
    aprovado = BooleanField('Aprovado para exibição no site', default=True)
    destaque = BooleanField('Destaque', default=False)
    ordem = IntegerField('Ordem', default=0)
    submit = SubmitField('Salvar Depoimento')


class GaleriaItemForm(FlaskForm):
    titulo = StringField('Título / Legenda Curta', validators=[
        DataRequired(message='Informe o título.'),
        Length(max=150)
    ])
    tipo = SelectField('Tipo de Mídia', choices=[
        ('imagem', 'Foto / Imagem'),
        ('video', 'Vídeo (YouTube)')
    ], default='imagem')
    arquivo = FileField('Arquivo de Imagem', validators=[
        Optional(),
        FileAllowed(['jpg', 'jpeg', 'png', 'webp'], 'Apenas imagens JPG, PNG ou WEBP!')
    ])
    url_video = StringField('Link do Vídeo (YouTube)', validators=[
        Optional(), Length(max=300)
    ])
    legenda = TextAreaField('Descrição / Legenda Detalhada', validators=[Optional()])
    destaque = BooleanField('Destaque na Galeria', default=False)
    ativo = BooleanField('Item Ativo', default=True)
    ordem = IntegerField('Ordem', default=0)
    submit = SubmitField('Salvar Item da Galeria')
