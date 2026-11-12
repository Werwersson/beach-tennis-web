import sqlite3

dbs = [
    'd:\\Projetos\\Beach_Tennis_Web\\beach_tennis.db',
    'd:\\Projetos\\Beach_Tennis_Web\\instance\\beach_tennis.db',
]

for db_path in dbs:
    print(f"\n=== {db_path} ===")
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()

    # Verificar se coluna ja existe
    cur.execute("PRAGMA table_info(avaliacoes)")
    cols = [row[1] for row in cur.fetchall()]
    print(f"  Colunas atuais: {cols}")

    if 'categoria' not in cols:
        cur.execute("ALTER TABLE avaliacoes ADD COLUMN categoria VARCHAR(10)")
        conn.commit()
        print("  Coluna 'categoria' adicionada!")
    else:
        print("  Coluna 'categoria' ja existe.")

    conn.close()

