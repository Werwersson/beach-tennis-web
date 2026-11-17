import sys
sys.path.insert(0, '.')
from app import create_app
from app.extensions import db
from app.models import Usuario, Aluno, Partida, PontoPartida
from app.utils.bt_tracker import calcular_estatisticas_partida
from app.utils.bt_tracker_pdf import gerar_pdf_bt_tracker

app = create_app('development')
app.config['WTF_CSRF_ENABLED'] = False

with app.app_context():
    partidas = Partida.query.all()
    print(f"Total de Partidas no banco: {len(partidas)}")
    if partidas:
        p = partidas[0]
        print(f"Partida #1: {p.titulo} | {p.dupla1_label} vs {p.dupla2_label}")
        print(f"Total de Pontos da partida: {len(p.pontos)}")
        
        # Testar estatísticas
        stats = calcular_estatisticas_partida(p)
        print(f"Stats calculadas com sucesso! Pontos D1={stats['pontos_dupla1']} D2={stats['pontos_dupla2']}")
        print(f"Total métricas gerais: {len(stats['estatisticas_gerais'])}")
        
        # Testar PDF
        pdf_bytes = gerar_pdf_bt_tracker(p)
        print(f"PDF gerado com sucesso! Tamanho: {len(pdf_bytes)} bytes")
        assert len(pdf_bytes) > 1000, "PDF muito pequeno"

client = app.test_client()

with app.app_context():
    # 1. Login Admin
    r_login = client.post('/auth/login', data={'email': 'professor@beachtennis.com', 'senha': 'admin123'}, follow_redirects=True)
    print("Login Admin status:", r_login.status_code)
    
    # 2. Rota Lista de Partidas Admin
    r_lista = client.get('/admin/partidas')
    print("Admin Lista Partidas status:", r_lista.status_code)
    assert r_lista.status_code == 200
    assert 'BT TRACKER' in r_lista.data.decode('utf-8')
    
    # 3. Rota Detalhes da Partida Admin
    r_det = client.get('/admin/partidas/1')
    print("Admin Detalhes Partida status:", r_det.status_code)
    assert r_det.status_code == 200
    html_det = r_det.data.decode('utf-8')
    assert 'BT TRACKER' in html_det
    assert 'Mapa de Calor' in html_det
    assert 'Dinâmica do Jogo' in html_det
    
    # 4. Rota PDF Admin
    r_pdf = client.get('/admin/partidas/1/pdf')
    print("Admin Download PDF status:", r_pdf.status_code, "Bytes:", len(r_pdf.data))
    assert r_pdf.status_code == 200
    assert r_pdf.mimetype == 'application/pdf'
    
    # 5. Adicionar Ponto via POST
    r_ponto = client.post('/admin/partidas/1/pontos/novo', data={
        'sacador': '1',
        'dupla_vencedora': '1',
        'atleta_finalizador': '1',
        'tipo_desfecho': 'winner',
        'tipo_golpe': 'Smash',
        'posicao_sacador': 'Direita',
        'direcao_saque': '3',
        'qualidade_saque': 'Bom',
        'placar_texto': '4x6 3x6 15x0',
        'situacao_adicional': 'Bola na Linha'
    }, follow_redirects=True)
    print("Adicionar Ponto status:", r_ponto.status_code)
    assert r_ponto.status_code == 200

    # 6. Logout Admin e Login Aluno
    client.get('/auth/logout')
    r_login_aluno = client.post('/auth/login', data={'email': 'aluno@beachtennis.com', 'senha': 'aluno123'}, follow_redirects=True)
    print("Login Aluno status:", r_login_aluno.status_code)
    
    # 7. Rota Partidas Aluno
    r_aluno_partidas = client.get('/aluno/partidas')
    print("Aluno Partidas status:", r_aluno_partidas.status_code)
    assert r_aluno_partidas.status_code == 200
    
    # 8. Rota Detalhes Aluno
    r_aluno_det = client.get('/aluno/partidas/1')
    print("Aluno Detalhes status:", r_aluno_det.status_code)
    assert r_aluno_det.status_code == 200

    # 9. Rota PDF Aluno
    r_aluno_pdf = client.get('/aluno/partidas/1/pdf')
    print("Aluno PDF status:", r_aluno_pdf.status_code, "Bytes:", len(r_aluno_pdf.data))
    assert r_aluno_pdf.status_code == 200

print("\nTODOS OS TESTES DO MÓDULO BT TRACKER PASSARAM COM 100% DE SUCESSO!")
