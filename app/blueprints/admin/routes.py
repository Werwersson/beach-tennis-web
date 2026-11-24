import os
import re
import json
from datetime import datetime, date, time, timedelta
from flask import (Blueprint, render_template, redirect, url_for, flash,
                   request, current_app, abort, jsonify, Response)
from werkzeug.utils import secure_filename
from app.extensions import db
from app.models import (Usuario, Aluno, MetaAluno, Turma, TurmaAluno,
                        Exercicio, Aula, AulaExercicio, Presenca,
                        Avaliacao, AvaliacaoNota, Depoimento,
                        ConfiguracaoSite, Plano, Conquista,
                        Modalidade, GaleriaItem, MensagemContato, TrofeuAluno,
                        Partida, PontoPartida)
from app.models.exercicio import CATEGORIAS_EXERCICIO, NIVEIS_EXERCICIO
from app.models.avaliacao import CRITERIOS_AVALIACAO
from app.models.categoria import CATEGORIAS_BEACH_TENNIS, CATEGORIA_PESOS
from app.utils.decorators import admin_required
from .forms import (AlunoForm, ExercicioForm, TurmaForm, AulaForm,
                    GerarAulasRecorrentesForm, CancelarAulaForm,
                    RemarcarAulaForm, AulaExercicioForm, AvaliacaoForm,
                    ConfiguracaoSiteForm, ConquistaForm, ModalidadeForm,
                    PlanoForm, DepoimentoForm, GaleriaItemForm, TrofeuForm,
                    PartidaForm)

from app.utils.analytics import get_aluno_analytics
from app.utils.pdf_generator import gerar_relatorio_pdf_aluno
from app.utils.bt_tracker import calcular_estatisticas_partida
from app.utils.bt_tracker_pdf import gerar_pdf_bt_tracker
from app.utils.schema_migration import garantir_esquema_banco
from app.utils.video import converter_para_embed

admin_bp = Blueprint('admin', __name__)


def sincronizar_categoria_aluno(aluno):
    """Mantém a categoria atual do aluno alinhada à avaliação mais recente.

    A avaliação guarda a categoria daquele ciclo; o cadastro do aluno funciona
    como atalho e valor padrão. Quando existe avaliação, a mais recente manda,
    para que a promoção registrada no ciclo apareça automaticamente no perfil.
    """
    ultima = (Avaliacao.query
              .filter_by(aluno_id=aluno.id)
              .order_by(Avaliacao.data.desc(), Avaliacao.id.desc())
              .first())
    if ultima and ultima.categoria:
        aluno.categoria = ultima.categoria_efetiva


# ── Utilitários ────────────────────────────────────────────────────────────
def _usar_vercel_blob():
    """Vercel Blob é usado quando o store está conectado (Vercel) ou há token."""
    return bool(os.environ.get('BLOB_STORE_ID') or os.environ.get('BLOB_READ_WRITE_TOKEN'))


def salvar_imagem(arquivo, prefixo='upload'):
    if not arquivo or not arquivo.filename:
        return None
    ext = arquivo.filename.rsplit('.', 1)[-1].lower()
    allowed = current_app.config.get('ALLOWED_EXTENSIONS', {'jpg', 'jpeg', 'png', 'gif', 'webp'})
    if ext not in allowed:
        return None
    nome_seguro = secure_filename(f"{prefixo}_{int(datetime.utcnow().timestamp())}_{arquivo.filename}")
    conteudo = arquivo.read()

    if _usar_vercel_blob():
        # Vercel Blob: necessário porque o filesystem da função é somente leitura.
        from vercel.blob import sync as blob
        resultado = blob.put_blob(
            f'beach-tennis/{nome_seguro}',
            conteudo,
            access='public',
            add_random_suffix=True,
            content_type=getattr(arquivo, 'mimetype', None),
        )
        return resultado.url

    caminho = os.path.join(current_app.config['UPLOAD_FOLDER'], nome_seguro)
    with open(caminho, 'wb') as destino:
        destino.write(conteudo)
    return nome_seguro


def remover_imagem(valor):
    """Remove uma imagem local ou do Vercel Blob, ignorando URLs externas."""
    if not valor:
        return
    valor = str(valor)
    if valor.startswith(('http://', 'https://')):
        if _usar_vercel_blob():
            try:
                from vercel.blob import sync as blob
                blob.delete_blob(valor)
            except Exception as erro:  # não impede a edição/exclusão do registro
                current_app.logger.warning('Falha ao remover imagem remota %s: %s', valor, erro)
        return

    valor_limpo = secure_filename(os.path.basename(valor))
    if not valor_limpo:
        return
    caminho = os.path.join(current_app.config['UPLOAD_FOLDER'], valor_limpo)
    if os.path.exists(caminho):
        try:
            os.remove(caminho)
        except OSError:
            pass


def extrair_youtube_id(url):
    if not url:
        return None
    patterns = [
        r'(?:v=|\/)([0-9A-Za-z_-]{11})',
        r'(?:youtu\.be\/)([0-9A-Za-z_-]{11})',
        r'(?:embed\/)([0-9A-Za-z_-]{11})',
    ]
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)
    return None


# ── DASHBOARD ──────────────────────────────────────────────────────────────
@admin_bp.route('/dashboard')
@admin_required
def dashboard():
    hoje = date.today()
    inicio_semana = hoje - timedelta(days=hoje.weekday())
    fim_semana = inicio_semana + timedelta(days=6)

    total_alunos = Aluno.query.filter_by(ativo=True).count()
    aulas_hoje = Aula.query.filter(
        db.func.date(Aula.data_hora) == hoje,
        Aula.status != 'cancelada'
    ).order_by(Aula.data_hora).all()

    aulas_semana = Aula.query.filter(
        db.func.date(Aula.data_hora) >= inicio_semana,
        db.func.date(Aula.data_hora) <= fim_semana,
        Aula.status != 'cancelada'
    ).order_by(Aula.data_hora).all()

    inicio_mes = hoje.replace(day=1)
    presencas_mes = Presenca.query.join(Aula).filter(
        db.func.date(Aula.data_hora) >= inicio_mes,
        db.func.date(Aula.data_hora) <= hoje
    ).all()
    total_p = len(presencas_mes)
    presentes = sum(1 for p in presencas_mes if p.status in ('presente', 'reposicao'))
    faltas_mes = sum(1 for p in presencas_mes if p.status == 'falta')
    justificadas_mes = sum(1 for p in presencas_mes if p.status in ('falta_justificada', 'ausencia_avisada'))
    reposicoes_mes = sum(1 for p in presencas_mes if p.status == 'reposicao')
    taxa_presenca = round((presentes / total_p * 100) if total_p > 0 else 0)

    # Alunos sem avaliação há mais de 30 dias ou nunca avaliados
    limite_30d = hoje - timedelta(days=30)
    alunos_ativos = Aluno.query.filter_by(ativo=True).order_by(Aluno.nome).all()
    alunos_sem_avaliacao = []
    
    for a in alunos_ativos:
        ultima = Avaliacao.query.filter_by(aluno_id=a.id).order_by(Avaliacao.data.desc(), Avaliacao.id.desc()).first()
        a.ultima_avaliacao = ultima.data if ultima else None
        if not ultima:
            a.dias_sem_avaliacao = 999  # nunca avaliado
            alunos_sem_avaliacao.append(a)
        elif ultima.data < limite_30d:
            a.dias_sem_avaliacao = (hoje - ultima.data).days
            alunos_sem_avaliacao.append(a)

    # Ordena os mais urgentes (mais dias sem avaliação)
    alunos_sem_avaliacao.sort(key=lambda x: x.dias_sem_avaliacao, reverse=True)

    # Alunos com maior evolução (índice corrigido pela categoria, 1ª vs última)
    alunos_evolucao = []
    for a in alunos_ativos:
        avals = Avaliacao.query.filter_by(aluno_id=a.id).order_by(Avaliacao.data.asc(), Avaliacao.id.asc()).all()
        if len(avals) >= 2:
            primeira = avals[0]
            ultima = avals[-1]
            diff = round(ultima.indice_tecnico - primeira.indice_tecnico, 1)
            alunos_evolucao.append({
                'aluno': a,
                'primeira_media': primeira.media,
                'ultima_media': ultima.media,
                'primeira_indice': primeira.indice_tecnico,
                'ultima_indice': ultima.indice_tecnico,
                'primeira_categoria': primeira.categoria_curta,
                'ultima_categoria': ultima.categoria_curta,
                'diff': diff,
                'diff_bruto': round(ultima.media - primeira.media, 1),
                'total_avaliacoes': len(avals),
                'ultima_data': ultima.data
            })
    alunos_evolucao.sort(key=lambda x: x['diff'], reverse=True)

    return render_template('admin/dashboard.html',
        total_alunos=total_alunos,
        aulas_hoje=aulas_hoje,
        aulas_semana=aulas_semana,
        taxa_presenca=taxa_presenca,
        total_presencas_mes=total_p,
        presentes_mes=presentes,
        faltas_mes=faltas_mes,
        justificadas_mes=justificadas_mes,
        reposicoes_mes=reposicoes_mes,
        alunos_sem_avaliacao=alunos_sem_avaliacao[:8],
        alunos_evolucao=alunos_evolucao[:5]
    )

# ── PARTIDAS – NOVAS FUNCIONALIDADES ────────────────────────────────────────

@admin_bp.route('/partidas/comparar', methods=['GET', 'POST'])
@admin_required
def partidas_comparar():
    """Página para comparar duas partidas lado a lado."""
    if request.method == 'POST':
        id1 = request.form.get('partida1')
        id2 = request.form.get('partida2')
        if not id1 or not id2:
            flash('Selecione duas partidas para comparar.', 'warning')
            return redirect(url_for('admin.partidas_comparar'))
        partida1 = db.get_or_404(Partida, int(id1))
        partida2 = db.get_or_404(Partida, int(id2))
        stats1 = calcular_estatisticas_partida(partida1)
        stats2 = calcular_estatisticas_partida(partida2)
        return render_template('admin/partidas/comparar_resultado.html',
            partida1=partida1, partida2=partida2, stats1=stats1, stats2=stats2)
    # GET: exibir formulário de seleção
    partidas = Partida.query.order_by(Partida.id.desc()).all()
    return render_template('admin/partidas/comparar.html', partidas=partidas)

@admin_bp.route('/partidas/set_score_summary')
@admin_required
def partidas_set_score_summary():
    """Resumo de número de sets por fase."""
    # Agrupa por fase e calcula média de sets (contando sets diferentes de zero)
    phases = db.session.query(
        Partida.fase,
        db.func.count(Partida.id),
        db.func.avg(
            (db.case((Partida.set1_dupla1 != 0, 1), else_=0) +
             db.case((Partida.set2_dupla1 != 0, 1), else_=0) +
             db.case((Partida.set3_dupla1 != 0, 1), else_=0) +
             db.case((Partida.set4_dupla1 != 0, 1), else_=0))
        ).label('avg_sets')
    ).group_by(Partida.fase).all()
    return render_template('admin/partidas/set_score_summary.html', phases=phases)

@admin_bp.route('/partidas/<int:id>/heatmap_json')
@admin_required
def partida_heatmap_json(id):
    """Retorna os pontos da partida filtrados por set (query param ?set=1)."""
    set_num = request.args.get('set', type=int, default=1)
    partida = db.get_or_404(Partida, id)
    pontos = PontoPartida.query.filter_by(partida_id=id, set_num=set_num).all()
    data = [
        {
            'origem_x': p.origem_x,
            'origem_y': p.origem_y,
            'destino_x': p.destino_x,
            'destino_y': p.destino_y,
            'tipo_desfecho': p.tipo_desfecho
        } for p in pontos if p.origem_x is not None and p.origem_y is not None
    ]
    return jsonify(data)

@admin_bp.route('/partidas/<int:id>/set_<int:set_num>_csv')
@admin_required
def partida_set_csv(id, set_num):
    """Exporta CSV contendo apenas os pontos do set especificado."""
    partida = db.get_or_404(Partida, id)
    pontos = PontoPartida.query.filter_by(partida_id=id, set_num=set_num).all()
    # Construir CSV simples
    header = 'numero_ponto,origem_x,origem_y,destino_x,destino_y,tipo_desfecho\n'
    rows = []
    for p in pontos:
        rows.append(f"{p.numero_ponto},{p.origem_x or ''},{p.origem_y or ''},{p.destino_x or ''},{p.destino_y or ''},{p.tipo_desfecho}")
    csv_content = header + '\n'.join(rows)
    response = Response(csv_content, mimetype='text/csv')
    response.headers.set('Content-Disposition', f'attachment; filename=partida_{id}_set{set_num}.csv')
    return response


# ── ALUNOS ────────────────────────────────────────────────────────────────
@admin_bp.route('/alunos')
@admin_required
def alunos_lista():
    q = request.args.get('q', '').strip()
    nivel = request.args.get('nivel', '').strip()
    categoria = request.args.get('categoria', '').strip()
    status = request.args.get('status', '').strip()

    query = Aluno.query
    if q:
        query = query.join(Usuario).filter(
            db.or_(Aluno.nome.ilike(f'%{q}%'), Usuario.email.ilike(f'%{q}%'))
        )
    if nivel:
        query = query.filter(Aluno.nivel == nivel)
    if categoria:
        query = query.filter(Aluno.categoria == categoria)
    if status == 'ativo':
        query = query.filter(Aluno.ativo.is_(True))
    elif status == 'inativo':
        query = query.filter(Aluno.ativo.is_(False))

    alunos = query.order_by(Aluno.nome).all()
    return render_template('admin/alunos/lista.html',
        alunos=alunos, total=len(alunos), q=q, nivel=nivel,
        categoria=categoria, categorias=CATEGORIAS_BEACH_TENNIS, status=status)


@admin_bp.route('/alunos/novo', methods=['GET', 'POST'])
@admin_required
def aluno_novo():
    form = AlunoForm()
    if form.validate_on_submit():
        email_limpo = form.email.data.lower().strip()
        usuario = Usuario(
            nome=form.nome.data.strip(),
            email=email_limpo,
            perfil='aluno',
            ativo=True  # Sempre ativo ao ser criado pelo professor
        )
        senha_inicial = form.senha.data if form.senha.data else 'beach123'
        usuario.set_senha(senha_inicial)
        db.session.add(usuario)
        db.session.flush()

        foto_nome = salvar_imagem(form.foto.data, 'aluno') if form.foto.data else None

        aluno = Aluno(
            usuario_id=usuario.id,
            nome=form.nome.data.strip(),
            telefone=form.telefone.data.strip() if form.telefone.data else None,
            data_nascimento=form.data_nascimento.data,
            nivel=form.nivel.data,
            categoria=form.categoria.data,
            lado_dominante=form.lado_dominante.data,
            objetivo=form.objetivo.data,
            observacoes=form.observacoes.data.strip() if form.observacoes.data else None,
            foto=foto_nome,
            ativo=True  # Sempre ativo ao ser criado pelo professor
        )
        db.session.add(aluno)
        db.session.commit()

        flash(f'Aluno "{aluno.nome}" cadastrado com sucesso! Usuário de acesso criado.', 'success')
        return redirect(url_for('admin.aluno_perfil', id=aluno.id))

    return render_template('admin/alunos/form.html', form=form, aluno=None)


