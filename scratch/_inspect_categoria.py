import sqlite3
import os

BASE = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
for name in ('beach_tennis.db', os.path.join('instance', 'beach_tennis.db')):
    path = os.path.join(BASE, name)
    print('==', path)
    conn = sqlite3.connect(path)
    cur = conn.cursor()
    cur.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
    tables = [r[0] for r in cur.fetchall()]
    print('tabelas:', tables)
    for t in ('usuarios', 'alunos', 'avaliacoes', 'avaliacao_notas'):
        if t in tables:
            cur.execute(f'SELECT COUNT(*) FROM {t}')
            print(t, cur.fetchone()[0])
    cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='alembic_version'")
    print('alembic_version:', cur.fetchall())
    cur.execute('SELECT id, nome, email, perfil FROM usuarios')
    print('usuarios:', cur.fetchall())
    if 'alunos' in tables:
        cur.execute('SELECT id, nome, nivel FROM alunos')
        print('alunos:', cur.fetchall())
    if 'avaliacoes' in tables:
        cur.execute('SELECT id, aluno_id, data FROM avaliacoes ORDER BY data')
        print('avaliacoes:', cur.fetchall())
    conn.close()
