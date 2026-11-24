from app import create_app
from app.extensions import db
from app.models import Usuario, Aluno
from app.utils.schema_migration import garantir_esquema_banco

app = create_app('development')
app.testing = True
app.config['WTF_CSRF_ENABLED'] = False


def test_cor_fundo_aluno():
    with app.app_context():
        garantir_esquema_banco()
        client = app.test_client()

        # Garante usuário aluno
        user = Usuario.query.filter_by(email='aluno@test.com').first()
        if not user:
            user = Usuario(nome='Aluno Teste', email='aluno@test.com', perfil='aluno', ativo=True)
            user.set_senha('aluno123')
            db.session.add(user)
            db.session.commit()
            aluno = Aluno(usuario_id=user.id, nome='Aluno Teste', ativo=True, cor_fundo='#F8F6F2')
            db.session.add(aluno)
            db.session.commit()
        else:
            user.set_senha('aluno123')
            user.ativo = True
            aluno = Aluno.query.filter_by(usuario_id=user.id).first()
            aluno.cor_fundo = '#F8F6F2'
            db.session.commit()

        # 1. Login aluno
        client.post('/auth/login', data={'email': 'aluno@test.com', 'senha': 'aluno123'}, follow_redirects=True)

        # 2. GET /aluno/perfil
        resp = client.get('/aluno/perfil')
        assert resp.status_code == 200
        html = resp.get_data(as_text=True)
        assert "Cor de Fundo da Tela" in html
        assert "btn-theme-swatch" in html
        assert "pickerCorFundo" in html
        print("✓ Interface de seleção de cor de fundo renderizada com sucesso!")

        # 3. Aluno atualiza cor de fundo via formulário do perfil
        resp_post = client.post('/aluno/perfil', data={
            'acao': 'dados',
            'email': 'aluno@test.com',
            'lado_dominante': 'destro',
            'cor_fundo': '#EAF2F8'
        }, follow_redirects=True)
        assert resp_post.status_code == 200

        db.session.refresh(aluno)
        assert aluno.cor_fundo == '#EAF2F8', f"Esperava '#EAF2F8', obteve {aluno.cor_fundo}"
        print("✓ Cor de fundo salva com sucesso pelo formulário do perfil!")

        # 4. Verifica se base_aluno.html reflete a cor personalizada no CSS
        resp_painel = client.get('/aluno/painel')
        assert resp_painel.status_code == 200
        html_painel = resp_painel.get_data(as_text=True)
        assert '#EAF2F8' in html_painel, "A cor personalizada deve estar no CSS da base"
        print("✓ base_aluno.html refletindo a cor personalizada no CSS!")

        # 5. Teste da rota instantânea /aluno/definir-cor-fundo via JSON
        resp_api = client.post('/aluno/definir-cor-fundo', json={'cor_fundo': '#1E2227'})
        assert resp_api.status_code == 200
        assert resp_api.get_json()['status'] == 'ok'
        db.session.refresh(aluno)
        assert aluno.cor_fundo == '#1E2227'
        print("✓ Endpoint instantâneo /aluno/definir-cor-fundo funcionou com sucesso!")

        # 6. Teste de rejeição de cor inválida / perigosa
        resp_inv = client.post('/aluno/definir-cor-fundo', json={'cor_fundo': '<script>alert(1)</script>'})
        assert resp_inv.status_code == 400
        print("✓ Validação contra injeção de valores inválidos funcionando corretamente!")

        # Restaura para cor padrão
        aluno.cor_fundo = '#F8F6F2'
        db.session.commit()


if __name__ == '__main__':
    test_cor_fundo_aluno()
    print("\nTODOS OS TESTES DE COR DE FUNDO PASSARAM COM SUCESSO!")
