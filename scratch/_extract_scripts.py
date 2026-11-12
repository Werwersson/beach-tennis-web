"""Extrai os <script> inline das telas renderizadas para validar a sintaxe com Node."""
import os
import re
import sys
import tempfile
import shutil

BASE = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, BASE)

TEMP_DB = os.path.join(tempfile.gettempdir(), 'bt_scripts.db')
shutil.copyfile(os.path.join(BASE, 'beach_tennis.db'), TEMP_DB)
os.environ['DATABASE_URL'] = 'sqlite:///' + TEMP_DB.replace('\\', '/')

from app import create_app

SAIDA = os.path.join(tempfile.gettempdir(), 'bt_js_check')
os.makedirs(SAIDA, exist_ok=True)

app = create_app('development')
app.config['TESTING'] = True
app.config['WTF_CSRF_ENABLED'] = False

admin = app.test_client()
admin.post('/auth/login', data={'email': 'professor@beachtennis.com', 'senha': 'admin123'})
aluno = app.test_client()
aluno.post('/auth/login', data={'email': 'aluno@beachtennis.com', 'senha': 'aluno123'})

paginas = {
    'aluno_evolucao': (aluno, '/aluno/evolucao'),
    'aluno_painel': (aluno, '/aluno/painel'),
    'admin_perfil': (admin, '/admin/alunos/3'),
    'admin_avaliacao_detalhe': (admin, '/admin/avaliacoes/4'),
    'admin_avaliacao_form': (admin, '/admin/avaliacoes/nova?aluno_id=3'),
    'admin_dashboard': (admin, '/admin/dashboard'),
}

for nome, (client, url) in paginas.items():
    resp = client.get(url)
    if resp.status_code != 200:
        print(f'[ERRO] {url} -> {resp.status_code}')
        continue
    html = resp.get_data(as_text=True)
    blocos = re.findall(r'<script(?![^>]*\bsrc=)[^>]*>(.*?)</script>', html, re.S | re.I)
    for i, bloco in enumerate(blocos):
        if not bloco.strip():
            continue
        caminho = os.path.join(SAIDA, f'{nome}_{i}.js')
        with open(caminho, 'w', encoding='utf-8') as f:
            f.write(bloco)
        print(f'{nome}_{i}.js ({len(bloco)} chars)')

try:
    from app.extensions import db
    with app.app_context():
        db.engine.dispose()
    os.remove(TEMP_DB)
except OSError:
    pass
