import re
from datetime import datetime, date, timedelta
from flask import Blueprint, render_template, redirect, url_for, flash, request, abort, Response
from flask_login import current_user
from app.extensions import db
from app.models import (Aluno, Turma, TurmaAluno, Aula, AulaExercicio,
                        Presenca, Avaliacao, MetaAluno, Exercicio, Partida, PontoPartida)
from app.models.exercicio import CATEGORIAS_EXERCICIO, NIVEIS_EXERCICIO
from app.utils.decorators import aluno_required
from app.utils.analytics import get_aluno_analytics
from app.utils.pdf_generator import gerar_relatorio_pdf_aluno
from app.utils.bt_tracker import calcular_estatisticas_partida
from app.utils.bt_tracker_pdf import gerar_pdf_bt_tracker
from app.utils.schema_migration import garantir_esquema_banco
from .forms import AlunoPartidaForm, AlterarSenhaForm

aluno_bp = Blueprint('aluno', __name__)


def get_current_aluno():
    aluno = current_user.aluno
    if not aluno or not aluno.ativo:
        flash('Perfil de aluno não encontrado ou inativo.', 'warning')
        abort(403)
    return aluno


@aluno_bp.route('/painel')
@aluno_required
def painel():
    """
    Painel Principal do Aluno:
    Próxima aula com exercícios planejados, presença, metas, evolução rápida e feedbacks.
    """
    aluno = get_current_aluno()
    
    # Turmas ativas do aluno
    turma_ids = [ta.turma_id for ta in aluno.turmas if ta.ativo]
    
    # Próxima aula programada
    agora = datetime.now()
    proxima_aula = None
    presenca_proxima = None
    exercicios_aula = []
    
    if turma_ids:
        proxima_aula = (Aula.query
                        .filter(Aula.turma_id.in_(turma_ids),
                                Aula.data_hora >= agora,
                                Aula.status == 'agendada')
                        .order_by(Aula.data_hora.asc())
                        .first())
        if proxima_aula:
            presenca_proxima = Presenca.query.filter_by(aula_id=proxima_aula.id, aluno_id=aluno.id).first()
            exercicios_aula = (AulaExercicio.query
                               .filter_by(aula_id=proxima_aula.id)
                               .order_by(AulaExercicio.ordem.asc())
                               .all())

    # Presenças recentes
    presencas_recentes = (Presenca.query.filter_by(aluno_id=aluno.id)
                          .join(Aula)
                          .order_by(Aula.data_hora.desc())
                          .limit(5)
                          .all())
    
    # Cálculo rápido de frequência geral
    total_chamadas = Presenca.query.filter_by(aluno_id=aluno.id).count()
    total_presentes = Presenca.query.filter_by(aluno_id=aluno.id).filter(Presenca.status.in_(['presente', 'reposicao'])).count()
    taxa_frequencia = round((total_presentes / total_chamadas * 100), 1) if total_chamadas > 0 else 100.0

    # Metas e Analytics
    metas = aluno.metas[:4]
    analytics = get_aluno_analytics(aluno)

    return render_template('aluno/painel.html',
        aluno=aluno,
        proxima_aula=proxima_aula,
        presenca_proxima=presenca_proxima,
        exercicios_aula=exercicios_aula,
        presencas_recentes=presencas_recentes,
        taxa_frequencia=taxa_frequencia,
        total_chamadas=total_chamadas,
        total_presentes=total_presentes,
        metas=metas,
        analytics=analytics
    )