@admin_bp.route('/alunos/<int:id>')
@admin_required
def aluno_perfil(id):
    aluno = db.get_or_404(Aluno, id)
    presencas = (Presenca.query
        .filter_by(aluno_id=id)
        .join(Aula)
        .order_by(Aula.data_hora.desc())
        .limit(15).all())

    analytics = get_aluno_analytics(aluno)

    return render_template('admin/alunos/perfil.html',
        aluno=aluno,
        presencas=presencas,
        analytics=analytics
    )


@admin_bp.route('/alunos/<int:id>/pdf')
@admin_required
def aluno_relatorio_pdf(id):
    """Exporta o relatório de progresso do atleta em PDF de alta qualidade."""
    aluno = db.get_or_404(Aluno, id)
    analytics = get_aluno_analytics(aluno)
    pdf_bytes = gerar_relatorio_pdf_aluno(aluno, analytics)

    nome_slug = re.sub(r'[^a-zA-Z0-9]+', '_', aluno.nome.lower()).strip('_')
    nome_arquivo = f"relatorio_{nome_slug}_{date.today().strftime('%Y-%m-%d')}.pdf"

    return Response(
        pdf_bytes,
        mimetype='application/pdf',
        headers={'Content-Disposition': f'attachment; filename="{nome_arquivo}"'}
    )


@admin_bp.route('/alunos/<int:id>/editar', methods=['GET', 'POST'])
@admin_required
def aluno_editar(id):
    aluno = db.get_or_404(Aluno, id)
    form = AlunoForm(aluno_id=id, obj=aluno)

    if request.method == 'GET' and aluno.usuario:
        form.email.data = aluno.usuario.email

    if form.validate_on_submit():
        aluno.nome = form.nome.data.strip()
        aluno.telefone = form.telefone.data.strip() if form.telefone.data else None
        aluno.data_nascimento = form.data_nascimento.data
        aluno.nivel = form.nivel.data
        aluno.categoria = form.categoria.data
        aluno.lado_dominante = form.lado_dominante.data
        aluno.objetivo = form.objetivo.data
        aluno.observacoes = form.observacoes.data.strip() if form.observacoes.data else None
        aluno.ativo = form.ativo.data

        if form.foto.data and form.foto.data.filename:
            remover_imagem(aluno.foto)
            aluno.foto = salvar_imagem(form.foto.data, 'aluno')

        if aluno.usuario:
            aluno.usuario.nome = aluno.nome
            aluno.usuario.email = form.email.data.lower().strip()
            aluno.usuario.ativo = aluno.ativo
            if form.senha.data:
                aluno.usuario.set_senha(form.senha.data)

        db.session.commit()
        flash(f'Dados do aluno "{aluno.nome}" atualizados com sucesso!', 'success')
        return redirect(url_for('admin.aluno_perfil', id=aluno.id))

    return render_template('admin/alunos/form.html', form=form, aluno=aluno)


@admin_bp.route('/alunos/<int:id>/excluir', methods=['POST'])
@admin_required
def aluno_excluir(id):
    aluno = db.get_or_404(Aluno, id)
    nome = aluno.nome
    remover_imagem(aluno.foto)

    usuario = aluno.usuario
    db.session.delete(aluno)
    if usuario:
        db.session.delete(usuario)
    db.session.commit()

    flash(f'Aluno "{nome}" e seu usuário de acesso foram removidos.', 'info')
    return redirect(url_for('admin.alunos_lista'))


@admin_bp.route('/alunos/<int:aluno_id>/metas/nova', methods=['GET', 'POST'])
@admin_required
def meta_nova(aluno_id):
    aluno = db.get_or_404(Aluno, aluno_id)
    if request.method == 'POST':
        descricao = request.form.get('descricao', '').strip()
        prazo_str = request.form.get('prazo', '').strip()
        if descricao:
            prazo = datetime.strptime(prazo_str, '%Y-%m-%d').date() if prazo_str else None
            meta = MetaAluno(aluno_id=aluno.id, descricao=descricao, prazo=prazo)
            db.session.add(meta)
            db.session.commit()
            flash('Meta adicionada com sucesso!', 'success')
        return redirect(url_for('admin.aluno_perfil', id=aluno.id))
    return render_template('admin/alunos/meta_form.html', aluno=aluno)


@admin_bp.route('/metas/<int:id>/concluir', methods=['POST'])
@admin_required
def meta_concluir(id):
    meta = db.get_or_404(MetaAluno, id)
    meta.concluida = not meta.concluida
    db.session.commit()
    status_str = 'concluída' if meta.concluida else 'reaberta'
    flash(f'Meta marcada como {status_str}!', 'success')
    return redirect(url_for('admin.aluno_perfil', id=meta.aluno_id))


# ── TROFÉUS DO ALUNO ──────────────────────────────────────────────────────
@admin_bp.route('/alunos/<int:aluno_id>/trofeus/novo', methods=['GET', 'POST'])
@admin_required
def trofeu_novo(aluno_id):
    aluno = db.get_or_404(Aluno, aluno_id)
    form = TrofeuForm()

    if form.validate_on_submit():
        trofeu = TrofeuAluno(
            aluno_id=aluno.id,
            ano=form.ano.data,
            colocacao=form.colocacao.data,
            categoria=form.categoria.data.strip(),
            titulo=form.titulo.data.strip(),
            torneio=form.torneio.data.strip() if form.torneio.data else None,
            destaque=form.destaque.data,
            ordem=form.ordem.data or 0,
        )
        db.session.add(trofeu)
        db.session.commit()
        flash(f'Troféu "{trofeu.titulo}" adicionado ao aluno {aluno.nome}!', 'success')
        return redirect(url_for('admin.aluno_perfil', id=aluno.id))

    return render_template('admin/alunos/trofeu_form.html', aluno=aluno, trofeu=None, form=form)


@admin_bp.route('/trofeus/<int:id>/editar', methods=['GET', 'POST'])
@admin_required
def trofeu_editar(id):
    trofeu = db.get_or_404(TrofeuAluno, id)
    form = TrofeuForm(obj=trofeu)

    if form.validate_on_submit():
        trofeu.ano = form.ano.data
        trofeu.colocacao = form.colocacao.data
        trofeu.categoria = form.categoria.data.strip()
        trofeu.titulo = form.titulo.data.strip()
        trofeu.torneio = form.torneio.data.strip() if form.torneio.data else None
        trofeu.destaque = form.destaque.data
        trofeu.ordem = form.ordem.data or 0
        db.session.commit()
        flash('Troféu atualizado com sucesso!', 'success')
        return redirect(url_for('admin.aluno_perfil', id=trofeu.aluno_id))

    return render_template('admin/alunos/trofeu_form.html', aluno=trofeu.aluno, trofeu=trofeu, form=form)


@admin_bp.route('/trofeus/<int:id>/excluir', methods=['POST'])
@admin_required
def trofeu_excluir(id):
    trofeu = db.get_or_404(TrofeuAluno, id)
    aluno_id = trofeu.aluno_id
    titulo = trofeu.titulo
    db.session.delete(trofeu)
    db.session.commit()
    flash(f'Troféu "{titulo}" removido.', 'info')
    return redirect(url_for('admin.aluno_perfil', id=aluno_id))


# ── EXERCÍCIOS ────────────────────────────────────────────────────────────
@admin_bp.route('/exercicios')
@admin_required
def exercicios_lista():
    q = request.args.get('q', '').strip()
    categoria = request.args.get('categoria', '').strip()
    nivel = request.args.get('nivel', '').strip()

    query = Exercicio.query
    if q:
        query = query.filter(
            db.or_(
                Exercicio.titulo.ilike(f'%{q}%'),
                Exercicio.descricao.ilike(f'%{q}%'),
                Exercicio.objetivo_tecnico.ilike(f'%{q}%')
            )
        )
    if categoria:
        query = query.filter(Exercicio.categoria == categoria)
    if nivel:
        query = query.filter(Exercicio.nivel == nivel)

    exercicios = query.order_by(Exercicio.titulo).all()
    return render_template('admin/exercicios/lista.html',
        exercicios=exercicios,
        total=len(exercicios),
        q=q,
        categoria=categoria,
        nivel=nivel,
        categorias=CATEGORIAS_EXERCICIO,
        niveis=NIVEIS_EXERCICIO
    )


@admin_bp.route('/exercicios/novo', methods=['GET', 'POST'])
@admin_required
def exercicio_novo():
    form = ExercicioForm()
    if form.validate_on_submit():
        imagem_nome = salvar_imagem(form.imagem.data, 'ex') if form.imagem.data else None

        exercicio = Exercicio(
            titulo=form.titulo.data.strip(),
            categoria=form.categoria.data,
            nivel=form.nivel.data,
            duracao_minutos=form.duracao_minutos.data,
            num_participantes=form.num_participantes.data.strip() if form.num_participantes.data else None,
            materiais=form.materiais.data.strip() if form.materiais.data else None,
            descricao=form.descricao.data.strip(),
            objetivo_tecnico=form.objetivo_tecnico.data.strip() if form.objetivo_tecnico.data else None,
            variacoes=form.variacoes.data.strip() if form.variacoes.data else None,
            erros_comuns=form.erros_comuns.data.strip() if form.erros_comuns.data else None,
            link_video=form.link_video.data.strip() if form.link_video.data else None,
            imagem=imagem_nome,
            ativo=form.ativo.data
        )
        db.session.add(exercicio)
        db.session.commit()

        flash(f'Exercício "{exercicio.titulo}" cadastrado com sucesso!', 'success')
        return redirect(url_for('admin.exercicio_detalhe', id=exercicio.id))

    return render_template('admin/exercicios/form.html', form=form, exercicio=None)


@admin_bp.route('/exercicios/<int:id>')
@admin_required
def exercicio_detalhe(id):
    exercicio = db.get_or_404(Exercicio, id)
    youtube_id = extrair_youtube_id(exercicio.link_video)
    return render_template('admin/exercicios/detalhe.html',
        exercicio=exercicio, youtube_id=youtube_id)


@admin_bp.route('/exercicios/<int:id>/editar', methods=['GET', 'POST'])
@admin_required
def exercicio_editar(id):
    exercicio = db.get_or_404(Exercicio, id)
    form = ExercicioForm(obj=exercicio)

    if form.validate_on_submit():
        exercicio.titulo = form.titulo.data.strip()
        exercicio.categoria = form.categoria.data
        exercicio.nivel = form.nivel.data
        exercicio.duracao_minutos = form.duracao_minutos.data
        exercicio.num_participantes = form.num_participantes.data.strip() if form.num_participantes.data else None
        exercicio.materiais = form.materiais.data.strip() if form.materiais.data else None
        exercicio.descricao = form.descricao.data.strip()
        exercicio.objetivo_tecnico = form.objetivo_tecnico.data.strip() if form.objetivo_tecnico.data else None
        exercicio.variacoes = form.variacoes.data.strip() if form.variacoes.data else None
        exercicio.erros_comuns = form.erros_comuns.data.strip() if form.erros_comuns.data else None
        exercicio.link_video = form.link_video.data.strip() if form.link_video.data else None
        exercicio.ativo = form.ativo.data

        if form.imagem.data and form.imagem.data.filename:
            remover_imagem(exercicio.imagem)
            exercicio.imagem = salvar_imagem(form.imagem.data, 'ex')

        db.session.commit()
        flash(f'Exercício "{exercicio.titulo}" atualizado com sucesso!', 'success')
        return redirect(url_for('admin.exercicio_detalhe', id=exercicio.id))

    return render_template('admin/exercicios/form.html', form=form, exercicio=exercicio)


@admin_bp.route('/exercicios/<int:id>/excluir', methods=['POST'])
@admin_required
def exercicio_excluir(id):
    exercicio = db.get_or_404(Exercicio, id)
    titulo = exercicio.titulo
    remover_imagem(exercicio.imagem)

    db.session.delete(exercicio)
    db.session.commit()
    flash(f'Exercício "{titulo}" excluído com sucesso.', 'info')
    return redirect(url_for('admin.exercicios_lista'))


# ── CRUD DE TURMAS ────────────────────────────────────────────────────────
@admin_bp.route('/turmas')
@admin_required
def turmas_lista():
    turmas = Turma.query.order_by(Turma.ativa.desc(), Turma.nome).all()
    return render_template('admin/turmas/lista.html', turmas=turmas)


@admin_bp.route('/turmas/nova', methods=['GET', 'POST'])
@admin_required
def turma_nova():
    form = TurmaForm()
    alunos_ativos = Aluno.query.filter_by(ativo=True).order_by(Aluno.nome).all()
    form.alunos_ids.choices = [(a.id, f"{a.nome} ({a.nivel.capitalize()})") for a in alunos_ativos]

    if form.validate_on_submit():
        dias_str = ','.join(sorted(form.dias_semana.data, key=int))
        turma = Turma(
            nome=form.nome.data.strip(),
            nivel=form.nivel.data,
            dias_semana=dias_str,
            horario_inicio=form.horario_inicio.data,
            horario_fim=form.horario_fim.data,
            local=form.local.data.strip(),
            vagas=form.vagas.data,
            ativa=form.ativa.data
        )
        db.session.add(turma)
        db.session.flush()

        # Vincula alunos selecionados
        for aluno_id in form.alunos_ids.data:
            ta = TurmaAluno(turma_id=turma.id, aluno_id=aluno_id, ativo=True)
            db.session.add(ta)

        db.session.commit()
        flash(f'Turma "{turma.nome}" criada com sucesso!', 'success')
        return redirect(url_for('admin.turmas_lista'))

    return render_template('admin/turmas/form.html', form=form, turma=None)


@admin_bp.route('/turmas/<int:id>')
@admin_bp.route('/turmas/<int:id>/editar', methods=['GET', 'POST'])
@admin_required
def turma_editar(id):
    turma = db.get_or_404(Turma, id)
    form = TurmaForm(obj=turma)
    alunos_ativos = Aluno.query.filter_by(ativo=True).order_by(Aluno.nome).all()
    form.alunos_ids.choices = [(a.id, f"{a.nome} ({a.nivel.capitalize()})") for a in alunos_ativos]

    if request.method == 'GET':
        form.dias_semana.data = turma.dias_semana_lista
        form.alunos_ids.data = [ta.aluno_id for ta in turma.alunos if ta.ativo]

    if form.validate_on_submit():
        turma.nome = form.nome.data.strip()
        turma.nivel = form.nivel.data
        turma.dias_semana = ','.join(sorted(form.dias_semana.data, key=int))
        turma.horario_inicio = form.horario_inicio.data
        turma.horario_fim = form.horario_fim.data
        turma.local = form.local.data.strip()
        turma.vagas = form.vagas.data
        turma.ativa = form.ativa.data

        # Sincroniza vínculos de alunos
        alunos_selecionados = set(form.alunos_ids.data or [])
        vinculos_existentes = {ta.aluno_id: ta for ta in turma.alunos}

        for aluno_id in alunos_selecionados:
            if aluno_id in vinculos_existentes:
                vinculos_existentes[aluno_id].ativo = True
            else:
                db.session.add(TurmaAluno(turma_id=turma.id, aluno_id=aluno_id, ativo=True))

        for aluno_id, ta in vinculos_existentes.items():
            if aluno_id not in alunos_selecionados:
                ta.ativo = False

        db.session.commit()
        flash(f'Turma "{turma.nome}" atualizada com sucesso!', 'success')
        return redirect(url_for('admin.turmas_lista'))

    return render_template('admin/turmas/form.html', form=form, turma=turma)


