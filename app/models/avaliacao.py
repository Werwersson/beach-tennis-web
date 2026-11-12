from datetime import datetime
from ..extensions import db
from .categoria import (
    CATEGORIAS_BEACH_TENNIS,
    normalizar_categoria,
    categoria_label as _categoria_label,
    peso_categoria as _peso_categoria,
    ordem_categoria as _ordem_categoria,
    calcular_indice,
)

CRITERIOS_AVALIACAO = [
    ('saque', 'Saque'),
    ('forehand', 'Forehand'),
    ('backhand', 'Backhand'),
    ('voleio', 'Voleio'),
    ('smash', 'Smash'),
    ('bandeja_defesa', 'Bandeja/Defesa'),
    ('deslocamento', 'Deslocamento'),
    ('posicionamento_dupla', 'Posicionamento em Dupla'),
    ('leitura_jogo', 'Leitura de Jogo'),
    ('condicionamento', 'Condicionamento Físico'),
    ('mental_foco', 'Aspecto Mental/Foco'),
]


class Avaliacao(db.Model):
    __tablename__ = 'avaliacoes'

    id = db.Column(db.Integer, primary_key=True)
    aluno_id = db.Column(db.Integer, db.ForeignKey('alunos.id'), nullable=False, index=True)
    data = db.Column(db.Date, nullable=False, index=True)
    # Categoria em que o atleta foi avaliado neste ciclo (D, C, B, A, Open).
    categoria = db.Column(db.String(10), nullable=True, index=True)
    comentarios = db.Column(db.Text, nullable=True)
    pontos_fortes = db.Column(db.Text, nullable=True)
    pontos_melhorar = db.Column(db.Text, nullable=True)
    metas_proximo_ciclo = db.Column(db.Text, nullable=True)
    link_video_analise = db.Column(db.String(300), nullable=True)
    criado_em = db.Column(db.DateTime, default=datetime.utcnow)

    # Relacionamentos
    aluno = db.relationship('Aluno', back_populates='avaliacoes')
    notas = db.relationship('AvaliacaoNota', back_populates='avaliacao', cascade='all, delete-orphan')

    def get_nota(self, criterio):
        for n in self.notas:
            if n.criterio == criterio:
                return n.nota
        return None

    @property
    def media_exata(self):
        """Média sem arredondamento, usada no cálculo do índice."""
        if not self.notas:
            return 0.0
        return sum(n.nota for n in self.notas) / len(self.notas)

    @property
    def media(self):
        if not self.notas:
            return 0
        return round(self.media_exata, 1)

    @property
    def categoria_efetiva(self):
        """Categoria do ciclo; avaliações antigas sem categoria caem em D."""
        return normalizar_categoria(self.categoria)

    @property
    def categoria_label(self):
        return _categoria_label(self.categoria_efetiva)

    @property
    def categoria_curta(self):
        return normalizar_categoria(self.categoria_efetiva)

    @property
    def peso_categoria(self):
        return _peso_categoria(self.categoria_efetiva)

    @property
    def ordem_categoria(self):
        return _ordem_categoria(self.categoria_efetiva)

    @property
    def indice_tecnico(self):
        """Índice Técnico do ciclo (0 a 100), já corrigido pelo peso da categoria."""
        return calcular_indice(self.media_exata, self.categoria_efetiva)

    def get_indice(self, criterio):
        """Índice Técnico (0 a 100) de um critério específico."""
        nota = self.get_nota(criterio)
        if nota is None:
            return None
        return calcular_indice(nota, self.categoria_efetiva)

    def __repr__(self):
        return f'<Avaliacao aluno={self.aluno_id} data={self.data} categoria={self.categoria}>'


class AvaliacaoNota(db.Model):
    __tablename__ = 'avaliacao_notas'

    id = db.Column(db.Integer, primary_key=True)
    avaliacao_id = db.Column(db.Integer, db.ForeignKey('avaliacoes.id'), nullable=False, index=True)
    criterio = db.Column(db.String(30), nullable=False)
    nota = db.Column(db.Float, nullable=False)

    __table_args__ = (db.UniqueConstraint('avaliacao_id', 'criterio', name='uq_avaliacao_criterio'),)

    # Relacionamentos
    avaliacao = db.relationship('Avaliacao', back_populates='notas')

    def __repr__(self):
        return f'<AvaliacaoNota criterio={self.criterio} nota={self.nota}>'
