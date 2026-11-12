"""Teste do fluxo de avaliação por categoria (nota bruta x curva de aprendizado).

Roda em uma cópia temporária do banco para não alterar os dados reais.
"""
import os
import sys
import tempfile
import shutil
from datetime import date, timedelta

BASE = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, BASE)
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

# Copia o banco antes de importar o app (a config lê DATABASE_URL na importação)
TEMP_DB = os.path.join(tempfile.gettempdir(), f'bt_test_categoria_{os.getpid()}.db')
shutil.copyfile(os.path.join(BASE, 'beach_tennis.db'), TEMP_DB)
os.environ['DATABASE_URL'] = 'sqlite:///' + TEMP_DB.replace('\\', '/')

from app import create_app
from app.extensions import db
from app.models import Aluno, Avaliacao, AvaliacaoNota
from app.models.avaliacao import CRITERIOS_AVALIACAO
from app.utils.analytics import get_aluno_analytics
from app.utils.pdf_generator import gerar_relatorio_pdf_aluno


def definir_notas(avaliacao, valor):
    for nota in list(avaliacao.notas):
        db.session.delete(nota)
    db.session.flush()
    for crit, _ in CRITERIOS_AVALIACAO:
        db.session.add(AvaliacaoNota(avaliacao_id=avaliacao.id, criterio=crit, nota=valor))