@admin_bp.route('/turmas/<int:id>/excluir', methods=['POST'])
@admin_required
def turma_excluir(id):
    turma = db.get_or_404(Turma, id)
    nome = turma.nome
    db.session.delete(turma)
    db.session.commit()
    flash(f'Turma "{nome}" excluída com sucesso.', 'info')
    return redirect(url_for('admin.turmas_lista'))


# ── AGENDA, CALENDÁRIO E AULAS ─────────────────────────────────────────────
@admin_bp.route('/aulas')
@admin_required
def aulas_lista():
    turma_id = request.args.get('turma_id', type=int)
    view = request.args.get('view', 'calendario')  # 'calendario' ou 'lista'
    status = request.args.get('status', '').strip()

    query = Aula.query.join(Turma)
    if turma_id:
        query = query.filter(Aula.turma_id == turma_id)
    if status:
        query = query.filter(Aula.status == status)

    aulas = query.order_by(Aula.data_hora.desc()).all()
    turmas = Turma.query.filter_by(ativa=True).order_by(Turma.nome).all()

    cancelar_form = CancelarAulaForm()
    remarcar_form = RemarcarAulaForm()

    return render_template('admin/aulas/lista.html',
        aulas=aulas,
        turmas=turmas,
        turma_id=turma_id,
        view=view,
        status=status,
        cancelar_form=cancelar_form,
        remarcar_form=remarcar_form
    )


@admin_bp.route('/aulas/api/eventos')
@admin_required
def aulas_api_eventos():
    """Retorna eventos para o calendário FullCalendar."""
    turma_id = request.args.get('turma_id', type=int)
    query = Aula.query.join(Turma)
    if turma_id:
        query = query.filter(Aula.turma_id == turma_id)

    eventos = []
    for aula in query.all():
        fim = aula.data_hora + timedelta(minutes=aula.duracao_minutos)
        
        # Cor de acordo com status
        if aula.status == 'cancelada':
            cor = '#dc3545'
            prefixo = '[CANCELADA] '
        elif aula.status == 'remarcada':
            cor = '#ffc107'
            prefixo = '[REMARCADA] '
        elif aula.status == 'realizada':
            cor = '#198754'
            prefixo = '✓ '
        else:
            cor = '#0077b6'
            prefixo = ''

        eventos.append({
            'id': aula.id,
            'title': f"{prefixo}{aula.turma.nome} ({aula.data_hora.strftime('%H:%M')})",
            'start': aula.data_hora.isoformat(),
            'end': fim.isoformat(),
            'backgroundColor': cor,
            'borderColor': cor,
            'url': url_for('admin.aula_detalhe', id=aula.id)
        })

    return jsonify(eventos)


@admin_bp.route('/aulas/nova', methods=['GET', 'POST'])
@admin_required
def aula_nova():
    """Criação de aula avulsa."""
    form = AulaForm()
    turmas_ativas = Turma.query.filter_by(ativa=True).order_by(Turma.nome).all()
    form.turma_id.choices = [(t.id, f"{t.nome} ({t.dias_semana_texto} {t.horario_inicio.strftime('%H:%M')})") for t in turmas_ativas]

    if form.validate_on_submit():
        aula = Aula(
            turma_id=form.turma_id.data,
            data_hora=form.data_hora.data,
            duracao_minutos=form.duracao_minutos.data,
            objetivo=form.objetivo.data.strip() if form.objetivo.data else None,
            observacoes=form.observacoes.data.strip() if form.observacoes.data else None,
            status='agendada'
        )
        db.session.add(aula)
        db.session.commit()

        flash(f'Aula agendada com sucesso para {aula.data_hora.strftime("%d/%m/%Y às %H:%M")}!', 'success')
        return redirect(url_for('admin.aula_detalhe', id=aula.id))

    return render_template('admin/aulas/form.html', form=form, aula=None)


@admin_bp.route('/aulas/recorrentes', methods=['GET', 'POST'])
@admin_required
def aulas_recorrentes():
    """Gera grade de aulas recorrentes para uma turma."""
    form = GerarAulasRecorrentesForm()
    turmas_ativas = Turma.query.filter_by(ativa=True).order_by(Turma.nome).all()
    form.turma_id.choices = [(t.id, f"{t.nome} - {t.dias_semana_texto} ({t.horario_inicio.strftime('%H:%M')})") for t in turmas_ativas]

    if form.validate_on_submit():
        turma = db.session.get(Turma, form.turma_id.data)
        dias_permitidos = set(turma.dias_semana_lista)

        dia_atual = form.data_inicio.data
        data_fim = form.data_fim.data
        aulas_criadas = 0

        while dia_atual <= data_fim:
            # weekday: 0 = Segunda, 6 = Domingo
            if dia_atual.weekday() in dias_permitidos:
                dt_hora = datetime.combine(dia_atual, turma.horario_inicio)
                # Verifica se já não existe aula para esta turma no mesmo horário exato
                existente = Aula.query.filter_by(turma_id=turma.id, data_hora=dt_hora).first()
                if not existente:
                    aula = Aula(
                        turma_id=turma.id,
                        data_hora=dt_hora,
                        duracao_minutos=form.duracao_minutos.data,
                        objetivo=form.objetivo_padrao.data.strip() if form.objetivo_padrao.data else None,
                        status='agendada'
                    )
                    db.session.add(aula)
                    aulas_criadas += 1
            dia_atual += timedelta(days=1)

        db.session.commit()
        flash(f'{aulas_criadas} aulas recorrentes geradas com sucesso para a turma "{turma.nome}"!', 'success')
        return redirect(url_for('admin.aulas_lista', turma_id=turma.id))

    return render_template('admin/aulas/recorrentes.html', form=form)


@admin_bp.route('/aulas/<int:id>/cancelar', methods=['POST'])
@admin_required
def aula_cancelar(id):
    aula = db.get_or_404(Aula, id)
    form = CancelarAulaForm()
    if form.validate_on_submit():
        aula.status = 'cancelada'
        aula.aviso_cancelamento = form.aviso_cancelamento.data.strip()
        db.session.commit()
        flash(f'Aula de {aula.data_hora.strftime("%d/%m/%Y")} cancelada com aviso aos alunos.', 'warning')
    else:
        flash('Erro ao cancelar a aula. Forneça o motivo.', 'danger')
    return redirect(url_for('admin.aula_detalhe', id=aula.id))


@admin_bp.route('/aulas/<int:id>/remarcar', methods=['POST'])
@admin_required
def aula_remarcar(id):
    aula = db.get_or_404(Aula, id)
    form = RemarcarAulaForm()
    if form.validate_on_submit():
        nova_dt = form.nova_data_hora.data
        motivo = form.motivo.data.strip() if form.motivo.data else 'Remarcada pelo professor'

        # Marca a atual como remarcada
        aula.status = 'remarcada'
        aula.aviso_cancelamento = f"Aula remarcada para {nova_dt.strftime('%d/%m/%Y %H:%M')}. Motivo: {motivo}"

        # Cria a nova aula ligada à original
        nova_aula = Aula(
            turma_id=aula.turma_id,
            data_hora=nova_dt,
            duracao_minutos=aula.duracao_minutos,
            objetivo=aula.objetivo,
            observacoes=aula.observacoes,
            status='agendada',
            aula_original_id=aula.id
        )
        db.session.add(nova_aula)
        db.session.flush()

        # Duplica os exercícios da aula original para a nova
        for ex in aula.exercicios:
            novo_ex = AulaExercicio(
                aula_id=nova_aula.id,
                exercicio_id=ex.exercicio_id,
                ordem=ex.ordem,
                duracao_minutos=ex.duracao_minutos,
                observacao=ex.observacao
            )
            db.session.add(novo_ex)

        db.session.commit()
        flash(f'Aula remarcada com sucesso para {nova_dt.strftime("%d/%m/%Y às %H:%M")}!', 'success')
        return redirect(url_for('admin.aula_detalhe', id=nova_aula.id))

    flash('Erro ao remarcar aula. Verifique a nova data.', 'danger')
    return redirect(url_for('admin.aula_detalhe', id=aula.id))


# ── PLANO DE AULA & MODO QUADRA ────────────────────────────────────────────
@admin_bp.route('/aulas/<int:id>', methods=['GET', 'POST'])
@admin_required
def aula_detalhe(id):
    aula = db.get_or_404(Aula, id)
    
    # Form para adicionar exercício
    form_ex = AulaExercicioForm()
    exercicios_ativos = Exercicio.query.filter_by(ativo=True).order_by(Exercicio.categoria, Exercicio.titulo).all()
    form_ex.exercicio_id.choices = [(e.id, f"[{e.categoria_nome}] {e.titulo} ({e.duracao_minutos}m)") for e in exercicios_ativos]

    cancelar_form = CancelarAulaForm()
    remarcar_form = RemarcarAulaForm()

    # Aulas anteriores da mesma turma para duplicação de plano
    outras_aulas = Aula.query.filter(
        Aula.id != aula.id,
        Aula.turma_id == aula.turma_id,
        Aula.exercicios.any()
    ).order_by(Aula.data_hora.desc()).limit(15).all()

    return render_template('admin/aulas/detalhe.html',
        aula=aula,
        form_ex=form_ex,
        cancelar_form=cancelar_form,
        remarcar_form=remarcar_form,
        outras_aulas=outras_aulas
    )


@admin_bp.route('/aulas/<int:id>/plano/adicionar', methods=['POST'])
@admin_required
def aula_plano_adicionar_exercicio(id):
    aula = db.get_or_404(Aula, id)
    form = AulaExercicioForm()
    exercicios_ativos = Exercicio.query.filter_by(ativo=True).order_by(Exercicio.titulo).all()
    form.exercicio_id.choices = [(e.id, e.titulo) for e in exercicios_ativos]

    if form.validate_on_submit():
        proxima_ordem = len(aula.exercicios) + 1
        ae = AulaExercicio(
            aula_id=aula.id,
            exercicio_id=form.exercicio_id.data,
            ordem=proxima_ordem,
            duracao_minutos=form.duracao_minutos.data,
            observacao=form.observacao.data.strip() if form.observacao.data else None
        )
        db.session.add(ae)
        db.session.commit()
        flash('Exercício adicionado ao plano de aula!', 'success')
    else:
        flash('Erro ao adicionar exercício ao plano.', 'danger')

    return redirect(url_for('admin.aula_detalhe', id=aula.id))


@admin_bp.route('/aulas/<int:id>/plano/remover/<int:item_id>', methods=['POST'])
@admin_required
def aula_plano_remover_exercicio(id, item_id):
    ae = db.get_or_404(AulaExercicio, item_id)
    if ae.aula_id != id:
        abort(400)
    db.session.delete(ae)
    
    # Reorganiza ordens
    outros = AulaExercicio.query.filter_by(aula_id=id).order_by(AulaExercicio.ordem).all()
    for idx, item in enumerate(outros, start=1):
        item.ordem = idx
        
    db.session.commit()
    flash('Exercício removido do plano de aula.', 'info')
    return redirect(url_for('admin.aula_detalhe', id=id))


@admin_bp.route('/aulas/<int:id>/plano/duplicar', methods=['POST'])
@admin_required
def aula_plano_duplicar(id):
    aula_destino = db.get_or_404(Aula, id)
    origem_id = request.form.get('aula_origem_id', type=int)
    aula_origem = db.get_or_404(Aula, origem_id)

    if not aula_destino.objetivo and aula_origem.objetivo:
        aula_destino.objetivo = aula_origem.objetivo

    # Limpa exercícios atuais ou apenda
    ordem_atual = len(aula_destino.exercicios)
    for ex in aula_origem.exercicios:
        ordem_atual += 1
        novo = AulaExercicio(
            aula_id=aula_destino.id,
            exercicio_id=ex.exercicio_id,
            ordem=ordem_atual,
            duracao_minutos=ex.duracao_minutos,
            observacao=ex.observacao
        )
        db.session.add(novo)

    db.session.commit()
    flash(f'Plano de aula duplicado com sucesso da aula de {aula_origem.data_hora.strftime("%d/%m/%Y")}!', 'success')
    return redirect(url_for('admin.aula_detalhe', id=aula_destino.id))


@admin_bp.route('/aulas/<int:id>/plano/reordenar', methods=['POST'])
@admin_required
def aula_plano_reordenar(id):
    """Reordena exercícios via POST ajax ou form (lista de IDs)."""
    dados = request.get_json(silent=True) or request.form
    ordem_ids = dados.get('ordem_ids')
    if isinstance(ordem_ids, str):
        ordem_ids = [int(x) for x in ordem_ids.split(',') if x.strip()]

    if ordem_ids:
        for idx, item_id in enumerate(ordem_ids, start=1):
            ae = db.session.get(AulaExercicio, int(item_id))
            if ae and ae.aula_id == id:
                ae.ordem = idx
        db.session.commit()
        return jsonify({'status': 'ok', 'message': 'Ordem atualizada com sucesso!'})

    return jsonify({'status': 'error', 'message': 'Dados inválidos'}), 400


@admin_bp.route('/aulas/<int:id>/modo-quadra')
@admin_required
def aula_modo_quadra(id):
    """Visualização limpa, de alta legibilidade e pensada para smartphone na quadra."""
    aula = db.get_or_404(Aula, id)
    alunos_turma = [ta.aluno for ta in aula.turma.alunos if ta.ativo]
    return render_template('admin/aulas/modo_quadra.html',
        aula=aula, alunos_turma=alunos_turma)


