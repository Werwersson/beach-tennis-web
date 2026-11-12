from datetime import datetime
from ..extensions import db

STATUS_PRESENCA = [
    ('presente', 'Presente'),
    ('falta', 'Falta'),
    ('falta_justificada', 'Falta Justificada'),
    ('reposicao', 'Reposição'),
    ('confirmado', 'Confirmado (aguardando aula)'),
    ('ausencia_avisada', 'Ausência Avisada'),
]


class Presenca(db.Model):
    __tablename__ = 'presencas'

    id = db.Column(db.Integer, primary_key=True)
    aula_id = db.Column(db.Integer, db.ForeignKey('aulas.id'), nullable=False, index=True)
    aluno_id = db.Column(db.Integer, db.ForeignKey('alunos.id'), nullable=False, index=True)
    status = db.Column(db.String(20), nullable=False, default='falta')
    justificativa = db.Column(db.Text, nullable=True)
    registrado_em = db.Column(db.DateTime, default=datetime.utcnow)

    __table_args__ = (db.UniqueConstraint('aula_id', 'aluno_id', name='uq_presenca_aula_aluno'),)

    # Relacionamentos
    aula = db.relationship('Aula', back_populates='presencas')
    aluno = db.relationship('Aluno', back_populates='presencas')

    def __repr__(self):
        return f'<Presenca aula={self.aula_id} aluno={self.aluno_id} status={self.status}>'
