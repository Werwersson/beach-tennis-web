import os
import sys

BASE = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, BASE)

from app import create_app
from app.models import Aluno
from app.utils.analytics import get_aluno_analytics

app = create_app('development')
app.config['TESTING'] = True
app.config['WTF_CSRF_ENABLED'] = False

with app.app_context():
    aluno = Aluno.query.order_by(Aluno.id).first()
    an = get_aluno_analytics(aluno)
    print('aluno:', aluno.nome, aluno.categoria_label)
    print('notas:', an['linha_medias'])
    print('indices:', an['linha_indices'])
    print('promocoes:', [(p['de'], p['para'], p['delta_media'], p['delta_indice']) for p in an['promocoes']])

client = app.test_client()
client.post('/auth/login', data={'email': 'aluno@beachtennis.com', 'senha': 'aluno123'})
html = client.get('/aluno/evolucao').get_data(as_text=True)
for chave in ['Sua Trajetória de Categoria', '"de": "D"', '"para": "C"', 'Nota na Categoria x Curva de Aprendizado']:
    print(f'{chave!r}:', chave in html)
for linha in html.splitlines():
    if 'const linhaIndices' in linha or 'const promocoes =' in linha or 'const linhaLabels' in linha:
        print(linha.strip())
