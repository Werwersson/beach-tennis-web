import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from datetime import datetime, date
from app import create_app
from app.extensions import db
from app.models import Usuario, Aluno, Conquista, Modalidade, Plano, Depoimento, MensagemContato

def test_etapa7():
    app = create_app('development')
    app.config['WTF_CSRF_ENABLED'] = False  # Facilita testes programáticos
    client = app.test_client()

    with app.app_context():
        print("--- 1. TESTE DA PÁGINA PÚBLICA (ROTA '/') ---")
        res = client.get('/')
        assert res.status_code == 200, f"Erro status {res.status_code}"
        html = res.data.decode('utf-8')
        assert "Aulas de Beach Tennis em Itabuna" in html, "Título do hero não encontrado!"
        assert "Everson Vicktor Silva Silveira" in html, "Nome do professor não encontrado!"
        assert "Líder do ranking AIBT 2026 em 3 categorias" in html, "Frase de destaque não encontrada!"
        assert "SportsActivityLocation" in html, "Schema.org structured data não encontrado!"
        assert "Itabuna" in html, "Cidade Itabuna não encontrada no SEO!"
        print("✓ Página pública renderizada com sucesso com dados do professor, hero e SEO!")

        print("\n--- 2. TESTE DE ROBOTS.TXT E SITEMAP.XML ---")
        res_robots = client.get('/robots.txt')
        assert res_robots.status_code == 200
        assert "User-agent: *" in res_robots.data.decode('utf-8')

        res_sitemap = client.get('/sitemap.xml')
        assert res_sitemap.status_code == 200
        assert "<loc>" in res_sitemap.data.decode('utf-8')
        print("✓ robots.txt e sitemap.xml operacionais!")

        print("\n--- 3. TESTE DO FORMULÁRIO DE CONTATO (COM HONEYPOT E RATE LIMIT) ---")
        # Envio legítimo
        res_contato = client.post('/contato', data={
            'nome': 'Interessado Teste',
            'telefone': '73988776655',
            'mensagem': 'Gostaria de agendar aula experimental na terça-feira.',
            'website_url': ''  # honeypot vazio
        }, follow_redirects=True)
        assert res_contato.status_code == 200
        msg_salva = MensagemContato.query.filter_by(nome='Interessado Teste').first()
        assert msg_salva is not None, "Mensagem não foi salva no banco de dados!"
        print("✓ Envio legítimo de mensagem de contato salvo no banco!")

        # Envio com honeypot preenchido (bot/spam)
        res_spam = client.post('/contato', data={
            'nome': 'Spam Bot Teste 2',
            'telefone': '00000000',
            'mensagem': 'Compre produtos promocionais',
            'website_url': 'http://spam-link.com'
        }, follow_redirects=True)
        spam_msg = MensagemContato.query.filter_by(nome='Spam Bot Teste 2').first()
        assert spam_msg is None, "Honeypot falhou! Mensagem de spam foi salva!"
        print("✓ Honeypot anti-spam bloqueou com sucesso envio malicioso!")

        print("\n--- 4. TESTE DE LOGIN E ROTAS ADMIN DO SITE ---")
        client_admin = app.test_client()
        login_res = client_admin.post('/auth/login', data={
            'email': 'professor@beachtennis.com',
            'senha': 'admin123'
        }, follow_redirects=True)
        assert login_res.status_code == 200
        assert b"Painel Administrativo" in login_res.data or b"Dashboard" in login_res.data

        # Configurações
        res_cfg = client_admin.get('/admin/site/configuracoes')
        assert res_cfg.status_code == 200
        assert "Everson Vicktor Silva Silveira" in res_cfg.data.decode('utf-8')

        # Conquistas
        res_conq = client_admin.get('/admin/site/conquistas')
        assert res_conq.status_code == 200
        assert "Campeão Masc B" in res_conq.data.decode('utf-8')

        # Modalidades
        res_mod = client_admin.get('/admin/site/modalidades')
        assert res_mod.status_code == 200
        assert "Individual" in res_mod.data.decode('utf-8')

        # Planos
        res_plan = client_admin.get('/admin/site/planos')
        assert res_plan.status_code == 200

        # Depoimentos
        res_dep = client_admin.get('/admin/site/depoimentos')
        assert res_dep.status_code == 200

        # Galeria
        res_gal = client_admin.get('/admin/site/galeria')
        assert res_gal.status_code == 200

        # Mensagens
        res_msg = client_admin.get('/admin/site/mensagens')
        assert res_msg.status_code == 200
        assert "Interessado Teste" in res_msg.data.decode('utf-8')
        print("✓ Todas as rotas administrativas do site público responderam 200 OK!")

        print("\n--- 5. TESTE DE EXPORTAÇÃO EM PDF ---")
        # Exportação pelo Admin
        aluno = Aluno.query.first()
        res_pdf_admin = client_admin.get(f'/admin/alunos/{aluno.id}/pdf')
        assert res_pdf_admin.status_code == 200
        assert res_pdf_admin.headers['Content-Type'] == 'application/pdf'
        assert len(res_pdf_admin.data) > 1000
        print(f"✓ PDF exportado pelo Admin com sucesso ({len(res_pdf_admin.data)} bytes, vetor ReportLab puro)!")

        # Exportação pelo Aluno
        client_admin.get('/auth/logout') # Desloga o admin
        client_aluno = app.test_client()
        login_aluno = client_aluno.post('/auth/login', data={
            'email': 'aluno@beachtennis.com',
            'senha': 'aluno123'
        }, follow_redirects=True)
        print("Login aluno:", login_aluno.status_code, "URL final:", login_aluno.request.path if hasattr(login_aluno, 'request') else '')
        res_pdf_aluno = client_aluno.get('/aluno/relatorio-pdf')
        print("PDF Aluno status:", res_pdf_aluno.status_code, "Headers:", dict(res_pdf_aluno.headers))
        assert res_pdf_aluno.status_code == 200
        assert res_pdf_aluno.headers['Content-Type'] == 'application/pdf'
        assert len(res_pdf_aluno.data) > 1000
        print(f"✓ PDF exportado pelo Aluno com sucesso ({len(res_pdf_aluno.data)} bytes)!")

        print("\n==============================================")
        print("🎉 TODOS OS TESTES DA ETAPA 7 PASSARAM COM SUCESSO!")
        print("==============================================")

if __name__ == '__main__':
    test_etapa7()