@aluno_bp.route('/aulas')
@aluno_required
def aulas():
    """
    Minhas Aulas: Próximas aulas com confirmação de presença e histórico completo.
    """
    aluno = get_current_aluno()
    turma_ids = [ta.turma_id for ta in aluno.turmas if ta.ativo]
    agora = datetime.now()

    aulas_futuras = []
    if turma_ids:
        aulas_query = (Aula.query
                       .filter(Aula.turma_id.in_(turma_ids),
                               Aula.data_hora >= agora,
                               Aula.status != 'cancelada')
                       .order_by(Aula.data_hora.asc())
                       .limit(10)
                       .all())
        
        # Mapeia presenças existentes para aulas futuras
        for af in aulas_query:
            p = Presenca.query.filter_by(aula_id=af.id, aluno_id=aluno.id).first()
            aulas_futuras.append({
                'aula': af,
                'presenca': p
            })

    # Histórico de aulas passadas
    historico = (Presenca.query.filter_by(aluno_id=aluno.id)
                 .join(Aula)
                 .order_by(Aula.data_hora.desc())
                 .limit(50)
                 .all())

    analytics = get_aluno_analytics(aluno)

    return render_template('aluno/aulas.html',
        aluno=aluno,
        aulas_futuras=aulas_futuras,
        historico=historico,
        analytics=analytics
    )


@aluno_bp.route('/aulas/<int:id>/confirmar', methods=['POST'])
@aluno_required
def confirmar_presenca(id):
    """
    O aluno confirma presença com antecedência para uma aula futura.
    """
    aluno = get_current_aluno()
    aula = db.get_or_404(Aula, id)

    # Verifica se aluno pertence à turma
    matriculado = any(ta.turma_id == aula.turma_id and ta.ativo for ta in aluno.turmas)
    if not matriculado:
        flash('Você não está matriculado na turma desta aula.', 'danger')
        return redirect(url_for('aluno.painel'))

    presenca = Presenca.query.filter_by(aula_id=aula.id, aluno_id=aluno.id).first()
    if presenca:
        presenca.status = 'confirmado'
        presenca.justificativa = None
        presenca.registrado_em = datetime.utcnow()
    else:
        presenca = Presenca(
            aula_id=aula.id,
            aluno_id=aluno.id,
            status='confirmado',
            registrado_em=datetime.utcnow()
        )
        db.session.add(presenca)

    db.session.commit()
    data_fmt = aula.data_hora.strftime('%d/%m às %H:%M')
    flash(f'Presença confirmada para a aula de {data_fmt}! O professor já foi notificado.', 'success')
    
    origem = request.form.get('origem', 'painel')
    if origem == 'aulas':
        return redirect(url_for('aluno.aulas'))
    return redirect(url_for('aluno.painel'))


@aluno_bp.route('/aulas/<int:id>/avisar-ausencia', methods=['POST'])
@aluno_required
def avisar_ausencia(id):
    """
    O aluno avisa ausência informando o motivo para o professor.
    """
    aluno = get_current_aluno()
    aula = db.get_or_404(Aula, id)
    motivo = request.form.get('motivo', '').strip()

    matriculado = any(ta.turma_id == aula.turma_id and ta.ativo for ta in aluno.turmas)
    if not matriculado:
        flash('Você não está matriculado na turma desta aula.', 'danger')
        return redirect(url_for('aluno.painel'))

    presenca = Presenca.query.filter_by(aula_id=aula.id, aluno_id=aluno.id).first()
    if presenca:
        presenca.status = 'ausencia_avisada'
        presenca.justificativa = motivo or 'Ausência avisada pelo aluno'
        presenca.registrado_em = datetime.utcnow()
    else:
        presenca = Presenca(
            aula_id=aula.id,
            aluno_id=aluno.id,
            status='ausencia_avisada',
            justificativa=motivo or 'Ausência avisada pelo aluno',
            registrado_em=datetime.utcnow()
        )
        db.session.add(presenca)

    db.session.commit()
    data_fmt = aula.data_hora.strftime('%d/%m às %H:%M')
    flash(f'Aviso de ausência na aula de {data_fmt} registrado. Obrigado por avisar!', 'info')
    
    origem = request.form.get('origem', 'painel')
    if origem == 'aulas':
        return redirect(url_for('aluno.aulas'))
    return redirect(url_for('aluno.painel'))


@aluno_bp.route('/evolucao')
@aluno_required
def evolucao():
    """
    Tela Completa de Evolução do Aluno:
    Gráficos radar, linha do tempo por critério, tabela comparativa com setas, pareceres e vídeos.
    """
    aluno = get_current_aluno()
    analytics = get_aluno_analytics(aluno)
    
    return render_template('aluno/evolucao.html',
        aluno=aluno,
        analytics=analytics
    )


