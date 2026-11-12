import sqlite3

# Atualizar AMBOS os bancos para garantir
dbs = [
    'd:\\Projetos\\Beach_Tennis_Web\\beach_tennis.db',
    'd:\\Projetos\\Beach_Tennis_Web\\instance\\beach_tennis.db',
]

updates = {
    'whatsapp': '5573999969999',
    'instagram': 'eversonvicktor',
}

for db_path in dbs:
    print(f"\n=== {db_path} ===")
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()

    for chave, valor in updates.items():
        cur.execute("SELECT valor FROM configuracoes_site WHERE chave=?", (chave,))
        row = cur.fetchone()
        if row:
            print(f"  Antes  - {chave}: {row[0]}")
            cur.execute("UPDATE configuracoes_site SET valor=? WHERE chave=?", (valor, chave))
        else:
            cur.execute("INSERT INTO configuracoes_site (chave, valor) VALUES (?,?)", (chave, valor))
            print(f"  Criado - {chave}: {valor}")
        cur.execute("SELECT valor FROM configuracoes_site WHERE chave=?", (chave,))
        print(f"  Depois - {chave}: {cur.fetchone()[0]}")

    conn.commit()
    conn.close()
    print("  Salvo!")

