from app import create_app
from app.extensions import db
from app.models import Usuario, Aluno
from app.utils.tema import is_cor_escura

app = create_app('development')
app.testing = True
app.config['WTF_CSRF_ENABLED'] = False


def test_is_cor_escura_calculo():
    # Cores claras
    assert not is_cor_escura('#F8F6F2')
    assert not is_cor_escura('#FFFFFF')
    assert not is_cor_escura('#FFFDF7')
    assert not is_cor_escura('#EAF2F8')
    assert not is_cor_escura('#EAF5EE')
    assert not is_cor_escura('#F4EFF9')
    assert not is_cor_escura('#EFEFEF')
    assert not is_cor_escura('#FFF')

    # Cores escuras
    assert is_cor_escura('#1E2227')
    assert is_cor_escura('#000000')
    assert is_cor_escura('#000')
    assert is_cor_escura('#0A2540')
    assert is_cor_escura('#333333')
    assert is_cor_escura('#111827')
    assert is_cor_escura('#0F172A')

    print("✓ Função is_cor_escura calculou luminosidade com 100% de precisão!")


def test_contraste_renderizacao():
    with app.app_context():
        client = app.test_client()

        user = Usuario.query.filter_by(email='aluno@test.com').first()
        if not user:
            user = Usuario(nome='Aluno Teste', email='aluno@test.com', perfil='aluno', ativo=True)
            user.set_senha('aluno123')
            db.session.add(user)
            db.session.commit()
            aluno = Aluno(usuario_id=user.id, nome='Aluno Teste', ativo=True)
            db.session.add(aluno)
            db.session.commit()
        else:
            user.set_senha('aluno123')
            user.ativo = True
            aluno = Aluno.query.filter_by(usuario_id=user.id).first()

        # Login
        client.post('/auth/login', data={'email': 'aluno@test.com', 'senha': 'aluno123'}, follow_redirects=True)

        # 1. Com cor clara (#F8F6F2)
        aluno.cor_fundo = '#F8F6F2'
        db.session.commit()

        resp_claro = client.get('/aluno/painel')
        assert resp_claro.status_code == 200
        html_claro = resp_claro.get_data(as_text=True)
        assert 'aluno-contrast-light' in html_claro
        assert 'body.aluno-contrast-light' in html_claro
        print("✓ Renderização com tema claro aplica aluno-contrast-light e estilos nítidos!")

        # 2. Com cor escura (#1E2227)
        aluno.cor_fundo = '#1E2227'
        db.session.commit()

        resp_escuro = client.get('/aluno/painel')
        assert resp_escuro.status_code == 200
        html_escuro = resp_escuro.get_data(as_text=True)
        assert 'aluno-contrast-dark' in html_escuro
        assert 'body.aluno-contrast-dark' in html_escuro
        assert 'text-shadow' in html_escuro
        print("✓ Renderização com tema escuro aplica aluno-contrast-dark com text-shadow e alto contraste!")

        # Restaura cor padrão
        aluno.cor_fundo = '#F8F6F2'
        db.session.commit()


if __name__ == '__main__':
    test_is_cor_escura_calculo()
    test_contraste_renderizacao()
    print("\nTODOS OS TESTES DE CONTRASTE DINÂMICO PASSARAM COM SUCESSO!")