@aluno_bp.route('/exercicios')
@aluno_required
def exercicios():
    """
    Biblioteca de Exercícios Liberados para Treino em Casa / Complementar.
    """
    aluno = get_current_aluno()
    categoria = request.args.get('categoria', '').strip()
    nivel = request.args.get('nivel', '').strip()
    busca = request.args.get('busca', '').strip()

    query = Exercicio.query.filter_by(ativo=True)
    if categoria:
        query = query.filter_by(categoria=categoria)
    if nivel:
        query = query.filter_by(nivel=nivel)
    if busca:
        query = query.filter(db.or_(
            Exercicio.titulo.ilike(f'%{busca}%'),
            Exercicio.objetivo_tecnico.ilike(f'%{busca}%'),
            Exercicio.descricao.ilike(f'%{busca}%')
        ))

    exercicios_lista = query.order_by(Exercicio.titulo.asc()).all()

    return render_template('aluno/exercicios.html',
        aluno=aluno,
        exercicios=exercicios_lista,
        categorias=CATEGORIAS_EXERCICIO,
        niveis=NIVEIS_EXERCICIO,
        categoria_sel=categoria,
        nivel_sel=nivel,
        busca=busca
    )


@aluno_bp.route('/relatorio-pdf')
@aluno_required
def relatorio_pdf():
    """O aluno exporta seu próprio relatório completo de progresso em PDF."""
    aluno = get_current_aluno()
    analytics = get_aluno_analytics(aluno)
    pdf_bytes = gerar_relatorio_pdf_aluno(aluno, analytics)

    nome_slug = re.sub(r'[^a-zA-Z0-9]+', '_', aluno.nome.lower()).strip('_')
    nome_arquivo = f"relatorio_{nome_slug}_{date.today().strftime('%Y-%m-%d')}.pdf"

    return Response(
        pdf_bytes,
        mimetype='application/pdf',
        headers={'Content-Disposition': f'attachment; filename="{nome_arquivo}"'}
    )


# ── MEU PERFIL & ALTERAR SENHA ─────────────────────────────────────────────
@aluno_bp.route('/perfil', methods=['GET', 'POST'], endpoint='perfil')
@aluno_bp.route('/alterar-senha', methods=['GET', 'POST'], endpoint='alterar_senha')
@aluno_required
def perfil():
    """
    Tela de Perfil e Alteração de Senha do Aluno.
    Permite visualizar os dados cadastrais do atleta e atualizar a senha com validação.
    """
    aluno = get_current_aluno()
    form = AlterarSenhaForm()

    if form.validate_on_submit():
        senha_atual = form.senha_atual.data.strip()
        nova_senha = form.nova_senha.data.strip()

        if not current_user.check_senha(senha_atual):
            flash('Senha atual incorreta. Por favor, digite sua senha atual corretamente.', 'danger')
        elif senha_atual == nova_senha:
            flash('A nova senha deve ser diferente da senha atual.', 'warning')
        else:
            current_user.set_senha(nova_senha)
            db.session.commit()
            flash('Sua senha foi alterada com sucesso! Utilize a nova senha em seus próximos acessos.', 'success')
            return redirect(url_for('aluno.perfil'))

    return render_template('aluno/perfil.html', aluno=aluno, form=form)


