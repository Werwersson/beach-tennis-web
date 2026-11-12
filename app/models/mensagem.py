from datetime import datetime
from ..extensions import db


class MensagemContato(db.Model):
    __tablename__ = 'mensagens_contato'

    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(120), nullable=False)
    telefone = db.Column(db.String(30), nullable=False)
    mensagem = db.Column(db.Text, nullable=False)
    ip = db.Column(db.String(50), nullable=True)
    lida = db.Column(db.Boolean, default=False)
    respondida = db.Column(db.Boolean, default=False)
    criado_em = db.Column(db.DateTime, default=datetime.utcnow, index=True)

    def __repr__(self):
        return f'<MensagemContato de {self.nome}>'

