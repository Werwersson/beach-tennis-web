from datetime import datetime
from ..extensions import db


class Turma(db.Model):
    __tablename__ = 'turmas'

    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(100), nullable=False)
    nivel = db.Column(db.String(20), nullable=False, default='iniciante')  # iniciante, intermediario, avancado, kids
    dias_semana = db.Column(db.String(20), nullable=False)  # ex: "1,3,5" (seg, qua, sex)
    horario_inicio = db.Column(db.Time, nullable=False)
    horario_fim = db.Column(db.Time, nullable=False)
    local = db.Column(db.String(150), nullable=False)
    vagas = db.Column(db.Integer, default=10)
    ativa = db.Column(db.Boolean, default=True)
    criado_em = db.Column(db.DateTime, default=datetime.utcnow)

    # Relacionamentos
    alunos = db.relationship('TurmaAluno', back_populates='turma', cascade='all, delete-orphan')
    aulas = db.relationship('Aula', back_populates='turma', cascade='all, delete-orphan', order_by='Aula.data_hora.desc()')

    @property
    def vagas_disponiveis(self):
        ativos = sum(1 for ta in self.alunos if ta.ativo)
        return self.vagas - ativos

    @property
    def dias_semana_lista(self):
        return [int(d) for d in self.dias_semana.split(',') if d.strip()]

    @property
    def dias_semana_texto(self):
        nomes = {0: 'Seg', 1: 'Ter', 2: 'Qua', 3: 'Qui', 4: 'Sex', 5: 'Sáb', 6: 'Dom'}
        return ', '.join(nomes.get(d, '') for d in self.dias_semana_lista)

    def __repr__(self):
        return f'<Turma {self.nome}>'


class TurmaAluno(db.Model):
    __tablename__ = 'turma_alunos'

    id = db.Column(db.Integer, primary_key=True)
    turma_id = db.Column(db.Integer, db.ForeignKey('turmas.id'), nullable=False, index=True)
    aluno_id = db.Column(db.Integer, db.ForeignKey('alunos.id'), nullable=False, index=True)
    data_entrada = db.Column(db.Date, default=datetime.utcnow)
    ativo = db.Column(db.Boolean, default=True)

    __table_args__ = (db.UniqueConstraint('turma_id', 'aluno_id', name='uq_turma_aluno'),)

    # Relacionamentos
    turma = db.relationship('Turma', back_populates='alunos')
    aluno = db.relationship('Aluno', back_populates='turmas')

    def __repr__(self):
        return f'<TurmaAluno turma={self.turma_id} aluno={self.aluno_id}>'
