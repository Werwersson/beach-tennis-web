"""tabelas de conquistas, modalidades, galeria e mensagens

Revision ID: f0cf57cd8b4a
Revises: b7c1d2e3f4a5
Create Date: 2026-11-12 16:22:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'f0cf57cd8b4a'
down_revision = 'b7c1d2e3f4a5'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'conquistas',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('ano', sa.Integer(), nullable=False),
        sa.Column('colocacao', sa.String(length=50), nullable=False),
        sa.Column('categoria', sa.String(length=100), nullable=False),
        sa.Column('titulo', sa.String(length=150), nullable=False),
        sa.Column('torneio', sa.String(length=150), nullable=True),
        sa.Column('destaque', sa.Boolean(), nullable=True),
        sa.Column('ordem', sa.Integer(), nullable=True),
        sa.Column('criado_em', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
    )
    with op.batch_alter_table('conquistas', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_conquistas_ano'), ['ano'], unique=False)

    op.create_table(
        'galeria_itens',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('titulo', sa.String(length=150), nullable=False),
        sa.Column('tipo', sa.String(length=20), nullable=True),
        sa.Column('arquivo', sa.String(length=250), nullable=True),
        sa.Column('url_video', sa.String(length=300), nullable=True),
        sa.Column('legenda', sa.Text(), nullable=True),
        sa.Column('destaque', sa.Boolean(), nullable=True),
        sa.Column('ativo', sa.Boolean(), nullable=True),
        sa.Column('ordem', sa.Integer(), nullable=True),
        sa.Column('criado_em', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
    )

    op.create_table(
        'mensagens_contato',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('nome', sa.String(length=120), nullable=False),
        sa.Column('telefone', sa.String(length=30), nullable=False),
        sa.Column('mensagem', sa.Text(), nullable=False),
        sa.Column('ip', sa.String(length=50), nullable=True),
        sa.Column('lida', sa.Boolean(), nullable=True),
        sa.Column('respondida', sa.Boolean(), nullable=True),
        sa.Column('criado_em', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
    )
    with op.batch_alter_table('mensagens_contato', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_mensagens_contato_criado_em'), ['criado_em'], unique=False)

    op.create_table(
        'modalidades',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('nome', sa.String(length=100), nullable=False),
        sa.Column('descricao', sa.Text(), nullable=False),
        sa.Column('icone', sa.String(length=50), nullable=True),
        sa.Column('publico_alvo', sa.String(length=150), nullable=True),
        sa.Column('duracao_estimada', sa.String(length=50), nullable=True),
        sa.Column('destaque', sa.Boolean(), nullable=True),
        sa.Column('ativo', sa.Boolean(), nullable=True),
        sa.Column('ordem', sa.Integer(), nullable=True),
        sa.Column('criado_em', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
    )


def downgrade():
    op.drop_table('modalidades')

    with op.batch_alter_table('mensagens_contato', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_mensagens_contato_criado_em'))
    op.drop_table('mensagens_contato')

    op.drop_table('galeria_itens')

    with op.batch_alter_table('conquistas', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_conquistas_ano'))
    op.drop_table('conquistas')
