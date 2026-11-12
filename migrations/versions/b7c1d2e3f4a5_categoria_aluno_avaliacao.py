"""categoria do aluno e da avaliacao

Revision ID: b7c1d2e3f4a5
Revises: a329c8f41ee5
Create Date: 2026-11-12 16:10:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'b7c1d2e3f4a5'
down_revision = 'a329c8f41ee5'
branch_labels = None
depends_on = None


def upgrade():
    # Categoria competitiva atual do aluno. O padrão é D (base da escada).
    with op.batch_alter_table('alunos', schema=None) as batch_op:
        batch_op.add_column(sa.Column('categoria', sa.String(length=10), nullable=False, server_default='D'))
    with op.batch_alter_table('alunos', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_alunos_categoria'), ['categoria'], unique=False)

    # Categoria em que o atleta foi avaliado em cada ciclo.
    with op.batch_alter_table('avaliacoes', schema=None) as batch_op:
        batch_op.add_column(sa.Column('categoria', sa.String(length=10), nullable=True))
    with op.batch_alter_table('avaliacoes', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_avaliacoes_categoria'), ['categoria'], unique=False)

    # Backfill coerente com o nível já cadastrado:
    # iniciante -> D, intermediário -> C, avançado -> B.
    op.execute("""
        UPDATE alunos
        SET categoria = CASE nivel
            WHEN 'iniciante' THEN 'D'
            WHEN 'intermediario' THEN 'C'
            WHEN 'avancado' THEN 'B'
            ELSE 'D'
        END
    """)
    # As avaliações herdam a categoria atual do aluno; o professor pode ajustar
    # ciclos históricos depois, pela tela de edição da avaliação.
    op.execute("""
        UPDATE avaliacoes
        SET categoria = COALESCE(
            (SELECT categoria FROM alunos WHERE alunos.id = avaliacoes.aluno_id),
            'D'
        )
    """)


def downgrade():
    with op.batch_alter_table('avaliacoes', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_avaliacoes_categoria'))
        batch_op.drop_column('categoria')

    with op.batch_alter_table('alunos', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_alunos_categoria'))
        batch_op.drop_column('categoria')
