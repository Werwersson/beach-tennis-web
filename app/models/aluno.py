from datetime import datetime
from ..extensions import db
from .categoria import (
    categoria_label as _categoria_label,
    normalizar_categoria,
    peso_categoria as _peso_categoria,
    ordem_categoria as _ordem_categoria,
)


class Aluno(db.Model):
    __tablename__ = 'alunos'

    id = db.Column(db.Integer, primary_key=True)
    usuario_id = db.Column(db.Integer, db.ForeignKey('usuarios.id'), unique=True, nullable=False, index=True)
    nome = db.Column(db.String(120), nullable=False)
    telefone = db.Column(db.String(20), nullable=True)
    data_nascimento = db.Column(db.Date, nullable=True)
    nivel = db.Column(db.String(20), default='iniciante')  # iniciante, intermediario, avancado
    # Categoria competitiva atual (D, C, B, A, Open). Cada avaliação guarda a
    # categoria daquele ciclo; este campo serve de atalho e valor padrão.
    categoria = db.Column(db.String(10), default='D', nullable=False, index=True, server_default='D')
    lado_dominante = db.Column(db.String(10), default='destro')  # destro, canhoto
    objetivo = db.Column(db.String(20), default='lazer')  # lazer, competicao, condicionamento
    foto = db.Column(db.String(200), nullable=True)
    observacoes = db.Column(db.Text, nullable=True)
    cor_fundo = db.Column(db.String(30), default='#F8F6F2', nullable=True)
    ativo = db.Column(db.Boolean, default=True, nullable=False)
    criado_em = db.Column(db.DateTime, default=datetime.utcnow)

    # Relacionamentos
    usuario = db.relationship('Usuario', back_populates='aluno')
    turmas = db.relationship('TurmaAluno', back_populates='aluno', cascade='all, delete-orphan')
    presencas = db.relationship('Presenca', back_populates='aluno', cascade='all, delete-orphan')
    avaliacoes = db.relationship('Avaliacao', back_populates='aluno', cascade='all, delete-orphan', order_by='Avaliacao.data.desc()')
    metas = db.relationship('MetaAluno', back_populates='aluno', cascade='all, delete-orphan', order_by='MetaAluno.criado_em.desc()')
    trofeus = db.relationship('TrofeuAluno', back_populates='aluno', cascade='all, delete-orphan', order_by='TrofeuAluno.ano.desc(), TrofeuAluno.ordem.asc()')

    @property
    def categoria_efetiva(self):
        return normalizar_categoria(self.categoria)

    @property
    def categoria_curta(self):
        return normalizar_categoria(self.categoria)

    @property
    def categoria_label(self):
        return _categoria_label(self.categoria_efetiva)

    @property
    def peso_categoria(self):
        return _peso_categoria(self.categoria_efetiva)

    @property
    def ordem_categoria(self):
        return _ordem_categoria(self.categoria_efetiva)

    def __repr__(self):
        return f'<Aluno {self.nome}>'


class MetaAluno(db.Model):
    __tablename__ = 'metas_aluno'

    id = db.Column(db.Integer, primary_key=True)
    aluno_id = db.Column(db.Integer, db.ForeignKey('alunos.id'), nullable=False, index=True)
    descricao = db.Column(db.Text, nullable=False)
    prazo = db.Column(db.Date, nullable=True)
    concluida = db.Column(db.Boolean, default=False)
    criado_em = db.Column(db.DateTime, default=datetime.utcnow)

    # Relacionamentos
    aluno = db.relationship('Aluno', back_populates='metas')

    def __repr__(self):
        return f'<MetaAluno aluno_id={self.aluno_id}>'
