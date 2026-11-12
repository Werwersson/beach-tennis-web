from datetime import datetime
from ..extensions import db


class Depoimento(db.Model):
    __tablename__ = 'depoimentos'

    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(100), nullable=False)
    texto = db.Column(db.Text, nullable=False)
    foto = db.Column(db.String(200), nullable=True)
    aprovado = db.Column(db.Boolean, default=False)
    destaque = db.Column(db.Boolean, default=False)
    ordem = db.Column(db.Integer, default=0)
    criado_em = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f'<Depoimento {self.nome}>'
