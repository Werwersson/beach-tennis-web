from datetime import datetime
from ..extensions import db


class ConfiguracaoSite(db.Model):
    __tablename__ = 'configuracoes_site'

    id = db.Column(db.Integer, primary_key=True)
    chave = db.Column(db.String(100), unique=True, nullable=False, index=True)
    valor = db.Column(db.Text, nullable=True)
    descricao = db.Column(db.String(200), nullable=True)
    atualizado_em = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    @classmethod
    def get(cls, chave, default=None):
        config = cls.query.filter_by(chave=chave).first()
        return config.valor if config else default

    @classmethod
    def set(cls, chave, valor, descricao=None):
        config = cls.query.filter_by(chave=chave).first()
        if config:
            config.valor = valor
        else:
            config = cls(chave=chave, valor=valor, descricao=descricao)
            db.session.add(config)
        db.session.commit()
        return config

    def __repr__(self):
        return f'<ConfiguracaoSite {self.chave}>'


class Plano(db.Model):
    __tablename__ = 'planos'

    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(100), nullable=False)
    descricao = db.Column(db.Text, nullable=True)
    preco = db.Column(db.Float, nullable=False)
    periodo = db.Column(db.String(30), default='mensal')  # mensal, trimestral, avulso
    aulas_por_semana = db.Column(db.Integer, nullable=True)
    destaque = db.Column(db.Boolean, default=False)
    ativo = db.Column(db.Boolean, default=True)
    ordem = db.Column(db.Integer, default=0)
    criado_em = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f'<Plano {self.nome}>'
