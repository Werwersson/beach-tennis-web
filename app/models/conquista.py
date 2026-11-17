from datetime import datetime
from ..extensions import db


class Conquista(db.Model):
    __tablename__ = 'conquistas'

    id = db.Column(db.Integer, primary_key=True)
    ano = db.Column(db.Integer, nullable=False, index=True)
    colocacao = db.Column(db.String(50), nullable=False)  # 'campeao', 'vice', '3_lugar'
    categoria = db.Column(db.String(100), nullable=False)
    titulo = db.Column(db.String(150), nullable=False)
    torneio = db.Column(db.String(150), nullable=True, default='Circuito AIBT')
    destaque = db.Column(db.Boolean, default=False)
    ordem = db.Column(db.Integer, default=0)
    criado_em = db.Column(db.DateTime, default=datetime.utcnow)

    @property
    def icone(self):
        if self.colocacao == 'campeao':
            return 'bi-trophy-fill text-warning'
        elif self.colocacao == 'vice':
            return 'bi-award-fill text-secondary'
        return 'bi-award text-bronze'

    @property
    def badge_class(self):
        if self.colocacao == 'campeao':
            return 'bg-warning text-dark'
        elif self.colocacao == 'vice':
            return 'bg-secondary text-white'
        return 'bg-light text-dark border'

    @property
    def colocacao_label(self):
        return {
            'campeao': 'Campeão',
            'vice': 'Vice-campeão',
            '3_lugar': '3º Lugar',
        }.get(self.colocacao, self.colocacao or 'Resultado')

    def __repr__(self):
        return f'<Conquista {self.ano} {self.titulo}>'


class TrofeuAluno(db.Model):
    """Troféu/conquista individual de um aluno (privado da área do aluno)."""
    __tablename__ = 'trofeus_aluno'

    id = db.Column(db.Integer, primary_key=True)
    aluno_id = db.Column(db.Integer, db.ForeignKey('alunos.id'), nullable=False, index=True)
    ano = db.Column(db.Integer, nullable=False, index=True)
    colocacao = db.Column(db.String(50), nullable=False)  # 'campeao', 'vice', '3_lugar'
    categoria = db.Column(db.String(100), nullable=False)
    titulo = db.Column(db.String(150), nullable=False)
    torneio = db.Column(db.String(150), nullable=True)
    destaque = db.Column(db.Boolean, default=False)
    ordem = db.Column(db.Integer, default=0)
    criado_em = db.Column(db.DateTime, default=datetime.utcnow)

    aluno = db.relationship('Aluno', back_populates='trofeus')

    @property
    def icone(self):
        if self.colocacao == 'campeao':
            return 'bi-trophy-fill text-warning'
        elif self.colocacao == 'vice':
            return 'bi-award-fill text-secondary'
        return 'bi-award text-bronze'

    @property
    def badge_class(self):
        if self.colocacao == 'campeao':
            return 'bg-warning text-dark'
        elif self.colocacao == 'vice':
            return 'bg-secondary text-white'
        return 'bg-light text-dark border'

    @property
    def colocacao_label(self):
        return {
            'campeao': 'Campeão',
            'vice': 'Vice-campeão',
            '3_lugar': '3º Lugar',
        }.get(self.colocacao, self.colocacao or 'Resultado')

    def __repr__(self):
        return f'<TrofeuAluno aluno={self.aluno_id} {self.ano} {self.titulo}>'