def main():
    app = create_app('development')
    app.config['TESTING'] = True
    app.config['WTF_CSRF_ENABLED'] = False

    # ── Preparação e cálculos (contexto de banco) ─────────────────────
    with app.app_context():
        aluno = Aluno.query.filter_by(nome='Lucas Silva').order_by(Aluno.id.desc()).first()
        assert aluno is not None, 'Aluno de teste não encontrado'
        aluno.categoria = 'C'
        aluno_id = aluno.id

        avaliacoes = (Avaliacao.query.filter_by(aluno_id=aluno_id)
                      .order_by(Avaliacao.data, Avaliacao.id).all())
        assert len(avaliacoes) >= 2, 'Esperava ao menos 2 avaliações no banco copiado'

        # Cenário: forte na D, promovido para a C (nota cai), evolui na C (índice sobe)
        aval_d, aval_c1 = avaliacoes[0], avaliacoes[1]
        aval_d.data = date.today() - timedelta(days=120)
        aval_d.categoria = 'D'
        definir_notas(aval_d, 8.0)

        aval_c1.data = date.today() - timedelta(days=60)
        aval_c1.categoria = 'C'
        definir_notas(aval_c1, 7.2)

        aval_c2 = Avaliacao(
            aluno_id=aluno_id,
            data=date.today() - timedelta(days=5),
            categoria='C',
            pontos_fortes='Consolidação na categoria C.',
            pontos_melhorar='Ajustar transição.',
            metas_proximo_ciclo='Subir para a B.',
        )
        db.session.add(aval_c2)
        db.session.flush()
        definir_notas(aval_c2, 7.6)
        db.session.commit()

        analytics = get_aluno_analytics(aluno)

        assert analytics['total_avaliacoes'] == 3
        assert analytics['media_inicial'] == 8.0, analytics['media_inicial']
        assert analytics['media_atual'] == 7.6, analytics['media_atual']
        assert analytics['diff_geral'] == -0.4, analytics['diff_geral']
        assert analytics['indice_inicial'] == 56.0, analytics['indice_inicial']
        assert analytics['indice_atual'] == 60.8, analytics['indice_atual']
        assert analytics['diff_indice'] == 4.8, analytics['diff_indice']
        assert analytics['tem_multiplas_categorias'] is True
        assert len(analytics['promocoes']) == 1
        promo = analytics['promocoes'][0]
        assert (promo['de'], promo['para']) == ('D', 'C')
        assert promo['delta_media'] < 0 and promo['delta_indice'] > 0
        assert analytics['linha_indices'] == [56.0, 57.6, 60.8], analytics['linha_indices']
        print('[OK] Analytics: nota bruta cai (-0.4) e índice sobe (+4.8) na promoção D → C')

        pdf = gerar_relatorio_pdf_aluno(aluno, analytics)
        assert pdf.startswith(b'%PDF') and len(pdf) > 1000
        print(f'[OK] PDF gerado com {len(pdf)} bytes')

    # ── Telas do aluno ────────────────────────────────────────────────
    client_aluno = app.test_client()
    r = client_aluno.post('/auth/login', data={'email': 'aluno@beachtennis.com', 'senha': 'aluno123'})
    assert r.status_code == 302 and '/aluno/painel' in r.headers['Location'], r.headers.get('Location')

    resp = client_aluno.get('/aluno/evolucao')
    assert resp.status_code == 200, resp.status_code
    html = resp.get_data(as_text=True)
    assert 'Curva de Aprendizado' in html
    assert 'Nota na Categoria' in html
    assert 'alunoLinhaChart' in html
    assert '"de": "D"' in html and '"para": "C"' in html
    assert 'Sua Trajetória de Categoria' in html
    print('[OK] Tela /aluno/evolucao exibe nota, curva e marcador de promoção D → C')

    html_painel = client_aluno.get('/aluno/painel').get_data(as_text=True)
    assert 'Índice Técnico' in html_painel
    assert 'Categoria C' in html_painel
    print('[OK] Painel do aluno exibe categoria e Índice Técnico')

    # ── Telas do admin ────────────────────────────────────────────────
    client_admin = app.test_client()
    r = client_admin.post('/auth/login', data={'email': 'professor@beachtennis.com', 'senha': 'admin123'})
    assert r.status_code == 302 and '/admin/dashboard' in r.headers['Location'], r.headers.get('Location')

    resp_perfil = client_admin.get(f'/admin/alunos/{aluno_id}')
    assert resp_perfil.status_code == 200, resp_perfil.status_code
    html_perfil = resp_perfil.get_data(as_text=True)
    assert 'Curva de Aprendizado' in html_perfil
    assert 'mudou de categoria' in html_perfil
    assert '"de": "D"' in html_perfil and '"para": "C"' in html_perfil
    print('[OK] Perfil admin exibe a curva e o alerta de mudança de categoria')

    dash = client_admin.get('/admin/dashboard').get_data(as_text=True)
    assert 'Maior Evolução Técnica (Índice)' in dash
    print('[OK] Dashboard exibe o ranking por Índice Técnico')

    # ── Nova avaliação na categoria B sincroniza a categoria do aluno ─
    dados_form = {
        'aluno_id': aluno_id,
        'categoria': 'B',
        'data': date.today().strftime('%Y-%m-%d'),
        'pontos_fortes': 'Bom ciclo na B.',
    }
    for crit, _ in CRITERIOS_AVALIACAO:
        dados_form[f'nota_{crit}'] = '7.5'
    resp = client_admin.post('/admin/avaliacoes/nova', data=dados_form, follow_redirects=False)
    assert resp.status_code == 302, (resp.status_code, resp.get_data(as_text=True)[:800])

    with app.app_context():
        aluno = db.session.get(Aluno, aluno_id)
        assert aluno.categoria == 'B', aluno.categoria
        ultima = (Avaliacao.query.filter_by(aluno_id=aluno_id)
                  .order_by(Avaliacao.data.desc(), Avaliacao.id.desc()).first())
        assert ultima.categoria_efetiva == 'B'
        assert ultima.indice_tecnico == 66.0
        ultima_id = ultima.id
    print('[OK] Nova avaliação na B atualizou a categoria do aluno e o índice (66.0)')

    # ── Edição para a categoria A também sincroniza o cadastro ────────
    dados_edit = dict(dados_form)
    dados_edit['categoria'] = 'A'
    for crit, _ in CRITERIOS_AVALIACAO:
        dados_edit[f'nota_{crit}'] = '8.0'
    resp = client_admin.post(f'/admin/avaliacoes/{ultima_id}/editar', data=dados_edit, follow_redirects=False)
    assert resp.status_code == 302, (resp.status_code, resp.get_data(as_text=True)[:800])

    with app.app_context():
        aluno = db.session.get(Aluno, aluno_id)
        avaliacao = db.session.get(Avaliacao, ultima_id)
        assert aluno.categoria == 'A', aluno.categoria
        assert avaliacao.categoria_efetiva == 'A'
        assert avaliacao.indice_tecnico == 76.0, avaliacao.indice_tecnico
    print('[OK] Edição para a categoria A sincronizou o cadastro e o índice (76.0)')

    print('\n=== TESTES DE CATEGORIA CONCLUÍDOS COM SUCESSO ===')


if __name__ == '__main__':
    try:
        main()
    finally:
        try:
            from app.extensions import db as _db
            with app.app_context():  # noqa: F821
                _db.engine.dispose()
        except Exception:
            pass
        if os.path.exists(TEMP_DB):
            try:
                os.remove(TEMP_DB)
            except OSError:
                pass