# ── CHAMADA RÁPIDA DE PRESENÇA ─────────────────────────────────────────
@admin_bp.route('/aulas/<int:id>/chamada', methods=['GET', 'POST'])
@admin_required
def aula_chamada(id):
    """Chamada rápida por aula com botões para presente, falta, falta justificada e reposição."""
    aula = db.get_or_404(Aula, id)
    
    # Alunos ativos matriculados na turma desta aula
    alunos_turma = [ta.aluno for ta in aula.turma.alunos if ta.ativo]
    
    # Presenças já registradas nesta aula
    presencas_existentes = {p.aluno_id: p for p in aula.presencas}
    
    # Todos os alunos para a chamada: matriculados + alunos que já tenham registro na aula (ex: reposição)
    alunos_ids = set([a.id for a in alunos_turma] + list(presencas_existentes.keys()))
    alunos_lista = Aluno.query.filter(Aluno.id.in_(alunos_ids)).order_by(Aluno.nome).all() if alunos_ids else []
    
    # Alunos elegíveis para reposição avulsa nesta aula (outros alunos ativos não listados)
    if alunos_ids:
        outros_alunos = Aluno.query.filter(Aluno.ativo == True, ~Aluno.id.in_(alunos_ids)).order_by(Aluno.nome).all()
    else:
        outros_alunos = Aluno.query.filter_by(ativo=True).order_by(Aluno.nome).all()

    if request.method == 'POST':
        # Caso o professor esteja adicionando um aluno para reposição via formulário rápido
        reposicao_aluno_id = request.form.get('reposicao_aluno_id', type=int)
        if reposicao_aluno_id:
            aluno_rep = db.session.get(Aluno, reposicao_aluno_id)
            if aluno_rep:
                p_rep = Presenca.query.filter_by(aula_id=aula.id, aluno_id=aluno_rep.id).first()
                if not p_rep:
                    p_rep = Presenca(
                        aula_id=aula.id,
                        aluno_id=aluno_rep.id,
                        status='reposicao',
                        justificativa='Reposição adicionada na chamada',
                        registrado_em=datetime.utcnow()
                    )
                    db.session.add(p_rep)
                    db.session.commit()
                    flash(f'Aluno {aluno_rep.nome} adicionado para reposição nesta aula.', 'info')
                    return redirect(url_for('admin.aula_chamada', id=aula.id))

        total_salvo = 0
        submitted_aluno_ids = request.form.getlist('aluno_ids', type=int)
        for al_id in submitted_aluno_ids:
            status = request.form.get(f'status_{al_id}', 'presente')
            justificativa = request.form.get(f'justificativa_{al_id}', '').strip()
            
            p = Presenca.query.filter_by(aula_id=aula.id, aluno_id=al_id).first()
            if p:
                p.status = status
                p.justificativa = justificativa or None
                p.registrado_em = datetime.utcnow()
            else:
                p = Presenca(
                    aula_id=aula.id,
                    aluno_id=al_id,
                    status=status,
                    justificativa=justificativa or None,
                    registrado_em=datetime.utcnow()
                )
                db.session.add(p)
            total_salvo += 1

        # Ao salvar a chamada, se a aula ainda constava como 'agendada', passa a 'realizada'
        if aula.status == 'agendada':
            aula.status = 'realizada'
            
        db.session.commit()
        flash(f'Chamada concluída com sucesso! {total_salvo} presenças registradas.', 'success')
        
        origem = request.form.get('origem')
        if origem == 'modo_quadra':
            return redirect(url_for('admin.aula_modo_quadra', id=aula.id))
        return redirect(url_for('admin.aula_detalhe', id=aula.id))

    return render_template(
        'admin/presencas/chamada.html',
        aula=aula,
        alunos=alunos_lista,
        presencas_map=presencas_existentes,
        outros_alunos=outros_alunos
    )


# ── RELATÓRIO DE FREQUÊNCIA ──────────────────────────────────────────────
@admin_bp.route('/presencas')
@admin_required
def presencas():
    """Relatório completo de frequência por aluno, por turma e histórico detalhado."""
    turma_id = request.args.get('turma_id', type=int)
    aluno_id = request.args.get('aluno_id', type=int)
    periodo = request.args.get('periodo', 'todos')  # '30_dias', 'mes_atual', 'todos'
    
    turmas = Turma.query.filter_by(ativa=True).order_by(Turma.nome).all()
    alunos = Aluno.query.filter_by(ativo=True).order_by(Aluno.nome).all()
    
    hoje = date.today()
    
    # Query base para o histórico
    query = Presenca.query.join(Aula).join(Aluno)
    if periodo == '30_dias':
        data_limite = hoje - timedelta(days=30)
        query = query.filter(Aula.data_hora >= datetime.combine(data_limite, time.min))
    elif periodo == 'mes_atual':
        data_limite = hoje.replace(day=1)
        query = query.filter(Aula.data_hora >= datetime.combine(data_limite, time.min))
        
    if turma_id:
        query = query.filter(Aula.turma_id == turma_id)
    if aluno_id:
        query = query.filter(Presenca.aluno_id == aluno_id)
        
    historico = query.order_by(Aula.data_hora.desc()).limit(150).all()
    
    # 1. Relatório por Aluno
    relatorio_alunos = []
    for al in alunos:
        q_al = Presenca.query.filter_by(aluno_id=al.id).join(Aula)
        if periodo == '30_dias':
            q_al = q_al.filter(Aula.data_hora >= datetime.combine(hoje - timedelta(days=30), time.min))
        elif periodo == 'mes_atual':
            q_al = q_al.filter(Aula.data_hora >= datetime.combine(hoje.replace(day=1), time.min))
        if turma_id:
            q_al = q_al.filter(Aula.turma_id == turma_id)
            
        registros_al = q_al.all()
        total_al = len(registros_al)
        pres_al = sum(1 for r in registros_al if r.status == 'presente')
        faltas_al = sum(1 for r in registros_al if r.status == 'falta')
        just_al = sum(1 for r in registros_al if r.status == 'falta_justificada')
        rep_al = sum(1 for r in registros_al if r.status == 'reposicao')
        taxa_al = round(((pres_al + rep_al) / total_al * 100), 1) if total_al > 0 else 0
        
        relatorio_alunos.append({
            'aluno': al,
            'total': total_al,
            'presentes': pres_al,
            'faltas': faltas_al,
            'justificadas': just_al,
            'reposicoes': rep_al,
            'taxa': taxa_al
        })
    
    # Ordenar por mais aulas e maior frequência
    relatorio_alunos.sort(key=lambda x: (x['total'] > 0, x['taxa'], x['aluno'].nome), reverse=True)

    # 2. Relatório por Turma
    relatorio_turmas = []
    for t in turmas:
        q_t = Presenca.query.join(Aula).filter(Aula.turma_id == t.id)
        if periodo == '30_dias':
            q_t = q_t.filter(Aula.data_hora >= datetime.combine(hoje - timedelta(days=30), time.min))
        elif periodo == 'mes_atual':
            q_t = q_t.filter(Aula.data_hora >= datetime.combine(hoje.replace(day=1), time.min))
            
        registros_t = q_t.all()
        total_t = len(registros_t)
        pres_t = sum(1 for r in registros_t if r.status in ('presente', 'reposicao'))
        faltas_t = sum(1 for r in registros_t if r.status == 'falta')
        just_t = sum(1 for r in registros_t if r.status == 'falta_justificada')
        taxa_t = round((pres_t / total_t * 100), 1) if total_t > 0 else 0
        
        aulas_realizadas = Aula.query.filter_by(turma_id=t.id, status='realizada').count()
        
        relatorio_turmas.append({
            'turma': t,
            'aulas_realizadas': aulas_realizadas,
            'total_registros': total_t,
            'presentes': pres_t,
            'faltas': faltas_t,
            'justificadas': just_t,
            'taxa': taxa_t
        })

    # Métricas gerais rápidas
    total_registros_geral = len(historico)
    total_presentes_geral = sum(1 for h in historico if h.status in ('presente', 'reposicao'))
    taxa_geral = round((total_presentes_geral / total_registros_geral * 100), 1) if total_registros_geral > 0 else 0

    return render_template(
        'admin/presencas/relatorio.html',
        turmas=turmas,
        alunos=alunos,
        turma_id=turma_id,
        aluno_id=aluno_id,
        periodo=periodo,
        relatorio_alunos=relatorio_alunos,
        relatorio_turmas=relatorio_turmas,
        historico=historico,
        total_registros_geral=total_registros_geral,
        taxa_geral=taxa_geral
    )


# ── AVALIAÇÃO E PROGRESSO ───────────────────────────────────────────────
@admin_bp.route('/avaliacoes')
@admin_required
def avaliacoes_lista():
    """Listagem de todas as avaliações periódicas realizadas."""
    busca = request.args.get('busca', '').strip()
    aluno_id = request.args.get('aluno_id', type=int)
    
    query = Avaliacao.query.join(Aluno)
    if busca:
        query = query.filter(Aluno.nome.ilike(f'%{busca}%'))
    if aluno_id:
        query = query.filter(Avaliacao.aluno_id == aluno_id)
        
    avaliacoes = query.order_by(Avaliacao.data.desc(), Avaliacao.id.desc()).all()
    alunos = Aluno.query.filter_by(ativo=True).order_by(Aluno.nome).all()
    
    return render_template(
        'admin/avaliacoes/lista.html',
        avaliacoes=avaliacoes,
        alunos=alunos,
        busca=busca,
        aluno_id=aluno_id
    )


@admin_bp.route('/avaliacoes/nova', methods=['GET', 'POST'])
@admin_required
def avaliacao_nova():
    """Formulário de avaliação periódica com 11 critérios (notas 1 a 10), pontos fortes, a melhorar, metas e vídeo."""
    form = AvaliacaoForm()
    alunos = Aluno.query.filter_by(ativo=True).order_by(Aluno.nome).all()
    form.aluno_id.choices = [
        (a.id, f"{a.nome} ({a.categoria_curta} · {a.nivel.capitalize() if a.nivel else 'Iniciante'})")
        for a in alunos
    ]

    aluno_pre_selecionado = request.args.get('aluno_id', type=int)
    if request.method == 'GET':
        form.data.data = date.today()
        if aluno_pre_selecionado:
            form.aluno_id.data = aluno_pre_selecionado
            aluno_pre = next((a for a in alunos if a.id == aluno_pre_selecionado), None)
            if aluno_pre:
                form.categoria.data = aluno_pre.categoria_efetiva

    if form.validate_on_submit():
        avaliacao = Avaliacao(
            aluno_id=form.aluno_id.data,
            data=form.data.data,
            categoria=form.categoria.data,
            pontos_fortes=form.pontos_fortes.data.strip() if form.pontos_fortes.data else None,
            pontos_melhorar=form.pontos_melhorar.data.strip() if form.pontos_melhorar.data else None,
            metas_proximo_ciclo=form.metas_proximo_ciclo.data.strip() if form.metas_proximo_ciclo.data else None,
            comentarios=form.comentarios.data.strip() if form.comentarios.data else None,
            link_video_analise=form.link_video_analise.data.strip() if form.link_video_analise.data else None
        )
        db.session.add(avaliacao)
        db.session.flush()  # Gera o id da avaliacao

        # Salva as notas dos 11 critérios
        for crit_key, _ in CRITERIOS_AVALIACAO:
            campo = getattr(form, f'nota_{crit_key}', None)
            nota_val = float(campo.data) if campo and campo.data is not None else 5.0
            nota_obj = AvaliacaoNota(
                avaliacao_id=avaliacao.id,
                criterio=crit_key,
                nota=nota_val
            )
            db.session.add(nota_obj)

        aluno = db.session.get(Aluno, avaliacao.aluno_id)
        sincronizar_categoria_aluno(aluno)
        db.session.commit()
        flash(
            f'Avaliação periódica de {aluno.nome} salva com sucesso! '
            f'Média na categoria: {avaliacao.media:.1f} · Índice Técnico: {avaliacao.indice_tecnico:.1f}/100.',
            'success'
        )
        return redirect(url_for('admin.avaliacao_detalhe', id=avaliacao.id))

    return render_template(
        'admin/avaliacoes/form.html',
        form=form,
        titulo='Nova Avaliação Periódica',
        criterios=CRITERIOS_AVALIACAO,
        categorias_aluno_json=json.dumps({a.id: a.categoria_efetiva for a in alunos}),
        pesos_categoria_json=json.dumps(CATEGORIA_PESOS),
    )


@admin_bp.route('/avaliacoes/<int:id>')
@admin_required
def avaliacao_detalhe(id):
    """Visualização da avaliação com notas dos 11 critérios, comparativo com ciclo anterior e link de vídeo."""
    avaliacao = db.get_or_404(Avaliacao, id)
    youtube_id = extrair_youtube_id(avaliacao.link_video_analise)
    
    # Busca avaliação anterior do mesmo aluno para comparar evolução numérica
    avaliacao_anterior = Avaliacao.query.filter(
        Avaliacao.aluno_id == avaliacao.aluno_id,
        Avaliacao.id != avaliacao.id,
        Avaliacao.data <= avaliacao.data
    ).order_by(Avaliacao.data.desc(), Avaliacao.id.desc()).first()
    
    comparativo = {}
    for crit_key, crit_label in CRITERIOS_AVALIACAO:
        nota_atual = avaliacao.get_nota(crit_key)
        nota_ant = avaliacao_anterior.get_nota(crit_key) if avaliacao_anterior else None
        diff = round(nota_atual - nota_ant, 1) if (nota_atual is not None and nota_ant is not None) else None

        indice_atual_crit = avaliacao.get_indice(crit_key)
        indice_ant_crit = avaliacao_anterior.get_indice(crit_key) if avaliacao_anterior else None
        diff_indice_crit = (
            round(indice_atual_crit - indice_ant_crit, 1)
            if (indice_atual_crit is not None and indice_ant_crit is not None) else None
        )

        comparativo[crit_key] = {
            'label': crit_label,
            'atual': nota_atual,
            'anterior': nota_ant,
            'diff': diff,
            'indice_atual': indice_atual_crit,
            'indice_anterior': indice_ant_crit,
            'diff_indice': diff_indice_crit,
        }

    mudou_categoria = bool(
        avaliacao_anterior and
        avaliacao_anterior.categoria_curta != avaliacao.categoria_curta
    )
    diff_media = round(avaliacao.media - avaliacao_anterior.media, 1) if avaliacao_anterior else None
    diff_indice = (
        round(avaliacao.indice_tecnico - avaliacao_anterior.indice_tecnico, 1)
        if avaliacao_anterior else None
    )

    return render_template(
        'admin/avaliacoes/detalhe.html',
        avaliacao=avaliacao,
        youtube_id=youtube_id,
        avaliacao_anterior=avaliacao_anterior,
        comparativo=comparativo,
        diff_media=diff_media,
        diff_indice=diff_indice,
        mudou_categoria=mudou_categoria,
        criterios=CRITERIOS_AVALIACAO
    )


@admin_bp.route('/avaliacoes/<int:id>/editar', methods=['GET', 'POST'])
@admin_required
def avaliacao_editar(id):
    """Editar avaliação periódica existente."""
    avaliacao = db.get_or_404(Avaliacao, id)
    form = AvaliacaoForm(obj=avaliacao)
    alunos = Aluno.query.order_by(Aluno.nome).all()
    form.aluno_id.choices = [
        (a.id, f"{a.nome} ({a.categoria_curta} · {a.nivel.capitalize() if a.nivel else 'Iniciante'})")
        for a in alunos
    ]

    if request.method == 'GET':
        if not avaliacao.categoria:
            form.categoria.data = 'D'
        for n in avaliacao.notas:
            campo = getattr(form, f'nota_{n.criterio}', None)
            if campo:
                campo.data = n.nota

    if form.validate_on_submit():
        avaliacao.aluno_id = form.aluno_id.data
        avaliacao.data = form.data.data
        avaliacao.categoria = form.categoria.data
        avaliacao.pontos_fortes = form.pontos_fortes.data.strip() if form.pontos_fortes.data else None
        avaliacao.pontos_melhorar = form.pontos_melhorar.data.strip() if form.pontos_melhorar.data else None
        avaliacao.metas_proximo_ciclo = form.metas_proximo_ciclo.data.strip() if form.metas_proximo_ciclo.data else None
        avaliacao.comentarios = form.comentarios.data.strip() if form.comentarios.data else None
        avaliacao.link_video_analise = form.link_video_analise.data.strip() if form.link_video_analise.data else None

        # Atualizar cada nota
        for crit_key, _ in CRITERIOS_AVALIACAO:
            campo = getattr(form, f'nota_{crit_key}', None)
            nota_val = float(campo.data) if campo and campo.data is not None else 5.0

            nota_obj = AvaliacaoNota.query.filter_by(avaliacao_id=avaliacao.id, criterio=crit_key).first()
            if nota_obj:
                nota_obj.nota = nota_val
            else:
                nota_obj = AvaliacaoNota(
                    avaliacao_id=avaliacao.id,
                    criterio=crit_key,
                    nota=nota_val
                )
                db.session.add(nota_obj)

        aluno = db.session.get(Aluno, avaliacao.aluno_id)
        sincronizar_categoria_aluno(aluno)
        db.session.commit()
        flash('Avaliação periódica atualizada com sucesso!', 'success')
        return redirect(url_for('admin.avaliacao_detalhe', id=avaliacao.id))

    return render_template(
        'admin/avaliacoes/form.html',
        form=form,
        avaliacao=avaliacao,
        titulo=f'Editar Avaliação — {avaliacao.aluno.nome}',
        criterios=CRITERIOS_AVALIACAO,
        categorias_aluno_json=json.dumps({a.id: a.categoria_efetiva for a in alunos}),
        pesos_categoria_json=json.dumps(CATEGORIA_PESOS),
    )


