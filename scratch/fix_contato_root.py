import sys, sqlite3, os
sys.path.insert(0, '.')

# Banco que o servidor realmente usa (raiz do projeto)
db_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'beach_tennis.db')
db_path = os.path.normpath(db_path)
print(f"Banco: {db_path}")
print(f"Existe: {os.path.exists(db_path)}")

conn = sqlite3.connect(db_path)
cur = conn.cursor()

updates = {
    'whatsapp': '5573999969999',
    'instagram': 'eversonvicktor',
}

for chave, valor in updates.items():
    cur.execute("SELECT valor FROM configuracao_site WHERE chave=?", (chave,))
    row = cur.fetchone()
    if row:
        print(f"Antes - {chave}: {row[0]}")
        cur.execute("UPDATE configuracao_site SET valor=? WHERE chave=?", (valor, chave))
    else:
        cur.execute("INSERT INTO configuracao_site (chave, valor) VALUES (?,?)", (chave, valor))
    cur.execute("SELECT valor FROM configuracao_site WHERE chave=?", (chave,))
    print(f"Depois - {chave}: {cur.fetchone()[0]}")

conn.commit()
conn.close()
print("\nSalvo com sucesso!")

