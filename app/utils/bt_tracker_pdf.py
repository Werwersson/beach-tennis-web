import io
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import (SimpleDocTemplate, Paragraph, Spacer, Table,
                                TableStyle, PageBreak, KeepTogether)
from .bt_tracker import calcular_estatisticas_partida


def gerar_pdf_bt_tracker(partida):
    """
    Gera um relatório completo em PDF no padrão BT Tracker,
    seguindo o design oficial: Capa, Detalhes da Partida, Estatísticas Gerais,
    Estatísticas por Atleta e Linha do Tempo Ponto a Ponto.
    """
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        leftMargin=36,
        rightMargin=36,
        topMargin=36,
        bottomMargin=36
    )

    styles = getSampleStyleSheet()
    primary_color = colors.HexColor('#0F172A')
    ocean_blue = colors.HexColor('#0284C7')
    green_accent = colors.HexColor('#10B981')
    red_accent = colors.HexColor('#EF4444')
    gray_muted = colors.HexColor('#64748B')
    light_bg = colors.HexColor('#F8FAFC')
    border_color = colors.HexColor('#E2E8F0')

    # Estilos customizados
    title_cover = ParagraphStyle(
        'CoverTitle',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=36,
        leading=42,
        alignment=1,
        textColor=primary_color,
        spaceAfter=15
    )

    subtitle_cover = ParagraphStyle(
        'CoverSubtitle',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=18,
        leading=24,
        alignment=1,
        textColor=primary_color,
        spaceAfter=50
    )

    brand_title = ParagraphStyle(
        'BrandTitle',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=42,
        leading=48,
        alignment=1,
        textColor=primary_color,
        spaceAfter=10
    )

    brand_slogan = ParagraphStyle(
        'BrandSlogan',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=13,
        leading=16,
        alignment=1,
        textColor=primary_color,
        spaceAfter=30
    )

    h1_style = ParagraphStyle(
        'SectionH1',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=20,
        leading=24,
        textColor=primary_color,
        spaceAfter=12
    )

    h2_style = ParagraphStyle(
        'SectionH2',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=13,
        leading=16,
        textColor=primary_color,
        spaceAfter=8
    )

    text_center = ParagraphStyle(
        'TextCenter',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=9,
        leading=12,
        alignment=1,
        textColor=primary_color
    )

    text_bold_center = ParagraphStyle(
        'TextBoldCenter',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=9,
        leading=12,
        alignment=1,
        textColor=primary_color
    )

    text_left = ParagraphStyle(
        'TextLeft',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=9,
        leading=12,
        alignment=0,
        textColor=primary_color
    )

    text_bold_left = ParagraphStyle(
        'TextBoldLeft',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=9,
        leading=12,
        alignment=0,
        textColor=primary_color
    )

    badge_fita = ParagraphStyle(
        'BadgeFita',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=7,
        leading=9,
        textColor=colors.white,
        alignment=1
    )

    elements = []
    stats = calcular_estatisticas_partida(partida)

    # ──────────────────────────────────────────────────────────────────────────
    # PÁGINA 1: CAPA
    # ──────────────────────────────────────────────────────────────────────────
    elements.append(Spacer(1, 120))
    elements.append(Paragraph("Olá!", title_cover))
    elements.append(Spacer(1, 10))
    elements.append(Paragraph("O relatório do seu jogo chegou!", subtitle_cover))
    elements.append(Spacer(1, 80))
    elements.append(Paragraph("BT INSIGHT", brand_title))
    elements.append(Paragraph("O SEU OLHAR FORA DA QUADRA", brand_slogan))
    elements.append(Spacer(1, 60))
    elements.append(Paragraph(f"<b>Partida:</b> {partida.dupla1_label} vs {partida.dupla2_label}", text_center))
    elements.append(Paragraph(f"<b>Torneio:</b> {partida.torneio or 'Circuito AIBT'} | <b>Categoria:</b> {partida.categoria or 'Masculina B'}", text_center))
    elements.append(Paragraph(f"<b>Data:</b> {partida.data.strftime('%d/%m/%Y')} | <b>Placar:</b> {partida.placar_resumo}", text_center))
    elements.append(PageBreak())

    # ──────────────────────────────────────────────────────────────────────────
    # PÁGINA 2: DETALHES DA PARTIDA & ESTATÍSTICAS GERAIS
    # ──────────────────────────────────────────────────────────────────────────
    elements.append(Paragraph("Detalhes da partida", h1_style))
    elements.append(Spacer(1, 6))

    # Tabela de Sets
    s1_d1 = partida.set1_dupla1 or 0
    s1_d2 = partida.set1_dupla2 or 0
    s2_d1 = partida.set2_dupla1 or 0
    s2_d2 = partida.set2_dupla2 or 0
    s3_d1 = partida.set3_dupla1 or 0
    s3_d2 = partida.set3_dupla2 or 0

    detalhes_data = [
        [
            Paragraph(f"🟢 <b>{partida.jogador1_nome} / {partida.jogador2_nome}</b>", text_bold_left),
            Paragraph(str(s1_d1), text_bold_center),
            Paragraph(str(s2_d1), text_bold_center),
            Paragraph(str(s3_d1), text_bold_center),
        ],
        [
            Paragraph(f"🔵 <b>{partida.jogador3_nome} / {partida.jogador4_nome}</b>", text_bold_left),
            Paragraph(str(s1_d2), text_bold_center),
            Paragraph(str(s2_d2), text_bold_center),
            Paragraph(str(s3_d2), text_bold_center),
        ],
    ]
    t_detalhes = Table(detalhes_data, colWidths=[360, 50, 50, 50])
    t_detalhes.setStyle(TableStyle([
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
        ('TOPPADDING', (0, 0), (-1, -1), 8),
        ('LINEBELOW', (0, 0), (-1, 0), 0.5, border_color),
        ('LINEBELOW', (0, 1), (-1, 1), 1, border_color),
    ]))
    elements.append(t_detalhes)
    elements.append(Spacer(1, 24))

    elements.append(Paragraph("Análise da partida", h1_style))
    elements.append(Paragraph("Estatísticas gerais", h2_style))
    elements.append(Spacer(1, 4))

    # Tabela de Estatísticas Gerais
    t_gerais_data = [
        [
            Paragraph(f"<b>{partida.jogador1_nome}</b><br/><b>{partida.jogador2_nome}</b>", text_bold_center),
            Paragraph("<b>Estatística</b>", text_bold_center),
            Paragraph(f"<b>{partida.jogador3_nome}</b><br/><b>{partida.jogador4_nome}</b>", text_bold_center),
        ]
    ]

    for item in stats['estatisticas_gerais']:
        t_gerais_data.append([
            Paragraph(str(item['dupla1']), text_bold_center if item['destaque'] == 'dupla1' else text_center),
            Paragraph(str(item['nome']), text_center),
            Paragraph(str(item['dupla2']), text_bold_center if item['destaque'] == 'dupla2' else text_center),
        ])

    t_gerais = Table(t_gerais_data, colWidths=[170, 170, 170])
    t_gerais.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), light_bg),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
        ('LINEBELOW', (0, 0), (-1, -1), 0.5, border_color),
    ]))
    elements.append(t_gerais)
    elements.append(PageBreak())

    # ──────────────────────────────────────────────────────────────────────────
    # PÁGINA 3: ESTATÍSTICAS POR ATLETA
    # ──────────────────────────────────────────────────────────────────────────
    elements.append(Paragraph("Estatísticas por atleta", h1_style))
    elements.append(Spacer(1, 10))

    t_atletas_data = [
        [
            Paragraph("<b>Estatística</b>", text_bold_left),
            Paragraph(f"<b>{partida.jogador1_nome}</b>", text_bold_center),
            Paragraph(f"<b>{partida.jogador2_nome}</b>", text_bold_center),
            Paragraph(f"<b>{partida.jogador3_nome}</b>", text_bold_center),
            Paragraph(f"<b>{partida.jogador4_nome}</b>", text_bold_center),
        ]
    ]

    metricas_atletas = [
        ('Winner', 'winners'),
        ('Ace', 'aces'),
        ('Erro de devolução', 'erros_devolucao'),
        ('Erro não forçado', 'erros_nao_forcados'),
        ('Forçou erro do adversário', 'forcou_erros'),
        ('Erro de Saque', 'saque_resumo'),
        ('Confirmação de saque', 'confirmacoes_saque'),
        ('Saque quebrado', 'saques_quebrados'),
    ]

    for label, chave in metricas_atletas:
        linha = [Paragraph(label, text_left)]
        for j in [1, 2, 3, 4]:
            val = stats['stats_atleta'][j].get(chave, 0)
            linha.append(Paragraph(str(val), text_center))
        t_atletas_data.append(linha)

    t_atletas = Table(t_atletas_data, colWidths=[140, 92, 92, 92, 92])
    t_atletas.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), light_bg),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 7),
        ('TOPPADDING', (0, 0), (-1, -1), 7),
        ('LINEBELOW', (0, 0), (-1, -1), 0.5, border_color),
    ]))
    elements.append(t_atletas)
    elements.append(Spacer(1, 24))

    # Dinâmica do jogo resumo
    elements.append(Paragraph("Dinâmica do jogo", h2_style))
    elements.append(Paragraph("Indicando a oscilação de vantagem da partida ao longo de cada ponto:", text_left))
    elements.append(Spacer(1, 6))

    # Tabela compacta dos maiores momentos
    dinamica_resumo = [
        [
            Paragraph("<b>Total de Pontos</b>", text_bold_left),
            Paragraph(str(stats['total_pontos']), text_center),
            Paragraph("<b>Ponto Decisivo (40x40)</b>", text_bold_left),
            Paragraph(f"{stats['pct_dupla1']}% vs {stats['pct_dupla2']}%", text_center),
        ],
        [
            Paragraph(f"<b>Ganhos por {partida.jogador1_nome}/{partida.jogador2_nome}</b>", text_left),
            Paragraph(f"{stats['pontos_dupla1']} ({stats['pct_dupla1']}%)", text_bold_center),
            Paragraph(f"<b>Ganhos por {partida.jogador3_nome}/{partida.jogador4_nome}</b>", text_left),
            Paragraph(f"{stats['pontos_dupla2']} ({stats['pct_dupla2']}%)", text_bold_center),
        ]
    ]
    t_dinamica = Table(dinamica_resumo, colWidths=[160, 90, 160, 98])
    t_dinamica.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), light_bg),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
        ('BOX', (0, 0), (-1, -1), 0.5, border_color),
        ('INNERGRID', (0, 0), (-1, -1), 0.5, border_color),
    ]))
    elements.append(t_dinamica)
    elements.append(PageBreak())

    # ──────────────────────────────────────────────────────────────────────────
    # PÁGINA 4+: HISTÓRICO PONTO A PONTO
    # ──────────────────────────────────────────────────────────────────────────
    elements.append(Paragraph("Histórico Ponto a Ponto", h1_style))
    elements.append(Paragraph("Detalhamento completo de cada ponto da partida:", text_left))
    elements.append(Spacer(1, 10))

    pontos = partida.pontos or []
    if not pontos:
        elements.append(Paragraph("Nenhum lance lançado para esta partida.", text_left))
    else:
        # Renderizar cada ponto em cards tabelados compactos
        linhas_pontos = []
        for p in pontos:
            # Vencedor badge
            if p.dupla_vencedora == 1:
                venc_txt = f"🟢 Vencido por <b>{partida.jogador1_nome} e {partida.jogador2_nome}</b>"
            else:
                venc_txt = f"🔵 Vencido por <b>{partida.jogador3_nome} e {partida.jogador4_nome}</b>"

            sacador_nome = partida.get_jogador_nome(p.sacador)
            lance_desc = p.descricao_lance or f"{p.tipo_desfecho.replace('_', ' ').capitalize()} de {partida.get_jogador_nome(p.atleta_finalizador or p.sacador)}"
            if p.tipo_golpe and p.tipo_golpe not in lance_desc:
                lance_desc += f" com {p.tipo_golpe}"

            placar_str = f"Placar: {p.placar_texto or '-'}"
            extra_badge = ""
            if p.situacao_adicional:
                extra_badge = f"<br/><font color='#0284C7'><b>[{p.situacao_adicional}]</b></font>"

            conteudo_ponto = (
                f"{venc_txt}<br/>"
                f"<font color='#64748B'>Sacador: {sacador_nome}</font><br/>"
                f"<b>{lance_desc}</b><br/>"
                f"<font color='#475569'>{placar_str}</font>{extra_badge}"
            )

            linhas_pontos.append([
                Paragraph(f"<b>#{p.numero_ponto}</b>", text_bold_center),
                Paragraph(conteudo_ponto, text_left)
            ])

        t_pontos = Table(linhas_pontos, colWidths=[40, 470])
        t_pontos.setStyle(TableStyle([
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
            ('TOPPADDING', (0, 0), (-1, -1), 6),
            ('LINEBELOW', (0, 0), (-1, -1), 0.5, border_color),
        ]))
        elements.append(t_pontos)

    doc.build(elements)
    buffer.seek(0)
    return buffer.getvalue()
