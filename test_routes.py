"""
test_routes.py – Testa as novas rotas do BT Tracker (comparação, heatmap, CSV, dashboard).

Uso:  python -u test_routes.py
"""
import re
from app import create_app
from app.models import Partida, Usuario, PontoPartida
from app.extensions import db
from app.utils.schema_migration import garantir_esquema_banco

# ----------------------------------------------------------------------
# Cria a aplicação com CSRF desabilitado para testes
# ----------------------------------------------------------------------
app = create_app('development')
app.testing = True
app.config['WTF_CSRF_ENABLED'] = False        # desabilita CSRF nos forms
app.config['LOGIN_DISABLED'] = False
client = app.test_client()

# ==============================================================
# 1. PREPARAÇÃO DO BANCO  (antes de qualquer query ORM)
# ==============================================================
with app.app_context():
    db.create_all()
    garantir_esquema_banco()
    print('[OK] Banco criado e migração executada.')

# ==============================================================
# 2. CRIAR ADMIN + PARTIDAS DE TESTE
# ==============================================================
with app.app_context():
    # Admin
    admin = Usuario.query.filter_by(email='admin@test.com').first()
    if not admin:
        admin = Usuario(
            nome='Admin Teste',
            email='admin@test.com',
            perfil='admin',
            ativo=True,
        )
        admin.set_senha('admin123')
        db.session.add(admin)
        db.session.commit()
        print('[OK] Usuário admin criado: admin@test.com / admin123')
    else:
        print('[OK] Usuário admin já existe.')

    # Partidas
    total = Partida.query.count()
    if total < 2:
        p1 = Partida(
            jogador1_nome='A1', jogador2_nome='A2',
            jogador3_nome='B1', jogador4_nome='B2',
            fase='Final',
        )
        p2 = Partida(
            jogador1_nome='C1', jogador2_nome='C2',
            jogador3_nome='D1', jogador4_nome='D2',
            fase='Grupos',
        )
        db.session.add_all([p1, p2])
        db.session.commit()
        pid1, pid2 = p1.id, p2.id
        print(f'[OK] Duas partidas criadas: ids {pid1}, {pid2}')
    else:
        partidas = Partida.query.order_by(Partida.id).limit(2).all()
        pid1, pid2 = partidas[0].id, partidas[1].id
        print(f'[OK] Usando partidas existentes: ids {pid1}, {pid2}')


# ==============================================================
# 3. LOGIN DO ADMIN
# ==============================================================
resp_login = client.post('/auth/login', data={
    'email': 'admin@test.com',
    'senha': 'admin123',
}, follow_redirects=True)
print(f'[LOGIN] Status: {resp_login.status_code}')
html = resp_login.get_data(as_text=True)
if 'dashboard' in html.lower() or resp_login.status_code == 200:
    print('[OK] Login realizado com sucesso!')
else:
    print('[ERRO] Login falhou. Trecho da resposta:')
    print(html[:300])


# ==============================================================
# 4. TESTAR ROTAS
# ==============================================================
def test_route(path, method='GET', data=None, expect_status=200):
    """Testa uma rota e imprime resultado resumido."""
    if method == 'GET':
        resp = client.get(path)
    else:
        resp = client.post(path, data=data, follow_redirects=True)

    status_ok = resp.status_code == expect_status
    icon = '✓' if status_ok else '✗'

    print(f'  {icon} {method} {path} → {resp.status_code}', end='')
    if not status_ok:
        print(f'  (esperado {expect_status})')
    else:
        print()

    if resp.is_json:
        json_data = resp.get_json()
        print(f'    JSON: {json_data}')
    return resp


if __name__ == '__main__':
    print()
    print('=' * 60)
    print('TESTES DAS ROTAS DO BT TRACKER')
    print('=' * 60)

    # -- Rotas existentes --
    print('\n--- Rotas existentes ---')
    test_route('/admin/dashboard')
    test_route('/admin/partidas')
    test_route('/admin/partidas/carregar-partida-exemplo', expect_status=302)

    # -- Novas rotas GET --
    print('\n--- Novas rotas (GET) ---')
    test_route('/admin/partidas/comparar')
    test_route('/admin/partidas/set_score_summary')

    # -- Comparação POST --
    print('\n--- Comparação de partidas (POST) ---')
    test_route('/admin/partidas/comparar', method='POST',
               data={'partida1': pid1, 'partida2': pid2})

    # -- Heatmap JSON --
    print('\n--- Heatmap JSON ---')
    test_route(f'/admin/partidas/{pid1}/heatmap_json?set=1')

    # -- CSV por set --
    print('\n--- CSV por set ---')
    test_route(f'/admin/partidas/{pid1}/set_1_csv')

    # -- Scout Simplificado: Lançar Ponto com Saque Difícil do Adversário --
    print('\n--- Scout Simplificado: Ponto com Saque Difícil (sem dados do adversário) ---')
    resp_ponto = test_route(f'/admin/partidas/{pid1}/pontos/novo', method='POST', data={
        'sacador': '3',               # Adversário sacando
        'saque_dificil': '1',         # Apenas indica que o saque foi difícil
        'dupla_vencedora': '1',       # Nossa dupla venceu
        'tipo_desfecho': 'winner',    # Winner nosso
        'atleta_finalizador': '1',    # Jogador 1
        'tipo_golpe': 'Smash',
        'set_num': '1',
        'placar_texto': '15x0'
    })

    # -- Editar Ponto pelo Professor --
    print('\n--- Editar Ponto pelo Professor ---')
    with app.app_context():
        ponto_recente = PontoPartida.query.filter_by(partida_id=pid1).order_by(PontoPartida.id.desc()).first()
        ponto_id = ponto_recente.id if ponto_recente else None

    if ponto_id:
        test_route(f'/admin/partidas/pontos/{ponto_id}/editar', method='POST', data={
            'sacador': '3',
            'saque_dificil': '1',
            'dupla_vencedora': '1',
            'tipo_desfecho': 'forcou_erro',
            'atleta_finalizador': '2',
            'tipo_golpe': 'Lob Chutado',
            'set_num': '1',
            'placar_texto': '30x0'
        })

    print()
    print('=' * 60)
    print('TESTES CONCLUÍDOS')
    print('=' * 60)
