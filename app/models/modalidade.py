from datetime import datetime
from ..extensions import db


class Modalidade(db.Model):
    __tablename__ = 'modalidades'

    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(100), nullable=False)
    descricao = db.Column(db.Text, nullable=False)
    icone = db.Column(db.String(50), default='bi-tsunami')
    publico_alvo = db.Column(db.String(150), nullable=True)
    duracao_estimada = db.Column(db.String(50), default='60 a 90 min')
    destaque = db.Column(db.Boolean, default=False)
    ativo = db.Column(db.Boolean, default=True)
    ordem = db.Column(db.Integer, default=0)
    criado_em = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f'<Modalidade {self.nome}>'

