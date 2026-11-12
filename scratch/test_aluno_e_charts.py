import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from datetime import datetime, date, timedelta
from app import create_app
from app.extensions import db
from app.models import Usuario, Aluno, Turma, Aula, Presenca, Avaliacao

def test_aluno_view(app):
    print("\n--- 1. TESTE DA ÁREA DO ALUNO E SEGURANÇA ---")
    aluno_client = app.test_client()
    
    # Login como Aluno
    r_login = aluno_client.post('/auth/login', data={'email': 'aluno@beachtennis.com', 'senha': 'aluno123'}, follow_redirects=False)
    assert r_login.status_code == 302 and '/aluno/painel' in r_login.headers['Location'], "Aluno deve redirecionar para /aluno/painel"
    print("[OK] Login do aluno autenticado -> /aluno/painel")

    # Aluno tenta acessar telas administrativas -> DEVE SER BLOQUEADO (403)
    r_adm1 = aluno_client.get('/admin/dashboard')
    assert r_adm1.status_code == 403, f"Aluno deveria receber 403 no admin dashboard, recebeu {r_adm1.status_code}"
    r_adm2 = aluno_client.get('/admin/alunos')
    assert r_adm2.status_code == 403, f"Aluno deveria receber 403 no CRUD de alunos, recebeu {r_adm2.status_code}"
    print("[OK] Aluno bloqueado com 403 em rotas administrativas (/admin/dashboard e /admin/alunos)")

    # Painel do Aluno (/aluno/painel)
    r_painel = aluno_client.get('/aluno/painel')
    assert r_painel.status_code == 200
    html_painel = r_painel.get_data(as_text=True)
    assert 'Lucas' in html_painel
    assert 'alunoRadarChart' in html_painel
    assert '/admin/' not in html_painel, "Aluno não deve ver links de administração"
    print("[OK] Painel do aluno carregado com radar e sem links de admin")

    # Ações do Aluno: Confirmar Presença e Avisar Ausência
    with app.app_context():
        aula = Aula.query.filter(Aula.data_hora >= datetime.now()).first()
        aluno = Usuario.query.filter_by(email='aluno@beachtennis.com').first().aluno

    r_conf = aluno_client.post(f'/aluno/aulas/{aula.id}/confirmar', data={'origem': 'painel'}, follow_redirects=True)
    assert r_conf.status_code == 200
    with app.app_context():
        p = Presenca.query.filter_by(aula_id=aula.id, aluno_id=aluno.id).first()
        assert p is not None and p.status == 'confirmado'
    print("[OK] Aluno confirmou presença com sucesso -> status: 'confirmado'")

    r_aus = aluno_client.post(f'/aluno/aulas/{aula.id}/avisar-ausencia', data={'motivo': 'Consulta médica', 'origem': 'painel'}, follow_redirects=True)
    assert r_aus.status_code == 200
    with app.app_context():
        p = Presenca.query.filter_by(aula_id=aula.id, aluno_id=aluno.id).first()
        assert p is not None and p.status == 'ausencia_avisada'
        assert 'médica' in p.justificativa.lower()
    print("[OK] Aluno avisou ausência com sucesso -> status: 'ausencia_avisada'")

    # Evolução do Aluno (/aluno/evolucao)
    r_evo = aluno_client.get('/aluno/evolucao')
    assert r_evo.status_code == 200
    html_evo = r_evo.get_data(as_text=True)
    assert 'radarEvolucaoChart' in html_evo
    assert 'alunoLinhaChart' in html_evo
    assert 'Curva de Aprendizado' in html_evo
    assert 'Nota na Categoria' in html_evo
    assert 'Comparativo por Critério' in html_evo
    assert '↑' in html_evo
    print("[OK] Tela de evolução do aluno carregou radar, linha temporal e tabela com deltas (↑)")

    # Exercícios do Aluno (/aluno/exercicios)
    r_ex = aluno_client.get('/aluno/exercicios')
    assert r_ex.status_code == 200
    print("[OK] Tela de treinos complementares do aluno carregada com sucesso")


def test_admin_view(app):
    print("\n--- 2. TESTE DA VISÃO DO PROFESSOR (ADMIN) E CHART.JS ---")
    admin_client = app.test_client()

    # Login como Admin
    r_login = admin_client.post('/auth/login', data={'email': 'professor@beachtennis.com', 'senha': 'admin123'}, follow_redirects=False)
    assert r_login.status_code == 302 and '/admin/dashboard' in r_login.headers['Location']
    print("[OK] Login do professor autenticado -> /admin/dashboard")

    # Admin tenta acessar painel exclusivo do aluno -> DEVE RECEBER 403
    r_aluno_tentativa = admin_client.get('/aluno/painel')
    assert r_aluno_tentativa.status_code == 403, f"Admin deve receber 403 no painel do aluno, recebeu {r_aluno_tentativa.status_code}"
    print("[OK] Admin bloqueado com 403 ao tentar acessar rota exclusiva de aluno")

    # Dashboard do Admin Completo
    r_dash = admin_client.get('/admin/dashboard')
    assert r_dash.status_code == 200
    html_dash = r_dash.get_data(as_text=True)
    assert 'Programação das Aulas da Semana' in html_dash
    assert 'Sem Avaliação há +30 dias' in html_dash
    assert 'Frequência do Mês Atual' in html_dash
    assert 'Maior Evolução Técnica' in html_dash
    print("[OK] Dashboard do admin renderiza aulas da semana, presença do mês, pendências >30d e ranking de evolução")

    # Perfil do Aluno com Chart.js (/admin/alunos/<id>)
    with app.app_context():
        aluno = Usuario.query.filter_by(email='aluno@beachtennis.com').first().aluno

    r_perfil = admin_client.get(f'/admin/alunos/{aluno.id}')
    assert r_perfil.status_code == 200
    html_perfil = r_perfil.get_data(as_text=True)
    assert 'radarChart' in html_perfil
    assert 'linhaEvolucaoChart' in html_perfil
    assert 'Curva de Aprendizado' in html_perfil
    assert 'frequenciaMensalChart' in html_perfil
    assert 'Comparativo por Critério' in html_perfil
    assert '↑' in html_perfil
    print("[OK] Perfil do aluno no admin exibindo Radar (inicial vs atual), Linha de evolução, Frequência mensal em barras e setas de evolução (↑)")


if __name__ == '__main__':
    app = create_app('development')
    app.config['TESTING'] = True
    app.config['WTF_CSRF_ENABLED'] = False
    
    test_aluno_view(app)
    test_admin_view(app)
    print("\n=== TODOS OS TESTES PASSARAM COM 100% DE SUCESSO! ===")
