from datetime import datetime, date
from ..extensions import db


class Partida(db.Model):
    """Partida de Beach Tennis com scout e estatísticas completas (BT Tracker)."""
    __tablename__ = 'partidas'

    id = db.Column(db.Integer, primary_key=True)
    data = db.Column(db.Date, nullable=False, default=date.today, index=True)
    titulo = db.Column(db.String(150), nullable=True)
    torneio = db.Column(db.String(150), nullable=True, default='Circuito AIBT')
    categoria = db.Column(db.String(50), nullable=True, default='Masculina B')
    fase = db.Column(db.String(50), nullable=True, default='Final')  # Final, Semifinal, Grupos, Treino
    local = db.Column(db.String(150), nullable=True, default='Arena Itabuna')

    # Dupla 1
    jogador1_nome = db.Column(db.String(100), nullable=False)
    jogador1_aluno_id = db.Column(db.Integer, db.ForeignKey('alunos.id'), nullable=True, index=True)
    jogador2_nome = db.Column(db.String(100), nullable=False)
    jogador2_aluno_id = db.Column(db.Integer, db.ForeignKey('alunos.id'), nullable=True, index=True)

    # Dupla 2
    jogador3_nome = db.Column(db.String(100), nullable=False)
    jogador3_aluno_id = db.Column(db.Integer, db.ForeignKey('alunos.id'), nullable=True, index=True)
    jogador4_nome = db.Column(db.String(100), nullable=False)
    jogador4_aluno_id = db.Column(db.Integer, db.ForeignKey('alunos.id'), nullable=True, index=True)

    # Placares dos Sets
    set1_dupla1 = db.Column(db.Integer, nullable=True, default=0)
    set1_dupla2 = db.Column(db.Integer, nullable=True, default=0)
    set2_dupla1 = db.Column(db.Integer, nullable=True, default=0)
    set2_dupla2 = db.Column(db.Integer, nullable=True, default=0)
    set3_dupla1 = db.Column(db.Integer, nullable=True, default=0)
    set3_dupla2 = db.Column(db.Integer, nullable=True, default=0)

    placar_detalhado = db.Column(db.String(100), nullable=True)
    dupla_vencedora = db.Column(db.Integer, default=1)  # 1 ou 2
    duracao_minutos = db.Column(db.Integer, nullable=True)
    observacoes = db.Column(db.Text, nullable=True)
    criado_em = db.Column(db.DateTime, default=datetime.utcnow)

    # Relacionamentos
    jogador1_aluno = db.relationship('Aluno', foreign_keys=[jogador1_aluno_id])
    jogador2_aluno = db.relationship('Aluno', foreign_keys=[jogador2_aluno_id])
    jogador3_aluno = db.relationship('Aluno', foreign_keys=[jogador3_aluno_id])
    jogador4_aluno = db.relationship('Aluno', foreign_keys=[jogador4_aluno_id])

    pontos = db.relationship(
        'PontoPartida',
        back_populates='partida',
        cascade='all, delete-orphan',
        order_by='PontoPartida.numero_ponto.asc()'
    )

    @property
    def dupla1_label(self):
        return f"{self.jogador1_nome} / {self.jogador2_nome}"

    @property
    def dupla2_label(self):
        return f"{self.jogador3_nome} / {self.jogador4_nome}"

    @property
    def placar_resumo(self):
        partes = []
        if self.set1_dupla1 is not None and self.set1_dupla2 is not None and (self.set1_dupla1 > 0 or self.set1_dupla2 > 0):
            partes.append(f"{self.set1_dupla1}x{self.set1_dupla2}")
        if self.set2_dupla1 is not None and self.set2_dupla2 is not None and (self.set2_dupla1 > 0 or self.set2_dupla2 > 0):
            partes.append(f"{self.set2_dupla1}x{self.set2_dupla2}")
        if self.set3_dupla1 is not None and self.set3_dupla2 is not None and (self.set3_dupla1 > 0 or self.set3_dupla2 > 0):
            partes.append(f"{self.set3_dupla1}x{self.set3_dupla2}")
        if self.placar_detalhado:
            return self.placar_detalhado
        return ' | '.join(partes) if partes else '0x0'

    def get_jogador_nome(self, num):
        nomes = {
            1: self.jogador1_nome,
            2: self.jogador2_nome,
            3: self.jogador3_nome,
            4: self.jogador4_nome,
        }
        return nomes.get(num, f"Jogador {num}")

    def __repr__(self):
        return f'<Partida {self.id} - {self.dupla1_label} vs {self.dupla2_label}>'