@admin_bp.route('/avaliacoes/<int:id>/excluir', methods=['POST'])
@admin_required
def avaliacao_excluir(id):
    """Excluir avaliação e suas notas em cascata."""
    avaliacao = db.get_or_404(Avaliacao, id)
    aluno = avaliacao.aluno
    nome_aluno = aluno.nome
    data_fmt = avaliacao.data.strftime('%d/%m/%Y')
    db.session.delete(avaliacao)
    db.session.flush()
    sincronizar_categoria_aluno(aluno)
    db.session.commit()
    flash(f'Avaliação de {nome_aluno} ({data_fmt}) excluída com sucesso.', 'info')
    return redirect(url_for('admin.avaliacoes_lista'))


# ── SITE PÚBLICO: CONFIGURAÇÕES E CONTEÚDOS ─────────────────────────────
@admin_bp.route('/configuracoes', methods=['GET', 'POST'])
@admin_bp.route('/site/configuracoes', methods=['GET', 'POST'])
@admin_required
def configuracoes():
    from app.blueprints.public.routes import calcular_idade_professor
    form = ConfiguracaoSiteForm()
    
    chaves = [
        'nome_professor', 'data_nascimento_professor', 'formacao_professor',
        'idade_professor', 'subtitulo_hero', 'sobre_texto',
        'whatsapp', 'whatsapp_mensagem', 'instagram', 'nome_quadra',
        'endereco', 'cidade', 'link_google_maps'
    ]
    
    if request.method == 'GET':
        for chave in chaves:
            campo = getattr(form, chave, None)
            if campo:
                val = ConfiguracaoSite.get(chave, '')
                if chave == 'data_nascimento_professor':
                    if not val:
                        val = '2004-03-10'
                    try:
                        campo.data = datetime.strptime(val, '%Y-%m-%d').date()
                    except (ValueError, TypeError):
                        campo.data = date(2004, 3, 10)
                else:
                    campo.data = val
                
    if form.validate_on_submit():
        for chave in chaves:
            campo = getattr(form, chave, None)
            if campo:
                if chave == 'data_nascimento_professor':
                    val_str = campo.data.strftime('%Y-%m-%d') if campo.data else '2004-03-10'
                    ConfiguracaoSite.set(chave, val_str)
                else:
                    ConfiguracaoSite.set(chave, campo.data.strip() if campo.data else '')
                
        if form.foto_professor.data and form.foto_professor.data.filename:
            foto_salva = salvar_imagem(form.foto_professor.data, 'prof')
            if foto_salva:
                ConfiguracaoSite.set('foto_professor', foto_salva)
                
        flash('Configurações do site atualizadas com sucesso!', 'success')
        return redirect(url_for('admin.configuracoes'))
        
    foto_atual = ConfiguracaoSite.get('foto_professor')
    data_nasc_salva = ConfiguracaoSite.get('data_nascimento_professor', '2004-03-10')
    idade_atual = calcular_idade_professor(data_nasc_salva)
    return render_template('admin/site/configuracoes.html', form=form, foto_atual=foto_atual, idade_atual=idade_atual)


# ── CONQUISTAS ──────────────────────────────────────────────────────────
@admin_bp.route('/site/conquistas')
@admin_required
def conquistas_lista():
    conquistas = Conquista.query.order_by(Conquista.ano.desc(), Conquista.ordem.asc(), Conquista.id.asc()).all()
    return render_template('admin/site/conquistas_lista.html', conquistas=conquistas)


@admin_bp.route('/site/conquistas/nova', methods=['GET', 'POST'])
@admin_required
def conquista_nova():
    form = ConquistaForm()
    if form.validate_on_submit():
        conquista = Conquista(
            ano=form.ano.data,
            colocacao=form.colocacao.data,
            categoria=form.categoria.data.strip(),
            titulo=form.titulo.data.strip(),
            torneio=form.torneio.data.strip() if form.torneio.data else 'Circuito AIBT',
            destaque=form.destaque.data,
            ordem=form.ordem.data or 0
        )
        db.session.add(conquista)
        db.session.commit()
        flash(f'Conquista "{conquista.titulo}" adicionada com sucesso!', 'success')
        return redirect(url_for('admin.conquistas_lista'))
        
    return render_template('admin/site/conquista_form.html', form=form, conquista=None)


@admin_bp.route('/site/conquistas/<int:id>/editar', methods=['GET', 'POST'])
@admin_required
def conquista_editar(id):
    conquista = db.get_or_404(Conquista, id)
    form = ConquistaForm(obj=conquista)
    if form.validate_on_submit():
        conquista.ano = form.ano.data
        conquista.colocacao = form.colocacao.data
        conquista.categoria = form.categoria.data.strip()
        conquista.titulo = form.titulo.data.strip()
        conquista.torneio = form.torneio.data.strip() if form.torneio.data else 'Circuito AIBT'
        conquista.destaque = form.destaque.data
        conquista.ordem = form.ordem.data or 0
        db.session.commit()
        flash(f'Conquista "{conquista.titulo}" atualizada com sucesso!', 'success')
        return redirect(url_for('admin.conquistas_lista'))
        
    return render_template('admin/site/conquista_form.html', form=form, conquista=conquista)


@admin_bp.route('/site/conquistas/<int:id>/excluir', methods=['POST'])
@admin_required
def conquista_excluir(id):
    conquista = db.get_or_404(Conquista, id)
    db.session.delete(conquista)
    db.session.commit()
    flash('Conquista excluída com sucesso.', 'info')
    return redirect(url_for('admin.conquistas_lista'))


# ── MODALIDADES ─────────────────────────────────────────────────────────
@admin_bp.route('/site/modalidades')
@admin_required
def modalidades_lista():
    modalidades = Modalidade.query.order_by(Modalidade.ordem.asc(), Modalidade.id.asc()).all()
    return render_template('admin/site/modalidades_lista.html', modalidades=modalidades)


@admin_bp.route('/site/modalidades/nova', methods=['GET', 'POST'])
@admin_required
def modalidade_nova():
    form = ModalidadeForm()
    if form.validate_on_submit():
        modalidade = Modalidade(
            nome=form.nome.data.strip(),
            descricao=form.descricao.data.strip(),
            icone=form.icone.data.strip() if form.icone.data else 'bi-tsunami',
            publico_alvo=form.publico_alvo.data.strip() if form.publico_alvo.data else None,
            duracao_estimada=form.duracao_estimada.data.strip() if form.duracao_estimada.data else '60 min',
            destaque=form.destaque.data,
            ativo=form.ativo.data,
            ordem=form.ordem.data or 0
        )
        db.session.add(modalidade)
        db.session.commit()
        flash(f'Modalidade "{modalidade.nome}" cadastrada com sucesso!', 'success')
        return redirect(url_for('admin.modalidades_lista'))
        
    return render_template('admin/site/modalidade_form.html', form=form, modalidade=None)


@admin_bp.route('/site/modalidades/<int:id>/editar', methods=['GET', 'POST'])
@admin_required
def modalidade_editar(id):
    modalidade = db.get_or_404(Modalidade, id)
    form = ModalidadeForm(obj=modalidade)
    if form.validate_on_submit():
        modalidade.nome = form.nome.data.strip()
        modalidade.descricao = form.descricao.data.strip()
        modalidade.icone = form.icone.data.strip() if form.icone.data else 'bi-tsunami'
        modalidade.publico_alvo = form.publico_alvo.data.strip() if form.publico_alvo.data else None
        modalidade.duracao_estimada = form.duracao_estimada.data.strip() if form.duracao_estimada.data else '60 min'
        modalidade.destaque = form.destaque.data
        modalidade.ativo = form.ativo.data
        modalidade.ordem = form.ordem.data or 0
        db.session.commit()
        flash(f'Modalidade "{modalidade.nome}" atualizada com sucesso!', 'success')
        return redirect(url_for('admin.modalidades_lista'))
        
    return render_template('admin/site/modalidade_form.html', form=form, modalidade=modalidade)


@admin_bp.route('/site/modalidades/<int:id>/excluir', methods=['POST'])
@admin_required
def modalidade_excluir(id):
    modalidade = db.get_or_404(Modalidade, id)
    db.session.delete(modalidade)
    db.session.commit()
    flash('Modalidade excluída com sucesso.', 'info')
    return redirect(url_for('admin.modalidades_lista'))


# ── PLANOS E VALORES ────────────────────────────────────────────────────
@admin_bp.route('/planos')
@admin_bp.route('/site/planos')
@admin_required
def planos_lista():
    planos = Plano.query.order_by(Plano.ordem.asc(), Plano.preco.asc()).all()
    return render_template('admin/site/planos_lista.html', planos=planos)


@admin_bp.route('/site/planos/novo', methods=['GET', 'POST'])
@admin_required
def plano_novo():
    form = PlanoForm()
    if form.validate_on_submit():
        plano = Plano(
            nome=form.nome.data.strip(),
            descricao=form.descricao.data.strip() if form.descricao.data else None,
            preco=form.preco.data,
            periodo=form.periodo.data,
            aulas_por_semana=form.aulas_por_semana.data,
            destaque=form.destaque.data,
            ativo=form.ativo.data,
            ordem=form.ordem.data or 0
        )
        db.session.add(plano)
        db.session.commit()
        flash(f'Plano "{plano.nome}" cadastrado com sucesso!', 'success')
        return redirect(url_for('admin.planos_lista'))
        
    return render_template('admin/site/plano_form.html', form=form, plano=None)


@admin_bp.route('/site/planos/<int:id>/editar', methods=['GET', 'POST'])
@admin_required
def plano_editar(id):
    plano = db.get_or_404(Plano, id)
    form = PlanoForm(obj=plano)
    if form.validate_on_submit():
        plano.nome = form.nome.data.strip()
        plano.descricao = form.descricao.data.strip() if form.descricao.data else None
        plano.preco = form.preco.data
        plano.periodo = form.periodo.data
        plano.aulas_por_semana = form.aulas_por_semana.data
        plano.destaque = form.destaque.data
        plano.ativo = form.ativo.data
        plano.ordem = form.ordem.data or 0
        db.session.commit()
        flash(f'Plano "{plano.nome}" atualizado com sucesso!', 'success')
        return redirect(url_for('admin.planos_lista'))
        
    return render_template('admin/site/plano_form.html', form=form, plano=plano)


@admin_bp.route('/site/planos/<int:id>/excluir', methods=['POST'])
@admin_required
def plano_excluir(id):
    plano = db.get_or_404(Plano, id)
    db.session.delete(plano)
    db.session.commit()
    flash('Plano excluído com sucesso.', 'info')
    return redirect(url_for('admin.planos_lista'))


# ── DEPOIMENTOS ─────────────────────────────────────────────────────────
@admin_bp.route('/depoimentos')
@admin_bp.route('/site/depoimentos')
@admin_required
def depoimentos():
    depoimentos = Depoimento.query.order_by(Depoimento.aprovado.asc(), Depoimento.criado_em.desc()).all()
    return render_template('admin/site/depoimentos_lista.html', depoimentos=depoimentos)


@admin_bp.route('/site/depoimentos/novo', methods=['GET', 'POST'])
@admin_required
def depoimento_novo():
    form = DepoimentoForm()
    if form.validate_on_submit():
        foto_nome = None
        if form.foto.data and form.foto.data.filename:
            foto_nome = salvar_imagem(form.foto.data, 'dep')
            
        dep = Depoimento(
            nome=form.nome.data.strip(),
            texto=form.texto.data.strip(),
            foto=foto_nome,
            aprovado=form.aprovado.data,
            destaque=form.destaque.data,
            ordem=form.ordem.data or 0
        )
        db.session.add(dep)
        db.session.commit()
        flash('Depoimento cadastrado com sucesso!', 'success')
        return redirect(url_for('admin.depoimentos'))
        
    return render_template('admin/site/depoimento_form.html', form=form, depoimento=None)


@admin_bp.route('/site/depoimentos/<int:id>/editar', methods=['GET', 'POST'])
@admin_required
def depoimento_editar(id):
    dep = db.get_or_404(Depoimento, id)
    form = DepoimentoForm(obj=dep)
    if form.validate_on_submit():
        dep.nome = form.nome.data.strip()
        dep.texto = form.texto.data.strip()
        dep.aprovado = form.aprovado.data
        dep.destaque = form.destaque.data
        dep.ordem = form.ordem.data or 0
        
        if form.foto.data and form.foto.data.filename:
            dep.foto = salvar_imagem(form.foto.data, 'dep')
            
        db.session.commit()
        flash('Depoimento atualizado com sucesso!', 'success')
        return redirect(url_for('admin.depoimentos'))
        
    return render_template('admin/site/depoimento_form.html', form=form, depoimento=dep)


@admin_bp.route('/site/depoimentos/<int:id>/toggle-aprovado', methods=['POST'])
@admin_required
def depoimento_toggle_aprovado(id):
    dep = db.get_or_404(Depoimento, id)
    dep.aprovado = not dep.aprovado
    db.session.commit()
    estado = 'aprovado' if dep.aprovado else 'reprovado'
    flash(f'Depoimento de {dep.nome} marcado como {estado}.', 'info')
    return redirect(url_for('admin.depoimentos'))


@admin_bp.route('/site/depoimentos/<int:id>/excluir', methods=['POST'])
@admin_required
def depoimento_excluir(id):
    dep = db.get_or_404(Depoimento, id)
    db.session.delete(dep)
    db.session.commit()
    flash('Depoimento excluído com sucesso.', 'info')
    return redirect(url_for('admin.depoimentos'))


# ── GALERIA ─────────────────────────────────────────────────────────────
@admin_bp.route('/site/galeria')
@admin_required
def galeria_lista():
    itens = GaleriaItem.query.order_by(GaleriaItem.ordem.asc(), GaleriaItem.criado_em.desc()).all()
    return render_template('admin/site/galeria_lista.html', itens=itens)


