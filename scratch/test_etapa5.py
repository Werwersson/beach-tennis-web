import os
import sys

# Garante path da aplicacao
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from datetime import datetime, date, time
from app import create_app
from app.extensions import db
from app.models import Usuario, Aluno, Turma, TurmaAluno, Aula, Presenca, Avaliacao, AvaliacaoNota, Exercicio
from app.models.avaliacao import CRITERIOS_AVALIACAO

def test_etapa5():
    app = create_app('development')
    app.config['WTF_CSRF_ENABLED'] = False
    app.config['TESTING'] = True
    with app.app_context():
        print("=== TESTE ETAPA 5: CHAMADA RÁPIDA, RELATÓRIO DE FREQUÊNCIA E AVALIAÇÃO PERIÓDICA ===")
        
        # 1. Garante professor admin
        admin = Usuario.query.filter_by(perfil='admin').first()
        assert admin is not None, "Professor admin deve existir"
        print(f"[OK] Admin localizado: {admin.email}")

        # 2. Garante alunos para teste
        aluno1 = Aluno.query.filter_by(ativo=True).first()
        if not aluno1:
            u_aluno = Usuario(nome='Carlos Silva', email='aluno1@teste.com', perfil='aluno')
            u_aluno.set_senha('senha123')
            db.session.add(u_aluno)
            db.session.flush()
            aluno1 = Aluno(usuario_id=u_aluno.id, nome='Carlos Silva', nivel='intermediario', lado_dominante='destro', ativo=True)
            db.session.add(aluno1)
            db.session.commit()
            print("[OK] Aluno 1 de teste criado")

        aluno2 = Aluno.query.filter(Aluno.id != aluno1.id, Aluno.ativo == True).first()
        if not aluno2:
            u_aluno2 = Usuario(nome='Mariana Costa', email='aluno2@teste.com', perfil='aluno')
            u_aluno2.set_senha('senha123')
            db.session.add(u_aluno2)
            db.session.flush()
            aluno2 = Aluno(usuario_id=u_aluno2.id, nome='Mariana Costa', nivel='avancado', lado_dominante='canhoto', ativo=True)
            db.session.add(aluno2)
            db.session.commit()
            print("[OK] Aluno 2 de teste criado")

        # 3. Garante turma e matricula alunos
        turma = Turma.query.filter_by(ativa=True).first()
        if not turma:
            turma = Turma(
                nome='Turma Intermediário Manhã',
                nivel='intermediario',
                dias_semana='1,3',
                horario_inicio=time(8, 0),
                horario_fim=time(9, 30),
                local='Quadra Central',
                vagas=6,
                ativa=True
            )
            db.session.add(turma)
            db.session.commit()
            print("[OK] Turma de teste criada")

        # Matricula aluno 1 na turma
        ta1 = TurmaAluno.query.filter_by(turma_id=turma.id, aluno_id=aluno1.id).first()
        if not ta1:
            ta1 = TurmaAluno(turma_id=turma.id, aluno_id=aluno1.id, ativo=True)
            db.session.add(ta1)
            db.session.commit()

        # Matricula aluno 2 na turma
        ta2 = TurmaAluno.query.filter_by(turma_id=turma.id, aluno_id=aluno2.id).first()
        if not ta2:
            ta2 = TurmaAluno(turma_id=turma.id, aluno_id=aluno2.id, ativo=True)
            db.session.add(ta2)
            db.session.commit()

        # 4. Cria uma aula para teste da chamada
        aula = Aula(
            turma_id=turma.id,
            data_hora=datetime.now(),
            duracao_minutos=90,
            objetivo='Treino tático de transição e saque',
            status='agendada'
        )
        db.session.add(aula)
        db.session.commit()
        print(f"[OK] Aula criada: ID={aula.id}, Turma={turma.nome}")

        # 5. Testa cliente HTTP autenticado como Admin
        client = app.test_client()
        with client.session_transaction() as sess:
            sess['_user_id'] = str(admin.id)
            sess['_fresh'] = True

        # Teste GET /admin/aulas/<id>/chamada
        resp_get_chamada = client.get(f'/admin/aulas/{aula.id}/chamada')
        assert resp_get_chamada.status_code == 200, f"GET chamada retornou {resp_get_chamada.status_code}"
        assert 'Chamada Rápida de Presença' in resp_get_chamada.get_data(as_text=True)
        print("[OK] GET /admin/aulas/<id>/chamada respondeu 200 com template correto")

        # Teste POST /admin/aulas/<id>/chamada
        dados_chamada = {
            'aluno_ids': [str(aluno1.id), str(aluno2.id)],
            f'status_{aluno1.id}': 'presente',
            f'justificativa_{aluno1.id}': '',
            f'status_{aluno2.id}': 'falta_justificada',
            f'justificativa_{aluno2.id}': 'Avisou com 24h de antecedência por viagem'
        }
        resp_post_chamada = client.post(f'/admin/aulas/{aula.id}/chamada', data=dados_chamada, follow_redirects=True)
        assert resp_post_chamada.status_code == 200
        print("[OK] POST /admin/aulas/<id>/chamada processado com sucesso")

        # Verifica no banco
        db.session.expire_all()
        aula_atualizada = db.session.get(Aula, aula.id)
        assert aula_atualizada.status == 'realizada', f"Status da aula deveria ser 'realizada', mas é {aula_atualizada.status}"
        p1 = Presenca.query.filter_by(aula_id=aula.id, aluno_id=aluno1.id).first()
        p2 = Presenca.query.filter_by(aula_id=aula.id, aluno_id=aluno2.id).first()
        assert p1 is not None and p1.status == 'presente', "Presenca do aluno 1 deve ser 'presente'"
        assert p2 is not None and p2.status == 'falta_justificada', "Presenca do aluno 2 deve ser 'falta_justificada'"
        assert 'viagem' in p2.justificativa.lower()
        print("[OK] Presencas conferidas no banco de dados e aula alterada para 'realizada'")

        # 6. Teste GET /admin/presencas (Relatório de Frequência)
        resp_presencas = client.get('/admin/presencas')
        assert resp_presencas.status_code == 200
        html_presencas = resp_presencas.get_data(as_text=True)
        assert 'Frequência por Aluno' in html_presencas
        assert 'Frequência por Turma' in html_presencas
        assert 'Histórico Detalhado' in html_presencas
        print("[OK] GET /admin/presencas carregou abas e relatórios com sucesso")

        # Filtros de presencas
        resp_filtro = client.get(f'/admin/presencas?turma_id={turma.id}&periodo=mes_atual')
        assert resp_filtro.status_code == 200
        print("[OK] Filtros de período e turma em /admin/presencas funcionando")

        # 7. Teste de Avaliação Periódica
        resp_get_nova_aval = client.get(f'/admin/avaliacoes/nova?aluno_id={aluno1.id}')
        assert resp_get_nova_aval.status_code == 200
        html_nova = resp_get_nova_aval.get_data(as_text=True)
        assert '11 Critérios Oficiais' in html_nova
        assert 'Saque' in html_nova
        assert 'Aspecto Mental & Foco' in html_nova
        print("[OK] GET /admin/avaliacoes/nova respondeu 200 com os 11 critérios")

        # Submete avaliação periódica completa
        dados_avaliacao = {
            'aluno_id': aluno1.id,
            'categoria': 'C',
            'data': date.today().strftime('%Y-%m-%d'),
            'nota_saque': 8.0,
            'nota_forehand': 7.5,
            'nota_backhand': 7.0,
            'nota_voleio': 8.5,
            'nota_smash': 9.0,
            'nota_bandeja_defesa': 6.5,
            'nota_deslocamento': 7.5,
            'nota_posicionamento_dupla': 8.0,
            'nota_leitura_jogo': 8.0,
            'nota_condicionamento': 7.0,
            'nota_mental_foco': 8.5,
            'pontos_fortes': 'Excelente potência no smash e ótimo saque colocado no cantinho.',
            'pontos_melhorar': 'Trabalhar recuperação defensiva em bolas na linha de fundo.',
            'metas_proximo_ciclo': 'Aprimorar bandeja e sincronia de movimentação com o parceiro.',
            'comentarios': 'Atleta muito focado e dedicado aos treinos semanais.',
            'link_video_analise': 'https://www.youtube.com/watch?v=dQw4w9WgXcQ'
        }
        resp_post_aval = client.post('/admin/avaliacoes/nova', data=dados_avaliacao, follow_redirects=False)
        assert resp_post_aval.status_code == 302, f"POST nova avaliacao deveria redirecionar, retornou {resp_post_aval.status_code}"
        location = resp_post_aval.headers['Location']
        print(f"[OK] POST /admin/avaliacoes/nova redirecionou para: {location}")

        # Busca a avaliação criada no banco
        aval = Avaliacao.query.filter_by(aluno_id=aluno1.id).order_by(Avaliacao.id.desc()).first()
        assert aval is not None, "Avaliacao deve ter sido salva"
        assert len(aval.notas) == 11, f"Deve conter 11 notas, possui {len(aval.notas)}"
        
        # Média esperada: (8.0 + 7.5 + 7.0 + 8.5 + 9.0 + 6.5 + 7.5 + 8.0 + 8.0 + 7.0 + 8.5) / 11 = 85.5 / 11 = 7.77... -> 7.8
        media_esperada = round(sum([8.0, 7.5, 7.0, 8.5, 9.0, 6.5, 7.5, 8.0, 8.0, 7.0, 8.5]) / 11, 1)
        assert aval.media == media_esperada, f"Média calculada {aval.media} difere de {media_esperada}"
        print(f"[OK] Avaliacao salva com 11 notas e média correta: {aval.media}")

        # 8. Teste GET /admin/avaliacoes/<id> (Detalhes da Avaliação)
        resp_detalhe = client.get(f'/admin/avaliacoes/{aval.id}')
        assert resp_detalhe.status_code == 200
        html_detalhe = resp_detalhe.get_data(as_text=True)
        assert 'Desempenho por Critério Avaliado' in html_detalhe
        assert 'Pontos Fortes Demonstrados' in html_detalhe
        assert 'Análise Biomecânica em Vídeo' in html_detalhe
        assert 'dQw4w9WgXcQ' in html_detalhe  # YouTube embed id
        # Confirma que Chart.js NÃO foi inserido nesta etapa (sem canvas ou instâncias de gráficos)
        assert 'new Chart(' not in html_detalhe and '<canvas' not in html_detalhe, "Não deve conter gráficos Chart.js nesta etapa"
        print("[OK] GET /admin/avaliacoes/<id> exibiu todos os detalhes sem Chart.js (respeitando a restrição da Etapa 5)")

        # 9. Teste Edição da Avaliação
        resp_get_edit = client.get(f'/admin/avaliacoes/{aval.id}/editar')
        assert resp_get_edit.status_code == 200
        dados_avaliacao['nota_saque'] = 9.0
        resp_post_edit = client.post(f'/admin/avaliacoes/{aval.id}/editar', data=dados_avaliacao, follow_redirects=True)
        assert resp_post_edit.status_code == 200
        db.session.expire_all()
        aval_editada = db.session.get(Avaliacao, aval.id)
        assert aval_editada.get_nota('saque') == 9.0, "Nota de saque atualizada para 9.0"
        print("[OK] Edição de avaliação validada com sucesso")

        # 10. Teste Listagem de Avaliações
        resp_lista = client.get('/admin/avaliacoes')
        assert resp_lista.status_code == 200
        assert aluno1.nome in resp_lista.get_data(as_text=True)
        print("[OK] GET /admin/avaliacoes listando avaliações corretamente")

        # 11. Teste Exclusão de Avaliação
        resp_excluir = client.post(f'/admin/avaliacoes/{aval.id}/excluir', follow_redirects=False)
        assert resp_excluir.status_code == 302
        db.session.expire_all()
        aval_removida = db.session.get(Avaliacao, aval.id)
        assert aval_removida is None, "Avaliação deve ter sido excluída"
        notas_restantes = AvaliacaoNota.query.filter_by(avaliacao_id=aval.id).all()
        assert len(notas_restantes) == 0, "Notas da avaliação devem ser excluídas em cascata"
        print("[OK] Exclusão de avaliação e cascata de notas verificadas com sucesso")

        print("\n=== TODOS OS TESTES DA ETAPA 5 FORAM CONCLUÍDOS COM 100% DE SUCESSO! ===")

if __name__ == '__main__':
    test_etapa5()
