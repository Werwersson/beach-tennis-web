"""
test_routes.py – Testa as novas rotas do BT Insight (comparação, heatmap, CSV, dashboard).

Uso:  python -u test_routes.py
"""
import re
from app import create_app
from app.models import Partida, Usuario, PontoPartida, Aluno
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

    # Aluno
    aluno_user = Usuario.query.filter_by(email='aluno@test.com').first()
    if not aluno_user:
        aluno_user = Usuario(
            nome='Aluno Teste',
            email='aluno@test.com',
            perfil='aluno',
            ativo=True,
        )
        aluno_user.set_senha('aluno123')
        db.session.add(aluno_user)
        db.session.flush()
        aluno_obj = Aluno(
            usuario_id=aluno_user.id,
            nome='Aluno Teste',
            nivel='iniciante',
            categoria='D',
            ativo=True
        )
        db.session.add(aluno_obj)
        db.session.commit()
        print('[OK] Usuário aluno criado: aluno@test.com / aluno123')
    else:
        aluno_user.set_senha('aluno123')
        db.session.commit()
        print('[OK] Usuário aluno já existe (senha resetada para aluno123).')

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
    print('TESTES DAS ROTAS DO BT INSIGHT')
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

    # -- Testes do Aluno: Perfil e Alteração de Senha --
    print('\n--- Aluno: Login, Perfil e Alteração de Senha ---')
    # Logout do admin
    client.get('/auth/logout')
    
    # Login como aluno
    resp_aluno_login = client.post('/auth/login', data={'email': 'aluno@test.com', 'senha': 'aluno123'}, follow_redirects=True)
    assert resp_aluno_login.status_code == 200, f"Erro no login do aluno: {resp_aluno_login.status_code}"
    print('  ✓ Login do Aluno realizado com sucesso (200)')

    # Acessar Perfil e Alterar Senha (GET)
    test_route('/aluno/perfil')
    test_route('/aluno/alterar-senha')

    # Teste de tentativa com senha atual incorreta
    resp_errada = client.post('/aluno/alterar-senha', data={
        'senha_atual': 'senha_errada_xyz',
        'nova_senha': 'novasenha456',
        'confirmar_senha': 'novasenha456'
    }, follow_redirects=True)
    assert 'Senha atual incorreta' in resp_errada.get_data(as_text=True)
    print('  ✓ Validação de senha atual incorreta funcionou')

    # Teste de tentativa com confirmação divergente
    resp_dif = client.post('/aluno/alterar-senha', data={
        'senha_atual': 'aluno123',
        'nova_senha': 'novasenha456',
        'confirmar_senha': 'outrasenha789'
    }, follow_redirects=True)
    assert resp_dif.status_code == 200
    print('  ✓ Validação de confirmação de senha divergente funcionou')

    # Teste de tentativa com nova senha igual à atual
    resp_igual = client.post('/aluno/alterar-senha', data={
        'senha_atual': 'aluno123',
        'nova_senha': 'aluno123',
        'confirmar_senha': 'aluno123'
    }, follow_redirects=True)
    assert 'diferente da senha atual' in resp_igual.get_data(as_text=True)
    print('  ✓ Validação de nova senha igual à atual funcionou')

    # Sucesso na alteração da senha
    resp_ok = client.post('/aluno/alterar-senha', data={
        'senha_atual': 'aluno123',
        'nova_senha': 'novasenha456',
        'confirmar_senha': 'novasenha456'
    }, follow_redirects=True)
    assert 'senha foi alterada com sucesso' in resp_ok.get_data(as_text=True).lower()
    print('  ✓ Alteração de senha realizada com sucesso')

    # Testar login com a NOVA senha
    client.get('/auth/logout')
    resp_novo_login = client.post('/auth/login', data={'email': 'aluno@test.com', 'senha': 'novasenha456'}, follow_redirects=True)
    assert resp_novo_login.status_code == 200 and 'Olá, Aluno' in resp_novo_login.get_data(as_text=True)
    print('  ✓ Novo login com a nova senha validado com sucesso (200)')

    # Teste de Segurança: Prevenção contra Open Redirect
    client.get('/auth/logout')
    resp_open_redirect = client.post('/auth/login?next=//malicious-site.com', data={'email': 'aluno@test.com', 'senha': 'novasenha456'}, follow_redirects=False)
    # Deve redirecionar internamente para o painel do aluno e NÃO para //malicious-site.com
    assert resp_open_redirect.headers.get('Location') != '//malicious-site.com'
    assert not resp_open_redirect.headers.get('Location', '').startswith('//')
    print('  ✓ Prevenção contra Open Redirect validada com sucesso')

    print()
    print('=' * 60)
    print('TESTES CONCLUÍDOS')
    print('=' * 60)