@admin_bp.route('/site/galeria/novo', methods=['GET', 'POST'])
@admin_required
def galeria_novo():
    form = GaleriaItemForm()
    if form.validate_on_submit():
        arquivo_nome = None
        if form.tipo.data == 'imagem' and form.arquivo.data and form.arquivo.data.filename:
            arquivo_nome = salvar_imagem(form.arquivo.data, 'gal')
            
        item = GaleriaItem(
            titulo=form.titulo.data.strip(),
            tipo=form.tipo.data,
            arquivo=arquivo_nome,
            url_video=converter_para_embed(form.url_video.data) if form.url_video.data else None,
            legenda=form.legenda.data.strip() if form.legenda.data else None,
            destaque=form.destaque.data,
            ativo=form.ativo.data,
            ordem=form.ordem.data or 0
        )
        db.session.add(item)
        db.session.commit()
        flash('Item adicionado à galeria com sucesso!', 'success')
        return redirect(url_for('admin.galeria_lista'))
        
    return render_template('admin/site/galeria_form.html', form=form, item=None)


@admin_bp.route('/site/galeria/<int:id>/editar', methods=['GET', 'POST'])
@admin_required
def galeria_editar(id):
    item = db.get_or_404(GaleriaItem, id)
    form = GaleriaItemForm(obj=item)
    if form.validate_on_submit():
        item.titulo = form.titulo.data.strip()
        item.tipo = form.tipo.data
        item.url_video = converter_para_embed(form.url_video.data) if form.url_video.data else None
        item.legenda = form.legenda.data.strip() if form.legenda.data else None
        item.destaque = form.destaque.data
        item.ativo = form.ativo.data
        item.ordem = form.ordem.data or 0
        
        if form.tipo.data == 'imagem' and form.arquivo.data and form.arquivo.data.filename:
            item.arquivo = salvar_imagem(form.arquivo.data, 'gal')
            
        db.session.commit()
        flash('Item da galeria atualizado com sucesso!', 'success')
        return redirect(url_for('admin.galeria_lista'))
        
    return render_template('admin/site/galeria_form.html', form=form, item=item)


@admin_bp.route('/site/galeria/<int:id>/excluir', methods=['POST'])
@admin_required
def galeria_excluir(id):
    item = db.get_or_404(GaleriaItem, id)
    db.session.delete(item)
    db.session.commit()
    flash('Item excluído da galeria com sucesso.', 'info')
    return redirect(url_for('admin.galeria_lista'))


# ── MENSAGENS RECEBIDAS (CONTATO) ───────────────────────────────────────
@admin_bp.route('/site/mensagens')
@admin_required
def mensagens_lista():
    filtro = request.args.get('filtro', 'todas')
    query = MensagemContato.query
    if filtro == 'nao_lidas':
        query = query.filter_by(lida=False)
    elif filtro == 'lidas':
        query = query.filter_by(lida=True)
    elif filtro == 'respondidas':
        query = query.filter_by(respondida=True)
        
    mensagens = query.order_by(MensagemContato.criado_em.desc()).all()
    total_nao_lidas = MensagemContato.query.filter_by(lida=False).count()
    
    return render_template(
        'admin/site/mensagens_lista.html',
        mensagens=mensagens,
        filtro=filtro,
        total_nao_lidas=total_nao_lidas
    )


@admin_bp.route('/site/mensagens/<int:id>/marcar-lida', methods=['POST'])
@admin_required
def mensagem_marcar_lida(id):
    msg = db.get_or_404(MensagemContato, id)
    msg.lida = not msg.lida
    db.session.commit()
    flash('Status de leitura atualizado.', 'info')
    return redirect(url_for('admin.mensagens_lista'))


@admin_bp.route('/site/mensagens/<int:id>/marcar-respondida', methods=['POST'])
@admin_required
def mensagem_marcar_respondida(id):
    msg = db.get_or_404(MensagemContato, id)
    msg.respondida = not msg.respondida
    if msg.respondida:
        msg.lida = True
    db.session.commit()
    flash('Status de resposta atualizado.', 'info')
    return redirect(url_for('admin.mensagens_lista'))


@admin_bp.route('/site/mensagens/<int:id>/excluir', methods=['POST'])
@admin_required
def mensagem_excluir(id):
    msg = db.get_or_404(MensagemContato, id)
    db.session.delete(msg)
    db.session.commit()
    flash('Mensagem excluída com sucesso.', 'info')
    return redirect(url_for('admin.mensagens_lista'))


# ── BT TRACKER: SCOUT & ANÁLISE DE PARTIDAS ──────────────────────────────
@admin_bp.route('/sincronizar-banco', methods=['GET', 'POST'])
@admin_required
def sincronizar_banco():
    """Garante que todas as tabelas e novas colunas existam no banco de produção."""
    try:
        garantir_esquema_banco()
        flash('Banco de dados sincronizado e todas as colunas atualizadas com sucesso!', 'success')
    except Exception as e:
        flash(f'Erro ao sincronizar banco: {e}', 'danger')
    return redirect(url_for('admin.partidas_lista'))


@admin_bp.route('/partidas')
@admin_required
def partidas_lista():
    """Listagem de todas as partidas cadastradas no BT Tracker."""
    busca = request.args.get('busca', '').strip()
    categoria = request.args.get('categoria', '').strip()

    query = Partida.query
    if busca:
        termo = f"%{busca}%"
        query = query.filter(
            db.or_(
                Partida.titulo.ilike(termo),
                Partida.jogador1_nome.ilike(termo),
                Partida.jogador2_nome.ilike(termo),
                Partida.jogador3_nome.ilike(termo),
                Partida.jogador4_nome.ilike(termo),
                Partida.torneio.ilike(termo),
            )
        )
    if categoria:
        query = query.filter_by(categoria=categoria)

    try:
        partidas = query.order_by(Partida.data.desc(), Partida.id.desc()).all()
        return render_template('admin/partidas/lista.html', partidas=partidas, busca=busca, categoria=categoria)
    except Exception:
        db.session.rollback()
        try:
            garantir_esquema_banco()
            partidas = query.order_by(Partida.data.desc(), Partida.id.desc()).all()
            return render_template('admin/partidas/lista.html', partidas=partidas, busca=busca, categoria=categoria)
        except Exception:
            db.session.rollback()
            return render_template('admin/partidas/lista.html', partidas=[], busca=busca, categoria=categoria)


@admin_bp.route('/partidas/nova', methods=['GET', 'POST'])
@admin_required
def partida_nova():
    """Cria uma nova partida no BT Tracker."""
    form = PartidaForm()
    alunos = Aluno.query.filter_by(ativo=True).order_by(Aluno.nome.asc()).all()
    aluno_choices = [(0, '-- Selecione um Aluno (ou digite o nome ao lado) --')] + [(a.id, a.nome) for a in alunos]
    form.jogador1_aluno_id.choices = aluno_choices
    form.jogador2_aluno_id.choices = aluno_choices
    form.jogador3_aluno_id.choices = aluno_choices
    form.jogador4_aluno_id.choices = aluno_choices

    if form.validate_on_submit():
        partida = Partida(
            titulo=form.titulo.data.strip(),
            data=form.data.data,
            torneio=form.torneio.data.strip() if form.torneio.data else 'Circuito AIBT',
            categoria=form.categoria.data.strip() if form.categoria.data else 'Masculina B',
            fase=form.fase.data.strip() if form.fase.data else 'Final',
            local=form.local.data.strip() if form.local.data else 'Arena Itabuna',
            jogador1_nome=form.jogador1_nome.data.strip(),
            jogador1_aluno_id=form.jogador1_aluno_id.data if form.jogador1_aluno_id.data > 0 else None,
            jogador2_nome=form.jogador2_nome.data.strip(),
            jogador2_aluno_id=form.jogador2_aluno_id.data if form.jogador2_aluno_id.data > 0 else None,
            jogador3_nome=form.jogador3_nome.data.strip(),
            jogador3_aluno_id=form.jogador3_aluno_id.data if form.jogador3_aluno_id.data > 0 else None,
            jogador4_nome=form.jogador4_nome.data.strip(),
            jogador4_aluno_id=form.jogador4_aluno_id.data if form.jogador4_aluno_id.data > 0 else None,
            set1_dupla1=form.set1_dupla1.data,
            set1_dupla2=form.set1_dupla2.data,
            set2_dupla1=form.set2_dupla1.data,
            set2_dupla2=form.set2_dupla2.data,
            set3_dupla1=form.set3_dupla1.data,
            set3_dupla2=form.set3_dupla2.data,
            placar_detalhado=form.placar_detalhado.data.strip() if form.placar_detalhado.data else None,
            dupla_vencedora=form.dupla_vencedora.data,
            duracao_minutos=form.duracao_minutos.data,
            observacoes=form.observacoes.data.strip() if form.observacoes.data else None,
            status=form.status.data or 'aprovada',
            comentario_professor=form.comentario_professor.data.strip() if form.comentario_professor.data else None,
            validada_em=datetime.utcnow() if (form.status.data or 'aprovada') == 'aprovada' else None,
        )
        db.session.add(partida)
        db.session.commit()
        flash(f'Partida "{partida.titulo}" criada com sucesso! Você já pode visualizar a análise e registrar lances.', 'success')
        return redirect(url_for('admin.partida_detalhes', id=partida.id))

    return render_template('admin/partidas/form.html', form=form, partida=None)


@admin_bp.route('/partidas/<int:id>/editar', methods=['GET', 'POST'])
@admin_required
def partida_editar(id):
    """Edita dados e placares de uma partida existente."""
    partida = db.get_or_404(Partida, id)
    form = PartidaForm(obj=partida)

    alunos = Aluno.query.filter_by(ativo=True).order_by(Aluno.nome.asc()).all()
    aluno_choices = [(0, '-- Selecione um Aluno (ou digite o nome ao lado) --')] + [(a.id, a.nome) for a in alunos]
    form.jogador1_aluno_id.choices = aluno_choices
    form.jogador2_aluno_id.choices = aluno_choices
    form.jogador3_aluno_id.choices = aluno_choices
    form.jogador4_aluno_id.choices = aluno_choices

    if form.validate_on_submit():
        partida.titulo = form.titulo.data.strip()
        partida.data = form.data.data
        partida.torneio = form.torneio.data.strip() if form.torneio.data else None
        partida.categoria = form.categoria.data.strip() if form.categoria.data else None
        partida.fase = form.fase.data.strip() if form.fase.data else None
        partida.local = form.local.data.strip() if form.local.data else None
        partida.jogador1_nome = form.jogador1_nome.data.strip()
        partida.jogador1_aluno_id = form.jogador1_aluno_id.data if form.jogador1_aluno_id.data > 0 else None
        partida.jogador2_nome = form.jogador2_nome.data.strip()
        partida.jogador2_aluno_id = form.jogador2_aluno_id.data if form.jogador2_aluno_id.data > 0 else None
        partida.jogador3_nome = form.jogador3_nome.data.strip()
        partida.jogador3_aluno_id = form.jogador3_aluno_id.data if form.jogador3_aluno_id.data > 0 else None
        partida.jogador4_nome = form.jogador4_nome.data.strip()
        partida.jogador4_aluno_id = form.jogador4_aluno_id.data if form.jogador4_aluno_id.data > 0 else None
        partida.set1_dupla1 = form.set1_dupla1.data
        partida.set1_dupla2 = form.set1_dupla2.data
        partida.set2_dupla1 = form.set2_dupla1.data
        partida.set2_dupla2 = form.set2_dupla2.data
        partida.set3_dupla1 = form.set3_dupla1.data
        partida.set3_dupla2 = form.set3_dupla2.data
        partida.placar_detalhado = form.placar_detalhado.data.strip() if form.placar_detalhado.data else None
        partida.dupla_vencedora = form.dupla_vencedora.data
        partida.duracao_minutos = form.duracao_minutos.data
        partida.observacoes = form.observacoes.data.strip() if form.observacoes.data else None
        partida.status = form.status.data
        partida.comentario_professor = form.comentario_professor.data.strip() if form.comentario_professor.data else None
        if form.status.data == 'aprovada' and not partida.validada_em:
            partida.validada_em = datetime.utcnow()

        db.session.commit()
        flash('Partida atualizada com sucesso!', 'success')
        return redirect(url_for('admin.partida_detalhes', id=partida.id))

    return render_template('admin/partidas/form.html', form=form, partida=partida)


@admin_bp.route('/partidas/<int:id>/validar', methods=['POST'])
@admin_required
def partida_validar(id):
    """O professor aprova a partida enviada pelo aluno e insere correções/feedbacks opcionais."""
    partida = db.get_or_404(Partida, id)
    comentario = request.form.get('comentario_professor', '').strip()
    
    partida.status = 'aprovada'
    partida.validada_em = datetime.utcnow()
    if comentario:
        partida.comentario_professor = comentario

    db.session.commit()
    flash(f'Partida #{partida.id} validada e aprovada com sucesso! O aluno já pode visualizá-la.', 'success')
    return redirect(url_for('admin.partida_detalhes', id=partida.id))


@admin_bp.route('/partidas/<int:id>/rejeitar', methods=['POST'])
@admin_required
def partida_rejeitar(id):
    """O professor solicita correções na partida enviada pelo aluno."""
    partida = db.get_or_404(Partida, id)
    comentario = request.form.get('comentario_professor', '').strip()
    
    partida.status = 'rejeitada'
    if comentario:
        partida.comentario_professor = comentario

    db.session.commit()
    flash(f'Status da partida #{partida.id} alterado para "Ajustes Solicitados".', 'warning')
    return redirect(url_for('admin.partida_detalhes', id=partida.id))


