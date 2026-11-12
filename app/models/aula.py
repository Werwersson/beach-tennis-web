from datetime import datetime
from ..extensions import db


class Aula(db.Model):
    __tablename__ = 'aulas'

    id = db.Column(db.Integer, primary_key=True)
    turma_id = db.Column(db.Integer, db.ForeignKey('turmas.id'), nullable=False, index=True)
    data_hora = db.Column(db.DateTime, nullable=False, index=True)
    duracao_minutos = db.Column(db.Integer, default=60)
    objetivo = db.Column(db.Text, nullable=True)
    observacoes = db.Column(db.Text, nullable=True)
    status = db.Column(db.String(20), default='agendada')  # agendada, realizada, cancelada, remarcada
    aula_original_id = db.Column(db.Integer, db.ForeignKey('aulas.id'), nullable=True)  # para remarcações
    aviso_cancelamento = db.Column(db.Text, nullable=True)
    criado_em = db.Column(db.DateTime, default=datetime.utcnow)

    # Relacionamentos
    turma = db.relationship('Turma', back_populates='aulas')
    exercicios = db.relationship('AulaExercicio', back_populates='aula', order_by='AulaExercicio.ordem', cascade='all, delete-orphan')
    presencas = db.relationship('Presenca', back_populates='aula', cascade='all, delete-orphan')
    aula_original = db.relationship('Aula', remote_side='Aula.id', foreign_keys=[aula_original_id])

    def __repr__(self):
        return f'<Aula turma={self.turma_id} data={self.data_hora}>'


class AulaExercicio(db.Model):
    __tablename__ = 'aula_exercicios'

    id = db.Column(db.Integer, primary_key=True)
    aula_id = db.Column(db.Integer, db.ForeignKey('aulas.id'), nullable=False, index=True)
    exercicio_id = db.Column(db.Integer, db.ForeignKey('exercicios.id'), nullable=False, index=True)
    ordem = db.Column(db.Integer, nullable=False, default=0)
    duracao_minutos = db.Column(db.Integer, nullable=True)
    observacao = db.Column(db.Text, nullable=True)

    # Relacionamentos
    aula = db.relationship('Aula', back_populates='exercicios')
    exercicio = db.relationship('Exercicio', back_populates='aulas')

    def __repr__(self):
        return f'<AulaExercicio aula={self.aula_id} ex={self.exercicio_id} ordem={self.ordem}>'