# ── BT INSIGHT DO ALUNO ───────────────────────────────────────────────────
@aluno_bp.route('/partidas')
@aluno_required
def partidas_lista():
    """Visualização das partidas e scouts (BT Insight) do aluno."""
    aluno = get_current_aluno()

    def _buscar_partidas():
        pts = Partida.query.filter(
            db.or_(
                Partida.criada_por_aluno_id == aluno.id,
                Partida.jogador1_aluno_id == aluno.id,
                Partida.jogador2_aluno_id == aluno.id,
                Partida.jogador3_aluno_id == aluno.id,
                Partida.jogador4_aluno_id == aluno.id,
                Partida.jogador1_nome.ilike(f"%{aluno.nome}%"),
                Partida.jogador2_nome.ilike(f"%{aluno.nome}%"),
                Partida.jogador3_nome.ilike(f"%{aluno.nome}%"),
                Partida.jogador4_nome.ilike(f"%{aluno.nome}%"),
            )
        ).order_by(Partida.data.desc(), Partida.id.desc()).all()

        return pts

    try:
        partidas = _buscar_partidas()
        return render_template('aluno/partidas.html', aluno=aluno, partidas=partidas)
    except Exception:
        db.session.rollback()
        try:
            garantir_esquema_banco()
            partidas = _buscar_partidas()
            return render_template('aluno/partidas.html', aluno=aluno, partidas=partidas)
        except Exception:
            db.session.rollback()
            return render_template('aluno/partidas.html', aluno=aluno, partidas=[])


@aluno_bp.route('/partidas/nova', methods=['GET', 'POST'])
@aluno_required
def partida_nova():
    """O aluno cadastra uma nova partida para avaliação do professor."""
    aluno = get_current_aluno()
    form = AlunoPartidaForm()

    if form.validate_on_submit():
        partida = Partida(
            titulo=form.titulo.data.strip(),
            data=form.data.data,
            torneio=form.torneio.data.strip() if form.torneio.data else 'Treino Competitivo',
            categoria=form.categoria.data,
            fase=form.fase.data.strip() if form.fase.data else 'Treino',
            local=form.local.data.strip() if form.local.data else 'Arena Itabuna',
            # O aluno que cadastra é o Jogador 1 da Dupla 1
            jogador1_nome=aluno.nome,
            jogador1_aluno_id=aluno.id,
            jogador2_nome=form.parceiro_nome.data.strip(),
            jogador3_nome=form.jogador3_nome.data.strip(),
            jogador4_nome=form.jogador4_nome.data.strip(),
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
            # Status: PENDENTE de validação do professor
            status='pendente',
            criada_por_aluno_id=aluno.id
        )
        db.session.add(partida)
        db.session.commit()
        flash('Partida registrada com sucesso! Ela foi enviada para validação e correções do professor Everson.', 'success')
        return redirect(url_for('aluno.partidas_lista'))

    return render_template('aluno/partida_form.html', aluno=aluno, form=form)


@aluno_bp.route('/partidas/<int:id>')
@aluno_required
def partida_detalhes(id):
    """Visualização da análise da partida pelo aluno no formato BT Insight."""
    aluno = get_current_aluno()
    partida = db.get_or_404(Partida, id)

    # Validação de autorização do aluno
    is_participante = (
        partida.criada_por_aluno_id == aluno.id or
        partida.jogador1_aluno_id == aluno.id or
        partida.jogador2_aluno_id == aluno.id or
        partida.jogador3_aluno_id == aluno.id or
        partida.jogador4_aluno_id == aluno.id or
        (aluno.nome.lower() in (partida.jogador1_nome or '').lower()) or
        (aluno.nome.lower() in (partida.jogador2_nome or '').lower()) or
        (aluno.nome.lower() in (partida.jogador3_nome or '').lower()) or
        (aluno.nome.lower() in (partida.jogador4_nome or '').lower())
    )
    if not is_participante and partida.status != 'aprovada':
        flash('Você não tem permissão para visualizar esta partida.', 'danger')
        return redirect(url_for('aluno.partidas_lista'))

    stats = calcular_estatisticas_partida(partida)
    return render_template('aluno/partida_detalhes.html', aluno=aluno, partida=partida, stats=stats)


