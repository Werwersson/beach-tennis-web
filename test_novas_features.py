from app import create_app
from app.extensions import db
from app.models import Usuario, Aluno, GaleriaItem
from app.utils.video import converter_para_embed, extrair_youtube_id
from app.utils.schema_migration import garantir_esquema_banco

app = create_app('development')
app.testing = True
app.config['WTF_CSRF_ENABLED'] = False


def test_converter_para_embed():
    assert extrair_youtube_id('https://www.youtube.com/watch?v=dQw4w9WgXcQ') == 'dQw4w9WgXcQ'
    assert extrair_youtube_id('https://youtu.be/dQw4w9WgXcQ?si=123') == 'dQw4w9WgXcQ'
    assert extrair_youtube_id('https://www.youtube.com/shorts/dQw4w9WgXcQ') == 'dQw4w9WgXcQ'
    assert extrair_youtube_id('https://www.youtube.com/embed/dQw4w9WgXcQ') == 'dQw4w9WgXcQ'

    assert converter_para_embed('https://www.youtube.com/watch?v=dQw4w9WgXcQ') == 'https://www.youtube.com/embed/dQw4w9WgXcQ'
    assert converter_para_embed('https://youtu.be/dQw4w9WgXcQ') == 'https://www.youtube.com/embed/dQw4w9WgXcQ'
    assert converter_para_embed('https://www.youtube.com/shorts/dQw4w9WgXcQ') == 'https://www.youtube.com/embed/dQw4w9WgXcQ'
    print("✓ Testes de conversão de URL de vídeo passaram com sucesso!")


def test_usuario_criado_sempre_ativo():
    with app.app_context():
        client = app.test_client()

        # Login admin
        admin = Usuario.query.filter_by(email='admin@test.com').first()
        if not admin:
            admin = Usuario(nome='Admin', email='admin@test.com', perfil='admin', ativo=True)
            admin.set_senha('admin123')
            db.session.add(admin)
            db.session.commit()
        else:
            admin.set_senha('admin123')
            admin.ativo = True
            db.session.commit()

        client.post('/auth/login', data={'email': 'admin@test.com', 'senha': 'admin123'}, follow_redirects=True)

        # Remove aluno de teste anterior se existir
        email_novo_aluno = 'aluno_ativo_teste@beachtennis.com'
        u_old = Usuario.query.filter_by(email=email_novo_aluno).first()
        if u_old:
            al_old = Aluno.query.filter_by(usuario_id=u_old.id).first()
            if al_old:
                db.session.delete(al_old)
            db.session.delete(u_old)
            db.session.commit()

        # Criar novo aluno
        resp = client.post('/admin/alunos/novo', data={
            'nome': 'Aluno Teste Ativo',
            'email': email_novo_aluno,
            'nivel': 'iniciante',
            'categoria': 'D',
            'lado_dominante': 'destro',
            'objetivo': 'lazer'
        }, follow_redirects=True)
        assert resp.status_code == 200

        u_criado = Usuario.query.filter_by(email=email_novo_aluno).first()
        assert u_criado is not None, "Usuário deveria ter sido criado"
        assert u_criado.ativo is True, "Usuário criado pelo professor DEVE ser ativo!"

        al_criado = Aluno.query.filter_by(usuario_id=u_criado.id).first()
        assert al_criado is not None, "Aluno deveria ter sido criado"
        assert al_criado.ativo is True, "Aluno criado pelo professor DEVE ser ativo!"
        print("✓ Novo aluno e usuário criados pelo professor são 100% ativos por padrão!")


def test_aluno_muda_email_e_lado_dominante():
    with app.app_context():
        client = app.test_client()

        u = Usuario.query.filter_by(email='aluno@test.com').first()
        if not u:
            u = Usuario(nome='Aluno Teste', email='aluno@test.com', perfil='aluno', ativo=True)
            u.set_senha('aluno123')
            db.session.add(u)
            db.session.commit()
            al = Aluno(usuario_id=u.id, nome='Aluno Teste', ativo=True)
            db.session.add(al)
            db.session.commit()
        else:
            u.set_senha('aluno123')
            u.ativo = True
            db.session.commit()

        # Login aluno
        client.post('/auth/login', data={'email': 'aluno@test.com', 'senha': 'aluno123'}, follow_redirects=True)

        # Alterar e-mail e lado dominante
        novo_email = 'aluno_alterado@test.com'
        u_dup = Usuario.query.filter_by(email=novo_email).first()
        if u_dup:
            db.session.delete(u_dup)
            db.session.commit()

        resp = client.post('/aluno/perfil', data={
            'acao': 'dados',
            'email': novo_email,
            'lado_dominante': 'canhoto',
            'telefone': '(73) 99111-2233',
            'data_nascimento': '2000-01-01'
        }, follow_redirects=True)
        assert resp.status_code == 200

        db.session.refresh(u)
        assert u.email == novo_email, f"Esperava {novo_email}, obteve {u.email}"
        al = Aluno.query.filter_by(usuario_id=u.id).first()
        assert al.lado_dominante == 'canhoto', f"Esperava 'canhoto', obteve {al.lado_dominante}"
        print("✓ Aluno alterou lado dominante e e-mail de acesso com sucesso!")

        # Valida que novo e-mail funciona para login
        client.get('/auth/logout')
        resp_login_novo = client.post('/auth/login', data={'email': novo_email, 'senha': 'aluno123'}, follow_redirects=True)
        assert resp_login_novo.status_code == 200
        assert "Meu Perfil" in resp_login_novo.get_data(as_text=True) or "Painel" in resp_login_novo.get_data(as_text=True)
        print("✓ Login com o novo e-mail realizado com sucesso!")

        # Restaura e-mail original para não quebrar outros testes
        u.email = 'aluno@test.com'
        db.session.commit()


def test_galeria_video_embed():
    with app.app_context():
        # Cria item com link padrão do youtube
        item = GaleriaItem.query.filter_by(titulo='Video Teste Embed').first()
        if not item:
            item = GaleriaItem(
                titulo='Video Teste Embed',
                tipo='video',
                url_video='https://www.youtube.com/watch?v=dQw4w9WgXcQ',
                ativo=True
            )
            db.session.add(item)
            db.session.commit()

        garantir_esquema_banco()
        db.session.refresh(item)
        assert item.url_video == 'https://www.youtube.com/embed/dQw4w9WgXcQ'
        assert item.url_video_embed == 'https://www.youtube.com/embed/dQw4w9WgXcQ'

        client = app.test_client()
        resp = client.get('/')
        assert resp.status_code == 200
        html = resp.get_data(as_text=True)
        assert 'https://www.youtube.com/embed/dQw4w9WgXcQ' in html
        assert 'allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture; web-share"' in html
        print("✓ Embed de vídeo na galeria renderizado com URL de embed correta e permissões completas!")

        db.session.delete(item)
        db.session.commit()


if __name__ == '__main__':
    test_converter_para_embed()
    test_usuario_criado_sempre_ativo()
    test_aluno_muda_email_e_lado_dominante()
    test_galeria_video_embed()
    print("\nTODOS OS TESTES DAS NOVAS FUNCIONALIDADES PASSARAM COM 100% DE SUCESSO!")
