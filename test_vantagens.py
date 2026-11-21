"""Quick test for the vantagens section on the homepage."""
from app import create_app

app = create_app('development')
c = app.test_client()

r = c.get('/')
print('Status:', r.status_code)

html = r.get_data(as_text=True)
print('Vantagens section present:', 'id="vantagens"' in html)
print('Vantagens nav link present:', '#vantagens' in html)
print('Vantagem cards count:', html.count('vantagem-card'))
print('CTA plataforma present:', 'cta-plataforma' in html)
print('Quero Ser Aluno button:', 'Quero Ser Aluno' in html)

keywords = [
    'Painel Digital Exclusivo',
    'Gráficos Radar',
    'BT Insight',
    'Relatórios Automáticos em PDF',
    'Controle de Presença',
    'Biblioteca de Exercícios',
    'Avaliações Periódicas',
    'Metas',
    'Acesso pelo Celular',
]
for kw in keywords:
    found = kw in html
    icon = '✓' if found else '✗'
    print(f'  {icon} {kw}')

assert r.status_code == 200
assert 'id="vantagens"' in html
print('\n[OK] Seção de Vantagens renderizada com sucesso na homepage!')
