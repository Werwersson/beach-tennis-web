import sqlite3

dbs = [
    'd:\\Projetos\\Beach_Tennis_Web\\beach_tennis.db',
    'd:\\Projetos\\Beach_Tennis_Web\\instance\\beach_tennis.db',
]

for db_path in dbs:
    print(f"\n=== {db_path} ===")
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()

    # Reordenar os 3 itens de 2025:
    # Ordem desejada (do topo para o fim da timeline):
    #   Vice Masc B (id=15)   -> ordem=14
    #   Vice Open Masc (id=16) -> ordem=15
    #   Campeao Masc D (id=14) -> ordem=16  (ultimo = ponto de partida)
    updates = [
        (14, 14),  # Vice Masc B
        (15, 15),  # Vice Open Masc
        (16, 16),  # Campeao Masc D - ultimo
    ]
    # Mas o id=14 é Masc D, id=15 é Vice Masc B, id=16 é Vice Open
    # Reordenar:
    #   id=15 (Vice Masc B)    -> ordem=14
    #   id=16 (Vice Open Masc) -> ordem=15
    #   id=14 (Campeao Masc D) -> ordem=16
    reorder = [
        (14, 15),   # id=15, nova ordem=14
        (15, 16),   # id=16, nova ordem=15
        (16, 14),   # id=14 (Masc D), nova ordem=16
    ]
    for nova_ordem, item_id in reorder:
        cur.execute("UPDATE conquistas SET ordem=? WHERE id=?", (nova_ordem, item_id))
        cur.execute("SELECT id, ano, categoria, colocacao, ordem FROM conquistas WHERE id=?", (item_id,))
        r = cur.fetchone()
        print(f"  id={r[0]} ano={r[1]} cat={r[2]} col={r[3]} ordem={r[4]}")

    conn.commit()
    conn.close()
    print("  Salvo!")