@admin_bp.route('/partidas/carregar-partida-exemplo', methods=['GET', 'POST'])
@admin_required
def partida_carregar_exemplo():
    """Carrega uma partida oficial do BT Tracker com 42 lances reais para teste imediato."""
    aluno_padrao = Aluno.query.first()
    partida = Partida(
        titulo='Final Circuito AIBT 2026 — Masculina B',
        data=date.today(),
        torneio='Circuito AIBT 2026',
        categoria='Masculina B',
        fase='Final',
        local='Arena Itabuna (Quadra Central)',
        jogador1_nome='Everson Vicktor',
        jogador2_nome=aluno_padrao.nome if aluno_padrao else 'Lucas Silva',
        jogador2_aluno_id=aluno_padrao.id if aluno_padrao else None,
        jogador3_nome='Carlos Mendes',
        jogador4_nome='Rafael Costa',
        set1_dupla1=4,
        set1_dupla2=6,
        set2_dupla1=3,
        set2_dupla2=6,
        placar_detalhado='4x6 | 3x6',
        dupla_vencedora=2,
        duracao_minutos=75,
        status='aprovada',
        observacoes='Grande final do Circuito AIBT com vento moderado. Destaque para os smashes e variações de saque aberto.'
    )
    db.session.add(partida)
    db.session.flush()

    amostra_pontos = [
        (4, 1, 3, 'erro_nao_forcado', 'Smash', 'Esquerda', '2', 'Bom', 'No sacador', 'Boa', '0x0 15x0', None, 45, 60, 50, 15, 'Erro não forçado de Smash de Carlos Mendes'),
        (4, 2, 4, 'winner', 'Smash', 'Esquerda', '3', 'Bom', 'Meio', 'Regular', '0x0 15x15', None, 60, 80, 20, 25, 'Winner de Smash de Rafael Costa'),
        (4, 2, 1, 'erro_nao_forcado', 'Avanço com Forehand', 'Esquerda', '4', 'Bom', 'No sacador', 'Regular', '0x0 15x30', None, 30, 20, 35, 95, 'Erro não forçado de Avanço de Everson Vicktor'),
        (4, 1, 4, 'erro_saque', None, 'Esquerda', '5', 'Erro', None, None, '0x0 30x30', None, 65, 85, 65, 45, 'Erro de Saque de Rafael Costa'),
        (4, 1, 4, 'erro_saque', None, 'Esquerda', '3', 'Erro', None, None, '0x0 40x30', None, 65, 85, 50, 48, 'Erro de Saque de Rafael Costa'),
        (4, 2, 4, 'winner', 'Gancho', 'Esquerda', '2', 'Bom', 'Lob', 'Regular', '0x0 40x40', 'Bola na Fita', 70, 75, 25, 20, 'Winner de Gancho de Rafael Costa [40x40 Decisivo]'),
        (4, 2, 4, 'forcou_erro', 'Lob Chutado com Forehand', 'Esquerda', '3', 'Bom', 'Meio', 'Ruim', '0x1', None, 50, 80, 80, 15, 'Rafael Costa forçou o erro com Lob Chutado'),
        (2, 2, 2, 'erro_saque', None, 'Direita', '1', 'Erro', None, None, '0x1 0x15', None, 35, 15, 35, 52, 'Erro de Saque de Jogador 2'),
        (2, 2, 2, 'erro_saque', None, 'Direita', '1', 'Erro', None, None, '0x1 0x30', None, 35, 15, 45, 53, 'Erro de Saque de Jogador 2'),
        (2, 2, 4, 'winner', 'Smash', 'Direita', '3', 'Regular', 'No sacador', 'Boa', '0x1 0x40', None, 65, 80, 30, 20, 'Winner de Smash de Rafael Costa'),
        (2, 1, 4, 'erro_devolucao', None, 'Direita', '2', 'Bom', 'No sacador', 'Erro', '0x1 15x40', None, 40, 20, 70, 70, 'Erro de devolução de Rafael Costa'),
        (2, 2, 4, 'forcou_erro', 'Smash', 'Direita', '3', 'Regular', 'Meio', 'Ruim', '0x2', None, 75, 75, 40, 25, 'Rafael Costa forçou o erro com Smash'),
        (3, 2, 4, 'winner', 'Smash', 'Direita', '3', 'Bom', 'No sacador', 'Regular', '0x2 0x15', None, 65, 80, 25, 15, 'Winner de Smash de Rafael Costa'),
        (3, 2, 4, 'winner', 'Lob Chutado com Forehand', 'Direita', '3', 'Bom', 'Meio', 'Regular', '0x2 0x30', 'Bola na Linha', 70, 75, 20, 10, 'Winner de Lob Chutado de Rafael Costa'),
        (3, 1, 2, 'winner', 'Lob Chutado com Backhand', 'Direita', '2', 'Regular', 'No sacador', 'Boa', '0x2 15x30', None, 40, 25, 80, 85, 'Winner de Lob Chutado de Jogador 2'),
        (3, 2, 2, 'erro_devolucao', None, 'Direita', '4', 'Bom', 'No parceiro', 'Erro', '0x2 15x40', 'Bola na Fita', 35, 85, 30, 30, 'Erro de devolução de Jogador 2'),
        (3, 1, 2, 'forcou_erro', 'Smash', 'Direita', '3', 'Regular', 'Meio', 'Regular', '0x2 30x40', None, 45, 30, 65, 80, 'Jogador 2 forçou erro com Smash'),
        (3, 2, 4, 'winner', 'Gancho', 'Direita', '3', 'Bom', 'No sacador', 'Regular', '0x3', None, 60, 75, 30, 15, 'Winner de Gancho de Rafael Costa'),
        (1, 2, 3, 'winner', 'Curta com Forehand', 'Direita', '3', 'Regular', 'No sacador', 'Boa', '0x3 0x15', 'Bola na Linha', 30, 70, 45, 45, 'Winner de Curta de Carlos Mendes'),
        (1, 1, 1, 'ace', None, 'Direita', '4', 'Ace', None, None, '0x3 15x15', None, 30, 15, 75, 75, 'Ace no ângulo de Everson Vicktor'),
        (1, 2, 4, 'forcou_erro', 'Lob Chutado com Forehand', 'Direita', '2', 'Regular', 'Meio', 'Ruim', '0x3 15x30', None, 70, 80, 30, 20, 'Rafael Costa forçou o erro com Lob Chutado'),
        (1, 2, 3, 'winner', 'Devolução com Forehand', 'Direita', '3', 'Regular', 'No sacador', 'Winner', '0x3 15x40', None, 30, 70, 75, 20, 'Winner de Devolução de Carlos Mendes'),
        (1, 1, 4, 'erro_devolucao', None, 'Direita', '3', 'Bom', 'No sacador', 'Erro', '0x3 30x40', None, 40, 20, 65, 65, 'Erro de devolução de Rafael Costa'),
        (1, 1, 3, 'erro_nao_forcado', 'Smash', 'Direita', '4', 'Bom', 'Meio', 'Regular', '0x3 40x40', 'Furou a bola', 35, 75, 40, 55, 'Erro não forçado de Smash de Carlos Mendes'),
        (1, 2, 1, 'erro_nao_forcado', 'Lob Chutado com Forehand', 'Direita', '3', 'Bom', 'No sacador', 'Regular', '0x4', None, 35, 25, 40, 95, 'Erro não forçado de Lob Chutado de Everson Vicktor'),
        (4, 2, 4, 'winner', 'Lob Chutado com Forehand', 'Esquerda', '3', 'Bom', 'Meio', 'Regular', '0x4 0x15', None, 65, 80, 25, 15, 'Winner de Lob Chutado de Rafael Costa'),
        (4, 1, 4, 'erro_saque', None, 'Esquerda', '4', 'Erro', None, None, '0x4 15x15', None, 65, 85, 40, 45, 'Erro de Saque de Rafael Costa'),
        (4, 1, 1, 'forcou_erro', 'Voleio estático com Forehand', 'Esquerda', '2', 'Regular', 'No sacador', 'Boa', '0x4 30x15', None, 40, 35, 60, 65, 'Everson Vicktor forçou erro com Voleio Estático'),
        (4, 2, 3, 'forcou_erro', '1-2 Combination', 'Esquerda', '3', 'Bom', 'Meio', 'Ruim', '0x4 30x30', None, 35, 65, 30, 25, 'Carlos Mendes forçou erro com 1-2 Combination'),
        (4, 1, 3, 'erro_nao_forcado', 'Curta com Forehand', 'Esquerda', '2', 'Bom', 'No sacador', 'Boa', '0x4 40x30', None, 40, 60, 45, 55, 'Erro não forçado de Curta de Carlos Mendes'),
        (4, 1, 1, 'forcou_erro', 'Smash', 'Esquerda', '3', 'Regular', 'Meio', 'Boa', '1x4', None, 35, 30, 65, 75, 'Everson Vicktor forçou erro com Smash'),
        (2, 1, 1, 'winner', 'Smash', 'Direita', '3', 'Bom', 'Meio', 'Regular', '1x4 15x30', None, 35, 35, 65, 80, 'Winner de Smash de Everson Vicktor'),
        (2, 1, 4, 'erro_nao_forcado', 'Curta com Backhand', 'Direita', '2', 'Bom', 'No sacador', 'Regular', '1x4 30x30', None, 65, 70, 60, 52, 'Erro não forçado de Curta de Rafael Costa'),
        (2, 1, 1, 'forcou_erro', 'Smash', 'Direita', '3', 'Bom', 'Meio', 'Regular', '1x4 40x30', None, 40, 30, 75, 75, 'Everson Vicktor forçou erro com Smash'),
        (2, 2, 3, 'winner', 'Smash', 'Direita', '4', 'Regular', 'No sacador', 'Boa', '1x4 40x40', None, 35, 75, 35, 20, 'Winner de Smash de Carlos Mendes'),
        (2, 1, 1, 'forcou_erro', '1-2 Combination', 'Direita', '3', 'Bom', 'Meio', 'Regular', '2x4', None, 35, 35, 70, 70, 'Everson Vicktor forçou o erro com 1-2 Combination'),
        (3, 1, 1, 'winner', 'Smash', 'Direita', '3', 'Regular', 'Meio', 'Boa', '2x4 15x0', None, 40, 30, 65, 75, 'Winner de Smash de Everson Vicktor'),
        (3, 1, 3, 'erro_saque', None, 'Direita', '2', 'Erro', None, None, '2x4 30x0', None, 35, 85, 50, 45, 'Erro de Saque de Carlos Mendes'),
        (3, 2, 2, 'erro_devolucao', None, 'Direita', '3', 'Bom', 'No sacador', 'Erro', '2x4 30x15', None, 45, 20, 35, 85, 'Erro de devolução de Jogador 2'),
        (3, 1, 3, 'erro_saque', None, 'Direita', '4', 'Erro', None, None, '2x4 40x15', None, 35, 85, 30, 45, 'Erro de Saque de Carlos Mendes'),
        (3, 2, 4, 'winner', 'Lob Chutado com Forehand', 'Direita', '3', 'Bom', 'Meio', 'Regular', '2x4 40x30', None, 70, 80, 25, 15, 'Winner de Lob Chutado de Rafael Costa'),
        (3, 1, 3, 'erro_nao_forcado', 'Lob Chutado com Forehand', 'Direita', '3', 'Bom', 'Meio', 'Regular', '3x4', None, 35, 75, 35, 5, 'Erro não forçado de Lob Chutado de Carlos Mendes'),
    ]

    for idx, pt in enumerate(amostra_pontos, start=1):
        ponto = PontoPartida(
            partida_id=partida.id,
            numero_ponto=idx,
            sacador=pt[0],
            dupla_vencedora=pt[1],
            atleta_finalizador=pt[2],
            tipo_desfecho=pt[3],
            tipo_golpe=pt[4],
            posicao_sacador=pt[5],
            direcao_saque=pt[6],
            qualidade_saque=pt[7],
            direcao_devolucao=pt[8],
            qualidade_devolucao=pt[9],
            placar_texto=pt[10],
            situacao_adicional=pt[11],
            origem_x=pt[12],
            origem_y=pt[13],
            destino_x=pt[14],
            destino_y=pt[15],
            descricao_lance=pt[16],
            duracao_ponto='Curto' if pt[3] in ['ace', 'erro_saque'] else ('Longo' if 'Lob' in str(pt[4]) else 'Médio')
        )
        db.session.add(ponto)

    db.session.commit()
    flash('Partida oficial do BT Insight com 42 lances carregada com sucesso!', 'success')
    return redirect(url_for('admin.partida_detalhes', id=partida.id))


@admin_bp.route('/partidas/<int:id>')
@admin_required
def partida_detalhes(id):
    """Dashboard de análise completa da partida no formato BT Insight."""
    partida = db.get_or_404(Partida, id)
    stats = calcular_estatisticas_partida(partida)
    return render_template('admin/partidas/detalhes.html', partida=partida, stats=stats)


@admin_bp.route('/partidas/<int:id>/pdf')
@admin_required
def partida_pdf(id):
    """Exporta o relatório completo da partida em PDF no padrão oficial BT Insight."""
    partida = db.get_or_404(Partida, id)
    pdf_bytes = gerar_pdf_bt_tracker(partida)

    nome_arquivo = f"BT_Insight_{secure_filename(partida.dupla1_label)}_vs_{secure_filename(partida.dupla2_label)}.pdf"
    return Response(
        pdf_bytes,
        mimetype='application/pdf',
        headers={'Content-Disposition': f'attachment; filename="{nome_arquivo}"'}
    )


@admin_bp.route('/partidas/<int:id>/excluir', methods=['POST'])
@admin_required
def partida_excluir(id):
    """Exclui a partida e todos os pontos associados."""
    partida = db.get_or_404(Partida, id)
    db.session.delete(partida)
    db.session.commit()
    flash('Partida excluída com sucesso.', 'info')
    return redirect(url_for('admin.partidas_lista'))


def _processar_dados_ponto(partida, form_data):
    """
    Processa os dados de um ponto de scout de forma simplificada:
    - A dupla foca apenas nas suas próprias ações (Jogador 1 e Jogador 2).
    - Não precisa detalhar ações dos adversários.
    - Análise de saque detalhada apenas para a nossa dupla; quando o adversário saca,
      apenas informa se o saque foi difícil (saque_dificil).
    """
    sacador = int(form_data.get('sacador', 1))
    dupla_vencedora = int(form_data.get('dupla_vencedora', 1))
    saque_dificil = form_data.get('saque_dificil') in ('1', 'true', 'True', 'on', 'sim', 'Sim')

    if sacador in (1, 2):
        # Nossa dupla sacando: análise técnica completa
        posicao_sacador = form_data.get('posicao_sacador', 'Direita')
        direcao_saque = form_data.get('direcao_saque', '3')
        qualidade_saque = form_data.get('qualidade_saque', 'Bom')
        saque_dificil = False
    else:
        # Adversário sacando: não detalha saque do adversário, apenas se foi difícil
        posicao_sacador = None
        direcao_saque = None
        qualidade_saque = 'Difícil' if saque_dificil else 'Regular'
        sacador = 3  # Dupla adversária representada

    tipo_desfecho_raw = form_data.get('tipo_desfecho', 'winner')

    # Ações e finalizador simplificados
    if tipo_desfecho_raw in ('winner_adversario', 'ponto_adversario'):
        tipo_desfecho = 'winner'
        atleta_finalizador = 3
        tipo_golpe = None
        descricao_lance = "Ponto / Winner do adversário"
    elif tipo_desfecho_raw in ('erro_adversario', 'erro_nao_forcado_adversario'):
        tipo_desfecho = 'erro_nao_forcado'
        atleta_finalizador = 3
        tipo_golpe = None
        descricao_lance = "Erro não forçado do adversário"
    elif tipo_desfecho_raw in ('erro_saque_adversario',):
        tipo_desfecho = 'erro_saque'
        atleta_finalizador = 3
        tipo_golpe = None
        descricao_lance = "Erro de saque do adversário"
    else:
        # Ação executada pela nossa dupla
        tipo_desfecho = tipo_desfecho_raw
        atleta_finalizador = int(form_data.get('atleta_finalizador', 1))
        if atleta_finalizador not in (1, 2):
            atleta_finalizador = 1
        tipo_golpe = form_data.get('tipo_golpe', '').strip() or None
        fin_nome = partida.get_jogador_nome(atleta_finalizador)
        nomes_desfecho = {
            'winner': 'Winner',
            'forcou_erro': 'Forçou erro',
            'erro_nao_forcado': 'Erro não forçado',
            'ace': 'Ace',
            'erro_saque': 'Erro de saque',
            'erro_devolucao': 'Erro de devolução'
        }
        desf_label = nomes_desfecho.get(tipo_desfecho, tipo_desfecho.replace('_', ' ').capitalize())
        descricao_lance = f"{desf_label} de {fin_nome}"
        if tipo_golpe:
            descricao_lance += f" ({tipo_golpe})"

    if saque_dificil and sacador in (3, 4):
        descricao_lance += " [Saque difícil do adversário]"

    placar_texto = form_data.get('placar_texto', '').strip() or None
    situacao_adicional = form_data.get('situacao_adicional', '').strip() or None
    duracao_ponto = form_data.get('duracao_ponto', 'Médio')
    set_num = int(form_data.get('set_num', 1)) if form_data.get('set_num') else 1

    return {
        'sacador': sacador,
        'dupla_vencedora': dupla_vencedora,
        'atleta_finalizador': atleta_finalizador,
        'tipo_desfecho': tipo_desfecho,
        'tipo_golpe': tipo_golpe,
        'posicao_sacador': posicao_sacador,
        'direcao_saque': direcao_saque,
        'qualidade_saque': qualidade_saque,
        'saque_dificil': saque_dificil,
        'placar_texto': placar_texto,
        'situacao_adicional': situacao_adicional,
        'duracao_ponto': duracao_ponto,
        'set_num': set_num,
        'descricao_lance': descricao_lance,
    }