@aluno_bp.route('/partidas/<int:id>/pdf')
@aluno_required
def partida_pdf(id):
    """Download do relatório oficial em PDF da partida (BT Insight)."""
    aluno = get_current_aluno()
    partida = db.get_or_404(Partida, id)

    is_participante = (
        partida.criada_por_aluno_id == aluno.id or
        partida.jogador1_aluno_id == aluno.id or
        partida.jogador2_aluno_id == aluno.id or
        partida.jogador3_aluno_id == aluno.id or
        partida.jogador4_aluno_id == aluno.id or
        (aluno.nome.lower() in (partida.jogador1_nome or '').lower()) or
        (aluno.nome.lower() in (partida.jogador2_nome or '').lower()) or
        (aluno.nome.lower() in (partida.jogador3_nome or '').lower()) or
        (aluno.nome.lower() in (partida.jogador4_nome or '').lower())
    )
    if not is_participante and partida.status != 'aprovada':
        flash('Você não tem permissão para exportar esta partida.', 'danger')
        return redirect(url_for('aluno.partidas_lista'))

    pdf_bytes = gerar_pdf_bt_tracker(partida)

    nome_arquivo = f"BT_Insight_{partida.id}_{date.today().strftime('%Y-%m-%d')}.pdf"
    return Response(
        pdf_bytes,
        mimetype='application/pdf',
        headers={'Content-Disposition': f'attachment; filename="{nome_arquivo}"'}
    )


@aluno_bp.route('/partidas/<int:id>/pontos/novo', methods=['POST'])
@aluno_required
def partida_ponto_adicionar(id):
    """O aluno lança um novo ponto no scout de sua partida."""
    aluno = get_current_aluno()
    partida = db.get_or_404(Partida, id)

    # Verifica se o aluno tem relação com a partida
    is_autor = (partida.criada_por_aluno_id == aluno.id or
                partida.jogador1_aluno_id == aluno.id or
                partida.jogador2_aluno_id == aluno.id)
    if not is_autor:
        flash('Você não tem permissão para lançar pontos nesta partida.', 'danger')
        return redirect(url_for('aluno.partidas_lista'))

    from app.blueprints.admin.routes import _processar_dados_ponto
    numero = len(partida.pontos) + 1
    dados = _processar_dados_ponto(partida, request.form)

    ponto = PontoPartida(
        partida_id=partida.id,
        numero_ponto=numero,
        **dados
    )
    db.session.add(ponto)
    db.session.commit()
    flash(f'Ponto #{numero} registrado com sucesso!', 'success')
    return redirect(url_for('aluno.partida_detalhes', id=partida.id))


@aluno_bp.route('/partidas/pontos/<int:ponto_id>/editar', methods=['POST'])
@aluno_required
def partida_ponto_editar(ponto_id):
    """O aluno edita um ponto no scout de sua partida."""
    aluno = get_current_aluno()
    ponto = db.get_or_404(PontoPartida, ponto_id)
    partida = ponto.partida

    is_autor = (partida.criada_por_aluno_id == aluno.id or
                partida.jogador1_aluno_id == aluno.id or
                partida.jogador2_aluno_id == aluno.id)
    if not is_autor:
        flash('Você não tem permissão para editar pontos nesta partida.', 'danger')
        return redirect(url_for('aluno.partidas_lista'))

    from app.blueprints.admin.routes import _processar_dados_ponto
    dados = _processar_dados_ponto(partida, request.form)
    for chave, valor in dados.items():
        setattr(ponto, chave, valor)

    db.session.commit()
    flash(f'Ponto #{ponto.numero_ponto} atualizado com sucesso!', 'success')
    return redirect(url_for('aluno.partida_detalhes', id=partida.id))


@aluno_bp.route('/partidas/pontos/<int:ponto_id>/excluir', methods=['POST'])
@aluno_required
def partida_ponto_excluir(ponto_id):
    """O aluno remove um ponto do scout de sua partida."""
    aluno = get_current_aluno()
    ponto = db.get_or_404(PontoPartida, ponto_id)
    partida = ponto.partida

    is_autor = (partida.criada_por_aluno_id == aluno.id or
                partida.jogador1_aluno_id == aluno.id or
                partida.jogador2_aluno_id == aluno.id)
    if not is_autor:
        flash('Você não tem permissão para remover pontos desta partida.', 'danger')
        return redirect(url_for('aluno.partidas_lista'))

    db.session.delete(ponto)
    db.session.commit()
    flash('Ponto removido com sucesso.', 'info')
    return redirect(url_for('aluno.partida_detalhes', id=partida.id))

