import json
from datetime import datetime, date, timedelta
from app.models.avaliacao import CRITERIOS_AVALIACAO
from app.models.categoria import categoria_label as _categoria_label
from app.models import Aula, Presenca


def _badge_por_diferenca(diff):
    """Símbolo, sinal e classes visuais para uma variação numérica."""
    if diff > 0:
        return {
            'simbolo': '↑',
            'classe': 'text-success',
            'badge_bg': 'bg-success',
            'sinal': f'+{diff}',
        }
    if diff < 0:
        return {
            'simbolo': '↓',
            'classe': 'text-danger',
            'badge_bg': 'bg-danger',
            'sinal': f'{diff}',
        }
    return {
        'simbolo': '=',
        'classe': 'text-muted',
        'badge_bg': 'bg-secondary',
        'sinal': '0.0',
    }


def get_aluno_analytics(aluno):
    """
    Calcula todas as métricas analíticas e datasets formatados para Chart.js
    do perfil de um aluno (radar comparativo, linha de evolução e barras de frequência).

    Além da nota bruta (relativa à categoria de cada ciclo), o retorno traz o
    **Índice Técnico** (0 a 100), que corrige a diferença de dificuldade entre as
    categorias. Assim, uma promoção D → C pode derrubar a nota bruta sem apagar a
    curva de aprendizado do atleta.
    """
    # 1. Avaliações em ordem cronológica crescente
    avaliacoes_cron = sorted(aluno.avaliacoes, key=lambda a: (a.data, a.id))
    tem_avaliacoes = len(avaliacoes_cron) > 0

    criterios_keys = [k for k, _ in CRITERIOS_AVALIACAO]
    criterios_labels = [label for _, label in CRITERIOS_AVALIACAO]

    primeira_aval = avaliacoes_cron[0] if tem_avaliacoes else None
    ultima_aval = avaliacoes_cron[-1] if tem_avaliacoes else None
    penultima_aval = avaliacoes_cron[-2] if len(avaliacoes_cron) > 1 else None

    primeira_scores = [primeira_aval.get_nota(k) or 0 for k in criterios_keys] if primeira_aval else []
    ultima_scores = [ultima_aval.get_nota(k) or 0 for k in criterios_keys] if ultima_aval else []

    # Linha do tempo de evolução (nota bruta e índice técnico)
    linha_datas = [a.data.strftime('%d/%m/%Y') for a in avaliacoes_cron]
    linha_datas_curtas = [a.data.strftime('%d/%m/%y') for a in avaliacoes_cron]
    linha_categorias = [a.categoria_curta for a in avaliacoes_cron]
    linha_categorias_label = [a.categoria_label for a in avaliacoes_cron]
    linha_pesos = [a.peso_categoria for a in avaliacoes_cron]
    linha_medias = [a.media for a in avaliacoes_cron]
    linha_indices = [a.indice_tecnico for a in avaliacoes_cron]
    linha_labels = [
        f"{data} · {cat}" for data, cat in zip(linha_datas_curtas, linha_categorias)
    ]

    criterios_timeline = {
        k: [a.get_nota(k) or 0 for a in avaliacoes_cron]
        for k in criterios_keys
    }
    criterios_timeline_indice = {
        k: [a.get_indice(k) or 0 for a in avaliacoes_cron]
        for k in criterios_keys
    }

    # Mudanças de categoria ao longo da trajetória (promoções ou reclassificações)
    promocoes = []
    for indice, atual in enumerate(avaliacoes_cron):
        if indice == 0:
            continue
        anterior = avaliacoes_cron[indice - 1]
        if anterior.categoria_curta == atual.categoria_curta:
            continue
        promocoes.append({
            'indice': indice,
            'data': atual.data,
            'data_anterior': anterior.data,
            'de': anterior.categoria_curta,
            'para': atual.categoria_curta,
            'de_label': anterior.categoria_label,
            'para_label': atual.categoria_label,
            'subiu': atual.ordem_categoria > anterior.ordem_categoria,
            'media_antes': anterior.media,
            'media_depois': atual.media,
            'delta_media': round(atual.media - anterior.media, 1),
            'indice_antes': anterior.indice_tecnico,
            'indice_depois': atual.indice_tecnico,
            'delta_indice': round(atual.indice_tecnico - anterior.indice_tecnico, 1),
        })

    # Comparativo detalhado por critério (nota bruta + índice corrigido)
    comparativo_criterios = []
    if tem_avaliacoes:
        for k, label in CRITERIOS_AVALIACAO:
            n_atual = ultima_aval.get_nota(k) or 0
            n_inicial = primeira_aval.get_nota(k) or 0
            i_atual = ultima_aval.get_indice(k) or 0
            i_inicial = primeira_aval.get_indice(k) or 0
            diff = round(n_atual - n_inicial, 1)
            diff_indice = round(i_atual - i_inicial, 1)

            visual = _badge_por_diferenca(diff)
            visual_indice = _badge_por_diferenca(diff_indice)

            comparativo_criterios.append({
                'chave': k,
                'label': label,
                'nota_inicial': n_inicial,
                'nota_atual': n_atual,
                'indice_inicial': i_inicial,
                'indice_atual': i_atual,
                'diff': diff,
                'diff_indice': diff_indice,
                'sinal': visual['sinal'],
                'simbolo': visual['simbolo'],
                'classe': visual['classe'],
                'badge_bg': visual['badge_bg'],
                'sinal_indice': visual_indice['sinal'],
                'simbolo_indice': visual_indice['simbolo'],
                'badge_bg_indice': visual_indice['badge_bg'],
            })

    # Resumo geral: nota bruta (pode cair na promoção) e índice corrigido
    media_inicial = primeira_aval.media if primeira_aval else 0.0
    media_atual = ultima_aval.media if ultima_aval else 0.0
    indice_inicial = primeira_aval.indice_tecnico if primeira_aval else 0.0
    indice_atual = ultima_aval.indice_tecnico if ultima_aval else 0.0
    diff_geral = round(media_atual - media_inicial, 1) if (primeira_aval and ultima_aval) else 0.0
    diff_indice = round(indice_atual - indice_inicial, 1) if (primeira_aval and ultima_aval) else 0.0

    categoria_inicial = primeira_aval.categoria_efetiva if primeira_aval else aluno.categoria_efetiva
    categoria_atual = ultima_aval.categoria_efetiva if ultima_aval else aluno.categoria_efetiva
    categorias_presentes = []
    for cat in linha_categorias:
        if cat not in categorias_presentes:
            categorias_presentes.append(cat)
    tem_multiplas_categorias = len(categorias_presentes) > 1

    # 2. Frequência Mensal (Últimos 6 meses)
    hoje = date.today()
    meses_info = []
    # Gera os últimos 6 meses (do mais antigo ao atual)
    for i in range(5, -1, -1):
        # Calcula primeiro dia do mês i meses atrás
        ano = hoje.year
        mes = hoje.month - i
        while mes <= 0:
            mes += 12
            ano -= 1

        primeiro_dia = date(ano, mes, 1)
        if mes == 12:
            ultimo_dia = date(ano + 1, 1, 1) - timedelta(days=1)
        else:
            ultimo_dia = date(ano, mes + 1, 1) - timedelta(days=1)

        nome_mes = primeiro_dia.strftime('%b/%y').capitalize()
        meses_info.append({
            'inicio': datetime.combine(primeiro_dia, datetime.min.time()),
            'fim': datetime.combine(ultimo_dia, datetime.max.time()),
            'label': nome_mes
        })

    presencas_aluno = (Presenca.query.filter_by(aluno_id=aluno.id)
                       .join(Aula)
                       .all())

    frequencia_labels = []
    frequencia_presentes = []
    frequencia_faltas = []
    frequencia_justificadas = []

    for m in meses_info:
        frequencia_labels.append(m['label'])
        pres_mes = [p for p in presencas_aluno if p.aula and m['inicio'] <= p.aula.data_hora <= m['fim']]

        qtd_presente = sum(1 for p in pres_mes if p.status in ('presente', 'reposicao'))
        qtd_falta = sum(1 for p in pres_mes if p.status == 'falta')
        qtd_justificada = sum(1 for p in pres_mes if p.status in ('falta_justificada', 'ausencia_avisada'))

        frequencia_presentes.append(qtd_presente)
        frequencia_faltas.append(qtd_falta)
        frequencia_justificadas.append(qtd_justificada)

    return {
        'tem_avaliacoes': tem_avaliacoes,
        'total_avaliacoes': len(avaliacoes_cron),
        'primeira_avaliacao': primeira_aval,
        'ultima_avaliacao': ultima_aval,
        'penultima_avaliacao': penultima_aval,
        'media_inicial': media_inicial,
        'media_atual': media_atual,
        'indice_inicial': indice_inicial,
        'indice_atual': indice_atual,
        'diff_geral': diff_geral,
        'diff_indice': diff_indice,
        'categoria_inicial': categoria_inicial,
        'categoria_atual': categoria_atual,
        'categoria_inicial_label': _categoria_label(categoria_inicial),
        'categoria_atual_label': _categoria_label(categoria_atual),
        'categorias_presentes': categorias_presentes,
        'tem_multiplas_categorias': tem_multiplas_categorias,
        'promocoes': promocoes,
        'comparativo_criterios': comparativo_criterios,
        'linha_medias': linha_medias,
        'linha_indices': linha_indices,
        'linha_categorias': linha_categorias,
        # JSONs para Chart.js
        'criterios_labels_json': json.dumps(criterios_labels),
        'primeira_scores_json': json.dumps(primeira_scores),
        'ultima_scores_json': json.dumps(ultima_scores),
        'linha_datas_json': json.dumps(linha_datas),
        'linha_labels_json': json.dumps(linha_labels),
        'linha_categorias_json': json.dumps(linha_categorias),
        'linha_categorias_label_json': json.dumps(linha_categorias_label),
        'linha_pesos_json': json.dumps(linha_pesos),
        'linha_medias_json': json.dumps(linha_medias),
        'linha_indices_json': json.dumps(linha_indices),
        'promocoes_json': json.dumps([
            {'indice': p['indice'], 'de': p['de'], 'para': p['para']}
            for p in promocoes
        ]),
        'criterios_timeline_json': json.dumps(criterios_timeline),
        'criterios_timeline_indice_json': json.dumps(criterios_timeline_indice),
        'frequencia_labels_json': json.dumps(frequencia_labels),
        'frequencia_presentes_json': json.dumps(frequencia_presentes),
        'frequencia_faltas_json': json.dumps(frequencia_faltas),
        'frequencia_justificadas_json': json.dumps(frequencia_justificadas),
    }
