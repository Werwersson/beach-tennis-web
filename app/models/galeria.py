from datetime import datetime
from ..extensions import db


class GaleriaItem(db.Model):
    __tablename__ = 'galeria_itens'

    id = db.Column(db.Integer, primary_key=True)
    titulo = db.Column(db.String(150), nullable=False)
    tipo = db.Column(db.String(20), default='imagem')  # 'imagem' ou 'video'
    arquivo = db.Column(db.String(250), nullable=True)
    url_video = db.Column(db.String(300), nullable=True)
    legenda = db.Column(db.Text, nullable=True)
    destaque = db.Column(db.Boolean, default=False)
    ativo = db.Column(db.Boolean, default=True)
    ordem = db.Column(db.Integer, default=0)
    criado_em = db.Column(db.DateTime, default=datetime.utcnow)

    @property
    def url_video_embed(self):
        from app.utils.video import converter_para_embed
        return converter_para_embed(self.url_video)

    def __repr__(self):
        return f'<GaleriaItem {self.titulo} ({self.tipo})>'

