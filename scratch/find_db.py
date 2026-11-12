import sqlite3, os

# Verificar todos os arquivos .db do projeto
for root, dirs, files in os.walk('d:\\Projetos\\Beach_Tennis_Web'):
    # Pular venv
    dirs[:] = [d for d in dirs if d not in ['venv', '__pycache__', '.git', 'migrations']]
    for f in files:
        if f.endswith('.db'):
            path = os.path.join(root, f)
            size = os.path.getsize(path)
            try:
                conn = sqlite3.connect(path)
                cur = conn.cursor()
                cur.execute("SELECT name FROM sqlite_master WHERE type='table'")
                tables = [r[0] for r in cur.fetchall()]
                # Checar se tem configuracao_site
                if 'configuracao_site' in tables:
                    cur.execute("SELECT chave, valor FROM configuracao_site WHERE chave IN ('whatsapp','instagram')")
                    rows = cur.fetchall()
                    print(f"\n[BANCO COM CONFIG] {path} ({size} bytes)")
                    for row in rows:
                        print(f"  {row[0]}: {row[1]}")
                else:
                    print(f"\n[SEM CONFIG] {path} ({size} bytes) - tabelas: {tables[:5]}")
                conn.close()
            except Exception as e:
                print(f"\n[ERRO] {path}: {e}")

