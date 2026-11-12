import sqlite3

dbs = [
    'd:\\Projetos\\Beach_Tennis_Web\\beach_tennis.db',
    'd:\\Projetos\\Beach_Tennis_Web\\instance\\beach_tennis.db',
]

for db_path in dbs:
    print(f"\n=== {db_path} ===")
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    cur.execute("SELECT id, ano, categoria, colocacao, torneio, ordem FROM conquistas ORDER BY ano DESC, ordem ASC, id ASC")
    rows = cur.fetchall()
    for i, r in enumerate(rows):
        print(f"  [{i+1}] id={r[0]} ano={r[1]} cat={r[2]} col={r[3]} ordem={r[5]}")
    conn.close()

