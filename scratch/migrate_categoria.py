"""Migração idempotente para as colunas de categoria.

Este projeto foi criado com ``db.create_all()`` e os bancos de desenvolvimento já
existem sem ``alembic_version``. Para não obrigar um ``flask db upgrade`` (que
falharia em bancos não versionados), este script aplica as mesmas mudanças da
revisão ``b7c1d2e3f4a5`` diretamente nos bancos SQLite locais.

Uso:
    python scratch/migrate_categoria.py            # adiciona colunas/índices
    python scratch/migrate_categoria.py --backfill # refaz o preenchimento inicial
"""
import os
import sqlite3
import sys

BASE = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
BANCOS = [
    os.path.join(BASE, 'beach_tennis.db'),
    os.path.join(BASE, 'instance', 'beach_tennis.db'),
]

BACKFILL_ALUNO = """
UPDATE alunos
SET categoria = CASE nivel
    WHEN 'iniciante' THEN 'D'
    WHEN 'intermediario' THEN 'C'
    WHEN 'avancado' THEN 'B'
    ELSE 'D'
END
"""

BACKFILL_AVALIACAO = """
UPDATE avaliacoes
SET categoria = COALESCE(
    (SELECT categoria FROM alunos WHERE alunos.id = avaliacoes.aluno_id),
    'D'
)
"""


def colunas(cur, tabela):
    cur.execute(f'PRAGMA table_info({tabela})')
    return [row[1] for row in cur.fetchall()]


def migrar(caminho, forcar_backfill=False):
    if not os.path.exists(caminho):
        print(f'[skip] {caminho} não existe')
        return
    print(f'== {caminho}')
    conn = sqlite3.connect(caminho)
    cur = conn.cursor()

    # 1. alunos.categoria
    adicionou_aluno = False
    if 'categoria' not in colunas(cur, 'alunos'):
        cur.execute("ALTER TABLE alunos ADD COLUMN categoria VARCHAR(10) NOT NULL DEFAULT 'D'")
        adicionou_aluno = True
        print('  + alunos.categoria')
    else:
        print('  = alunos.categoria já existe')

    # 2. avaliacoes.categoria
    adicionou_avaliacao = False
    if 'categoria' not in colunas(cur, 'avaliacoes'):
        cur.execute('ALTER TABLE avaliacoes ADD COLUMN categoria VARCHAR(10)')
        adicionou_avaliacao = True
        print('  + avaliacoes.categoria')
    else:
        print('  = avaliacoes.categoria já existe')

    # 3. Backfill inicial (só quando a coluna acabou de ser criada ou sob demanda)
    if adicionou_aluno or forcar_backfill:
        cur.execute(BACKFILL_ALUNO)
        print(f'  alunos classificados: {cur.rowcount}')
    if adicionou_avaliacao or forcar_backfill:
        cur.execute(BACKFILL_AVALIACAO)
        print(f'  avaliações classificadas: {cur.rowcount}')

    # 4. índices
    cur.execute('CREATE INDEX IF NOT EXISTS ix_alunos_categoria ON alunos (categoria)')
    cur.execute('CREATE INDEX IF NOT EXISTS ix_avaliacoes_categoria ON avaliacoes (categoria)')

    conn.commit()
    conn.close()


if __name__ == '__main__':
    forcar = '--backfill' in sys.argv
    for banco in BANCOS:
        migrar(banco, forcar_backfill=forcar)
    print('\nMigração concluída.')
