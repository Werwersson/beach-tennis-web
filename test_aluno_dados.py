import os
from datetime import date
from app import create_app
from app.extensions import db
from app.models import Usuario, Aluno

app = create_app('development')
app.testing = True
app.config['WTF_CSRF_ENABLED'] = False

def test_aluno_dados_opcionais():
    with app.app_context():
        client = app.test_client()

        # Garante usuário aluno de teste
        user = Usuario.query.filter_by(email='aluno@test.com').first()
        if not user:
            user = Usuario(nome='Aluno Teste', email='aluno@test.com', perfil='aluno', ativo=True)
            user.set_senha('aluno123')
            db.session.add(user)
            db.session.flush()
        else:
            user.set_senha('aluno123')

        aluno = Aluno.query.filter_by(usuario_id=user.id).first()
        if not aluno:
            aluno = Aluno(usuario_id=user.id, nome='Aluno Teste', ativo=True)
            db.session.add(aluno)
        db.session.commit()

        # 1. Login
        login_resp = client.post('/auth/login', data={'email': 'aluno@test.com', 'senha': 'aluno123'}, follow_redirects=True)
        assert login_resp.status_code == 200, "Falha no login do aluno"

        # 2. GET /aluno/perfil
        perfil_resp = client.get('/aluno/perfil')
        assert perfil_resp.status_code == 200, "Falha no GET /aluno/perfil"
        html = perfil_resp.get_data(as_text=True)
        assert "Telefone / WhatsApp" in html
        assert "Data de Nascimento" in html
        assert "Campos Opcionais" in html
        assert "Salvar Dados" in html
        print("✓ GET /aluno/perfil exibindo campos opcionais corretamente.")

        # 3. Aluno insere telefone e data de nascimento
        post_dados_resp = client.post('/aluno/perfil', data={
            'acao': 'dados',
            'telefone': '(73) 98877-6655',
            'data_nascimento': '2001-05-15'
        }, follow_redirects=True)
        assert post_dados_resp.status_code == 200, "Falha no POST com dados"

        aluno_db = Aluno.query.filter_by(usuario_id=user.id).first()
        assert aluno_db.telefone == '(73) 98877-6655', f"Esperava telefone salvo, obteve {aluno_db.telefone}"
        assert aluno_db.data_nascimento == date(2001, 5, 15), f"Esperava data salva, obteve {aluno_db.data_nascimento}"
        print("✓ Aluno inseriu número e data de nascimento com sucesso!")

        # 4. Aluno opta por não inserir (deixa em branco / limpa os campos)
        post_limpar_resp = client.post('/aluno/perfil', data={
            'acao': 'dados',
            'telefone': '',
            'data_nascimento': ''
        }, follow_redirects=True)
        assert post_limpar_resp.status_code == 200, "Falha no POST com campos vazios"

        db.session.refresh(aluno_db)
        assert aluno_db.telefone is None, f"Esperava telefone None, obteve {aluno_db.telefone}"
        assert aluno_db.data_nascimento is None, f"Esperava data_nascimento None, obteve {aluno_db.data_nascimento}"
        print("✓ Opção de não inserir validada com sucesso (salvo como None)!")

        # 5. Alteração de senha continua funcionando
        post_senha_resp = client.post('/aluno/alterar-senha', data={
            'acao': 'senha',
            'senha_atual': 'aluno123',
            'nova_senha': 'novasenha123',
            'confirmar_senha': 'novasenha123'
        }, follow_redirects=True)
        assert post_senha_resp.status_code == 200, "Falha na alteração de senha"
        db.session.refresh(user)
        assert user.check_senha('novasenha123'), "Nova senha não foi aplicada"
        print("✓ Alteração de senha permanece funcionando perfeitamente!")

if __name__ == '__main__':
    test_aluno_dados_opcionais()
    print("\nTODOS OS TESTES DE DADOS OPCIONAIS DO ALUNO PASSARAM COM SUCESSO!")
