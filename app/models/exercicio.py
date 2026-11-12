from datetime import datetime
from ..extensions import db

CATEGORIAS_EXERCICIO = [
    ('aquecimento', 'Aquecimento'),
    ('saque', 'Saque'),
    ('voleio', 'Voleio'),
    ('smash', 'Smash'),
    ('bandeja_defesa', 'Bandeja/Defesa'),
    ('forehand', 'Forehand'),
    ('backhand', 'Backhand'),
    ('deslocamento', 'Deslocamento e Posicionamento'),
    ('dupla', 'Jogo em Dupla'),
    ('tatica', 'Tática'),
    ('condicionamento', 'Condicionamento Físico'),
    ('alongamento', 'Alongamento/Volta à Calma'),
]

NIVEIS_EXERCICIO = [
    ('iniciante', 'Iniciante'),
    ('intermediario', 'Intermediário'),
    ('avancado', 'Avançado'),
    ('todos', 'Todos os Níveis'),
]


class Exercicio(db.Model):
    __tablename__ = 'exercicios'

    id = db.Column(db.Integer, primary_key=True)
    titulo = db.Column(db.String(150), nullable=False)
    categoria = db.Column(db.String(30), nullable=False, index=True)
    nivel = db.Column(db.String(20), nullable=False, default='todos', index=True)
    duracao_minutos = db.Column(db.Integer, default=10)
    num_participantes = db.Column(db.String(30), nullable=True)  # ex: "2-4"
    materiais = db.Column(db.Text, nullable=True)
    descricao = db.Column(db.Text, nullable=False)
    objetivo_tecnico = db.Column(db.Text, nullable=True)
    variacoes = db.Column(db.Text, nullable=True)
    erros_comuns = db.Column(db.Text, nullable=True)
    link_video = db.Column(db.String(300), nullable=True)
    imagem = db.Column(db.String(200), nullable=True)
    ativo = db.Column(db.Boolean, default=True)
    criado_em = db.Column(db.DateTime, default=datetime.utcnow)
    atualizado_em = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relacionamentos
    aulas = db.relationship('AulaExercicio', back_populates='exercicio', cascade='all, delete-orphan')

    @property
    def categoria_nome(self):
        return dict(CATEGORIAS_EXERCICIO).get(self.categoria, self.categoria)

    @property
    def nivel_nome(self):
        return dict(NIVEIS_EXERCICIO).get(self.nivel, self.nivel)

    def __repr__(self):
        return f'<Exercicio {self.titulo}>'