@admin_bp.route('/partidas/<int:id>/pontos/novo', methods=['POST'])
@admin_required
def partida_ponto_adicionar(id):
    """Adiciona um novo ponto / scout lance a lance na partida."""
    partida = db.get_or_404(Partida, id)
    numero = len(partida.pontos) + 1
    dados = _processar_dados_ponto(partida, request.form)

    # Coordenadas opcionais para o mapa de calor
    def parse_float(val, default):
        try:
            return float(val) if val is not None and val != '' else default
        except:
            return default

    origem_x = parse_float(request.form.get('origem_x'), 50.0)
    origem_y = parse_float(request.form.get('origem_y'), 75.0)
    destino_x = parse_float(request.form.get('destino_x'), 50.0)
    destino_y = parse_float(request.form.get('destino_y'), 25.0)

    ponto = PontoPartida(
        partida_id=partida.id,
        numero_ponto=numero,
        origem_x=origem_x,
        origem_y=origem_y,
        destino_x=destino_x,
        destino_y=destino_y,
        **dados
    )
    db.session.add(ponto)
    db.session.commit()
    flash(f'Ponto #{numero} registrado com sucesso!', 'success')
    return redirect(url_for('admin.partida_detalhes', id=partida.id))


@admin_bp.route('/partidas/pontos/<int:ponto_id>/editar', methods=['POST'])
@admin_required
def partida_ponto_editar(ponto_id):
    """O professor edita os dados de um ponto do scout."""
    ponto = db.get_or_404(PontoPartida, ponto_id)
    partida = ponto.partida
    dados = _processar_dados_ponto(partida, request.form)
    for chave, valor in dados.items():
        setattr(ponto, chave, valor)

    db.session.commit()
    flash(f'Ponto #{ponto.numero_ponto} atualizado com sucesso pelo professor!', 'success')
    return redirect(url_for('admin.partida_detalhes', id=partida.id))


@admin_bp.route('/partidas/pontos/<int:ponto_id>/excluir', methods=['POST'])
@admin_required
def partida_ponto_excluir(ponto_id):
    """Exclui um ponto específico da partida."""
    ponto = db.get_or_404(PontoPartida, ponto_id)
    partida_id = ponto.partida_id
    db.session.delete(ponto)
    db.session.commit()
    flash('Ponto removido com sucesso.', 'info')
    return redirect(url_for('admin.partida_detalhes', id=partida_id))


@admin_bp.route('/partidas/<int:id>/carregar-amostra-scout', methods=['POST'])
@admin_required
def partida_carregar_amostra(id):
    """Carrega na partida uma sequência rica e completa de pontos reais do BT Tracker."""
    partida = db.get_or_404(Partida, id)
    
    # Se já tiver pontos, não duplica a menos que solicitado
    if partida.pontos:
        PontoPartida.query.filter_by(partida_id=partida.id).delete()
        db.session.commit()

    # Base de pontos realistas baseados nas partidas do relatório BT Tracker
    amostra_pontos = [
        # (sacador, dupla_vencedora, finalizador, desfecho, golpe, pos_saque, dir_saque, qual_saque, dir_dev, qual_dev, placar, situacao, ox, oy, dx, dy, desc)
        (4, 1, 3, 'erro_nao_forcado', 'Smash', 'Esquerda', '2', 'Bom', 'No sacador', 'Boa', '0x0 15x0', None, 45, 60, 50, 15, 'Erro não forçado de Smash de Jogador 3'),
        (4, 2, 4, 'winner', 'Smash', 'Esquerda', '3', 'Bom', 'Meio', 'Regular', '0x0 15x15', None, 60, 80, 20, 25, 'Winner de Smash de Jogador 4'),
        (4, 2, 1, 'erro_nao_forcado', 'Avanço com Forehand', 'Esquerda', '4', 'Bom', 'No sacador', 'Regular', '0x0 15x30', None, 30, 20, 35, 95, 'Erro não forçado de Avanço de Jogador 1'),
        (4, 1, 4, 'erro_saque', None, 'Esquerda', '5', 'Erro', None, None, '0x0 30x30', None, 65, 85, 65, 45, 'Erro de Saque de Jogador 4'),
        (4, 1, 4, 'erro_saque', None, 'Esquerda', '3', 'Erro', None, None, '0x0 40x30', None, 65, 85, 50, 48, 'Erro de Saque de Jogador 4'),
        (4, 2, 4, 'winner', 'Gancho', 'Esquerda', '2', 'Bom', 'Lob', 'Regular', '0x0 40x40', 'Bola na Fita', 70, 75, 25, 20, 'Winner de Gancho de Jogador 4 [40x40 Decisivo]'),
        (4, 2, 4, 'forcou_erro', 'Lob Chutado com Forehand', 'Esquerda', '3', 'Bom', 'Meio', 'Ruim', '0x1', None, 50, 80, 80, 15, 'Jogador 4 forçou o erro com Lob Chutado'),

        (2, 2, 2, 'erro_saque', None, 'Direita', '1', 'Erro', None, None, '0x1 0x15', None, 35, 15, 35, 52, 'Erro de Saque de Jogador 2'),
        (2, 2, 2, 'erro_saque', None, 'Direita', '1', 'Erro', None, None, '0x1 0x30', None, 35, 15, 45, 53, 'Erro de Saque de Jogador 2'),
        (2, 2, 4, 'winner', 'Smash', 'Direita', '3', 'Regular', 'No sacador', 'Boa', '0x1 0x40', None, 65, 80, 30, 20, 'Winner de Smash de Jogador 4'),
        (2, 1, 4, 'erro_devolucao', None, 'Direita', '2', 'Bom', 'No sacador', 'Erro', '0x1 15x40', None, 40, 20, 70, 70, 'Erro de devolução de Jogador 4'),
        (2, 2, 4, 'forcou_erro', 'Smash', 'Direita', '3', 'Regular', 'Meio', 'Ruim', '0x2', None, 75, 75, 40, 25, 'Jogador 4 forçou o erro com Smash'),

        (3, 2, 4, 'winner', 'Smash', 'Direita', '3', 'Bom', 'No sacador', 'Regular', '0x2 0x15', None, 65, 80, 25, 15, 'Winner de Smash de Jogador 4'),
        (3, 2, 4, 'winner', 'Lob Chutado com Forehand', 'Direita', '3', 'Bom', 'Meio', 'Regular', '0x2 0x30', 'Bola na Linha', 70, 75, 20, 10, 'Winner de Lob Chutado de Jogador 4'),
        (3, 1, 2, 'winner', 'Lob Chutado com Backhand', 'Direita', '2', 'Regular', 'No sacador', 'Boa', '0x2 15x30', None, 40, 25, 80, 85, 'Winner de Lob Chutado de Jogador 2'),
        (3, 2, 2, 'erro_devolucao', None, 'Direita', '4', 'Bom', 'No parceiro', 'Erro', '0x2 15x40', 'Bola na Fita', 35, 85, 30, 30, 'Erro de devolução de Jogador 2'),
        (3, 1, 2, 'forcou_erro', 'Smash', 'Direita', '3', 'Regular', 'Meio', 'Regular', '0x2 30x40', None, 45, 30, 65, 80, 'Jogador 2 forçou erro com Smash'),
        (3, 2, 4, 'winner', 'Gancho', 'Direita', '3', 'Bom', 'No sacador', 'Regular', '0x3', None, 60, 75, 30, 15, 'Winner de Gancho de Jogador 4'),

        (1, 2, 3, 'winner', 'Curta com Forehand', 'Direita', '3', 'Regular', 'No sacador', 'Boa', '0x3 0x15', 'Bola na Linha', 30, 70, 45, 45, 'Winner de Curta de Jogador 3'),
        (1, 1, 1, 'ace', None, 'Direita', '4', 'Ace', None, None, '0x3 15x15', None, 30, 15, 75, 75, 'Ace no ângulo de Jogador 1'),
        (1, 2, 4, 'forcou_erro', 'Lob Chutado com Forehand', 'Direita', '2', 'Regular', 'Meio', 'Ruim', '0x3 15x30', None, 70, 80, 30, 20, 'Jogador 4 forçou o erro com Lob Chutado'),
        (1, 2, 3, 'winner', 'Devolução com Forehand', 'Direita', '3', 'Regular', 'No sacador', 'Winner', '0x3 15x40', None, 30, 70, 75, 20, 'Winner de Devolução de Jogador 3'),
        (1, 1, 4, 'erro_devolucao', None, 'Direita', '3', 'Bom', 'No sacador', 'Erro', '0x3 30x40', None, 40, 20, 65, 65, 'Erro de devolução de Jogador 4'),
        (1, 1, 3, 'erro_nao_forcado', 'Smash', 'Direita', '4', 'Bom', 'Meio', 'Regular', '0x3 40x40', 'Furou a bola', 35, 75, 40, 55, 'Erro não forçado de Smash de Jogador 3'),
        (1, 2, 1, 'erro_nao_forcado', 'Lob Chutado com Forehand', 'Direita', '3', 'Bom', 'No sacador', 'Regular', '0x4', None, 35, 25, 40, 95, 'Erro não forçado de Lob Chutado de Jogador 1'),

        (4, 2, 4, 'winner', 'Lob Chutado com Forehand', 'Esquerda', '3', 'Bom', 'Meio', 'Regular', '0x4 0x15', None, 65, 80, 25, 15, 'Winner de Lob Chutado de Jogador 4'),
        (4, 1, 4, 'erro_saque', None, 'Esquerda', '4', 'Erro', None, None, '0x4 15x15', None, 65, 85, 40, 45, 'Erro de Saque de Jogador 4'),
        (4, 1, 1, 'forcou_erro', 'Voleio estático com Forehand', 'Esquerda', '2', 'Regular', 'No sacador', 'Boa', '0x4 30x15', None, 40, 35, 60, 65, 'Jogador 1 forçou erro com Voleio Estático'),
        (4, 2, 3, 'forcou_erro', '1-2 Combination', 'Esquerda', '3', 'Bom', 'Meio', 'Ruim', '0x4 30x30', None, 35, 65, 30, 25, 'Jogador 3 forçou erro com 1-2 Combination'),
        (4, 1, 3, 'erro_nao_forcado', 'Curta com Forehand', 'Esquerda', '2', 'Bom', 'No sacador', 'Boa', '0x4 40x30', None, 40, 60, 45, 55, 'Erro não forçado de Curta de Jogador 3'),
        (4, 1, 1, 'forcou_erro', 'Smash', 'Esquerda', '3', 'Regular', 'Meio', 'Boa', '1x4', None, 35, 30, 65, 75, 'Jogador 1 forçou erro com Smash'),

        (2, 1, 1, 'winner', 'Smash', 'Direita', '3', 'Bom', 'Meio', 'Regular', '1x4 15x30', None, 35, 35, 65, 80, 'Winner de Smash de Jogador 1'),
        (2, 1, 4, 'erro_nao_forcado', 'Curta com Backhand', 'Direita', '2', 'Bom', 'No sacador', 'Regular', '1x4 30x30', None, 65, 70, 60, 52, 'Erro não forçado de Curta de Jogador 4'),
        (2, 1, 1, 'forcou_erro', 'Smash', 'Direita', '3', 'Bom', 'Meio', 'Regular', '1x4 40x30', None, 40, 30, 75, 75, 'Jogador 1 forçou erro com Smash'),
        (2, 2, 3, 'winner', 'Smash', 'Direita', '4', 'Regular', 'No sacador', 'Boa', '1x4 40x40', None, 35, 75, 35, 20, 'Winner de Smash de Jogador 3'),
        (2, 1, 1, 'forcou_erro', '1-2 Combination', 'Direita', '3', 'Bom', 'Meio', 'Regular', '2x4', None, 35, 35, 70, 70, 'Jogador 1 forçou o erro com 1-2 Combination'),

        (3, 1, 1, 'winner', 'Smash', 'Direita', '3', 'Regular', 'Meio', 'Boa', '2x4 15x0', None, 40, 30, 65, 75, 'Winner de Smash de Jogador 1'),
        (3, 1, 3, 'erro_saque', None, 'Direita', '2', 'Erro', None, None, '2x4 30x0', None, 35, 85, 50, 45, 'Erro de Saque de Jogador 3'),
        (3, 2, 2, 'erro_devolucao', None, 'Direita', '3', 'Bom', 'No sacador', 'Erro', '2x4 30x15', None, 45, 20, 35, 85, 'Erro de devolução de Jogador 2'),
        (3, 1, 3, 'erro_saque', None, 'Direita', '4', 'Erro', None, None, '2x4 40x15', None, 35, 85, 30, 45, 'Erro de Saque de Jogador 3'),
        (3, 2, 4, 'winner', 'Lob Chutado com Forehand', 'Direita', '3', 'Bom', 'Meio', 'Regular', '2x4 40x30', None, 70, 80, 25, 15, 'Winner de Lob Chutado de Jogador 4'),
        (3, 1, 3, 'erro_nao_forcado', 'Lob Chutado com Forehand', 'Direita', '3', 'Bom', 'Meio', 'Regular', '3x4', None, 35, 75, 35, 5, 'Erro não forçado de Lob Chutado de Jogador 3'),
    ]

    for idx, pt in enumerate(amostra_pontos, start=1):
        ponto = PontoPartida(
            partida_id=partida.id,
            numero_ponto=idx,
            sacador=pt[0],
            dupla_vencedora=pt[1],
            atleta_finalizador=pt[2],
            tipo_desfecho=pt[3],
            tipo_golpe=pt[4],
            posicao_sacador=pt[5],
            direcao_saque=pt[6],
            qualidade_saque=pt[7],
            direcao_devolucao=pt[8],
            qualidade_devolucao=pt[9],
            placar_texto=pt[10],
            situacao_adicional=pt[11],
            origem_x=pt[12],
            origem_y=pt[13],
            destino_x=pt[14],
            destino_y=pt[15],
            descricao_lance=pt[16],
            duracao_ponto='Curto' if pt[3] in ['ace', 'erro_saque'] else ('Longo' if 'Lob' in str(pt[4]) else 'Médio')
        )
        db.session.add(ponto)

    # Atualiza placar da partida para refletir a amostra
    partida.set1_dupla1 = 4
    partida.set1_dupla2 = 6
    partida.set2_dupla1 = 3
    partida.set2_dupla2 = 6
    partida.placar_detalhado = "4x6 | 3x6"
    partida.dupla_vencedora = 2

    db.session.commit()
    flash('Amostra oficial de scout (BT Insight) carregada com sucesso!', 'success')
    return redirect(url_for('admin.partida_detalhes', id=partida.id))