class PontoPartida(db.Model):
    """Registro detalhado de cada ponto da partida (lance a lance e estatística)."""
    __tablename__ = 'pontos_partida'

    id = db.Column(db.Integer, primary_key=True)
    partida_id = db.Column(db.Integer, db.ForeignKey('partidas.id'), nullable=False, index=True)
    numero_ponto = db.Column(db.Integer, nullable=False, index=True)

    set_num = db.Column(db.Integer, default=1)
    placar_texto = db.Column(db.String(50), nullable=True)  # ex: "0x0 15x0", "4x6 2x3 15x30"

    # Participantes do ponto
    sacador = db.Column(db.Integer, nullable=False)  # 1, 2, 3 ou 4
    dupla_vencedora = db.Column(db.Integer, nullable=False)  # 1 ou 2
    atleta_finalizador = db.Column(db.Integer, nullable=True)  # 1, 2, 3 ou 4 (quem fez o winner ou cometeu o erro)

    # Tipo de Desfecho
    # 'winner', 'forcou_erro', 'erro_nao_forcado', 'erro_saque', 'erro_devolucao', 'ace'
    tipo_desfecho = db.Column(db.String(40), nullable=False, index=True)
    tipo_golpe = db.Column(db.String(80), nullable=True)  # Smash, Lob Chutado com Forehand, Avanço, etc.

    # Análise de Saque
    posicao_sacador = db.Column(db.String(20), nullable=True)  # 'Direita', 'Esquerda'
    direcao_saque = db.Column(db.String(30), nullable=True)  # '1', '2', '3', '4', '5', 'Lob' -> Direita-3
    qualidade_saque = db.Column(db.String(20), nullable=True)  # 'Bom', 'Regular', 'Ruim', 'Ace', 'Erro'

    # Análise de Devolução
    direcao_devolucao = db.Column(db.String(40), nullable=True)  # 'No sacador', 'No parceiro', 'Meio', 'Lob'
    qualidade_devolucao = db.Column(db.String(20), nullable=True)  # 'Boa', 'Regular', 'Ruim', 'Winner', 'Erro'

    # Análise de Primeira Bola
    tipo_primeira_bola = db.Column(db.String(80), nullable=True)
    direcao_primeira_bola = db.Column(db.String(40), nullable=True)  # 'Cruzada', 'Paralela', 'Meio'
    qualidade_primeira_bola = db.Column(db.String(20), nullable=True)  # 'Boa', 'Regular', 'Ruim'

    # Informações Adicionais
    duracao_ponto = db.Column(db.String(20), default='Médio')  # 'Curto', 'Médio', 'Longo'
    situacao_adicional = db.Column(db.String(100), nullable=True)  # 'Bola na Fita', 'Bola na Linha', 'Furou a bola', 'Provocação'

    # Coordenadas do mapa de calor (0 a 100% da quadra)
    origem_x = db.Column(db.Float, nullable=True)
    origem_y = db.Column(db.Float, nullable=True)
    destino_x = db.Column(db.Float, nullable=True)
    destino_y = db.Column(db.Float, nullable=True)

    descricao_lance = db.Column(db.String(250), nullable=True)

    # Relacionamento
    partida = db.relationship('Partida', back_populates='pontos')

    def __repr__(self):
        return f'<Ponto {self.numero_ponto} Partida={self.partida_id} {self.tipo_desfecho}>'
