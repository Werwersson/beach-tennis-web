"""Smoke test rápido: carrega o app, calcula analytics e renderiza as telas-chave."""
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import create_app
from app.models import Aluno
from app.utils.analytics import get_aluno_analytics

app = create_app('development')
app.config['TESTING'] = True
app.config['WTF_CSRF_ENABLED'] = False

with app.app_context():
    for aluno in Aluno.query.order_by(Aluno.id).all():
        an = get_aluno_analytics(aluno)
        print(
            f'#{aluno.id} {aluno.nome} cat={aluno.categoria} '
            f'avals={an["total_avaliacoes"]} '
            f'nota {an["media_inicial"]}->{an["media_atual"]} '
            f'indice {an["indice_inicial"]}->{an["indice_atual"]} '
            f'promocoes={[(p["de"], p["para"]) for p in an["promocoes"]]}'
        )

admin = app.test_client()
r = admin.post('/auth/login', data={'email': 'professor@beachtennis.com', 'senha': 'admin123'}, follow_redirects=False)
print('login admin:', r.status_code, r.headers.get('Location'))
for url in ['/admin/dashboard', '/admin/alunos', '/admin/avaliacoes', '/admin/alunos/3', '/admin/avaliacoes/4', '/admin/avaliacoes/nova?aluno_id=3']:
    resp = admin.get(url)
    print(url, '->', resp.status_code, len(resp.data))
    if resp.status_code >= 500:
        print(resp.get_data(as_text=True)[:2000])

aluno_client = app.test_client()
r = aluno_client.post('/auth/login', data={'email': 'aluno@beachtennis.com', 'senha': 'aluno123'}, follow_redirects=False)
print('login aluno:', r.status_code, r.headers.get('Location'))
for url in ['/aluno/painel', '/aluno/evolucao']:
    resp = aluno_client.get(url)
    print(url, '->', resp.status_code, len(resp.data))
    if resp.status_code >= 500:
        print(resp.get_data(as_text=True)[:2000])
