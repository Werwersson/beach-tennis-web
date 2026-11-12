import io
import math
from datetime import date
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, KeepTogether
)
from reportlab.graphics.shapes import Drawing, Polygon, Line, Circle, String, Rect, Group
from app.models.avaliacao import CRITERIOS_AVALIACAO


def gerar_grafico_radar_reportlab(scores_inicial, scores_atual, labels_criterios,
                                  label_inicial='Avaliação Inicial',
                                  label_atual='Avaliação Atual (Última)'):
    """
    Gera um gráfico radar puramente vetorial e de alta resolução utilizando o motor de desenho do ReportLab.
    Sem dependências externas de JavaScript ou navegadores headless.
    """
    largura = 480
    altura = 240
    cx = largura / 2
    cy = altura / 2
    raio_max = 85

    d = Drawing(largura, altura)

    # Cores esportivas
    cor_grade = colors.HexColor('#D5D0C7')
    cor_inicial = colors.HexColor('#F77F00')
    cor_atual = colors.HexColor('#0077B6')

    n = len(labels_criterios)
    angulos = [(2 * math.pi * i / n) - (math.pi / 2) for i in range(n)]

    # 1. Círculos/Polígonos concêntricos da grade (níveis 2, 4, 6, 8, 10)
    for nivel in [2, 4, 6, 8, 10]:
        r = (nivel / 10.0) * raio_max
        pontos_grade = []
        for a in angulos:
            px = cx + r * math.cos(a)
            py = cy + r * math.sin(a)
            pontos_grade.extend([px, py])
        d.add(Polygon(pontos_grade, strokeColor=cor_grade, strokeWidth=0.6, fillColor=None))

    # 2. Eixos radiais a partir do centro
    for i, a in enumerate(angulos):
        ex = cx + raio_max * math.cos(a)
        ey = cy + raio_max * math.sin(a)
        d.add(Line(cx, cy, ex, ey, strokeColor=cor_grade, strokeWidth=0.7))

        # Rótulos dos eixos
        dist_label = raio_max + 14
        lx = cx + dist_label * math.cos(a)
        ly = cy + dist_label * math.sin(a) - 3

        txt = labels_criterios[i]
        # Abreviações para caber no PDF
        txt = txt.replace('Aspecto Mental e Foco', 'Mental/Foco')
        txt = txt.replace('Condicionamento Físico', 'Condic. Físico')
        txt = txt.replace('Deslocamento e Mobilidade', 'Deslocamento')
        txt = txt.replace('Posicionamento em Dupla', 'Posic. Dupla')
        txt = txt.replace('Leitura de Jogo', 'Leitura Jogo')

        # Alinhamento do texto
        anchor = 'middle'
        if math.cos(a) > 0.2:
            anchor = 'start'
        elif math.cos(a) < -0.2:
            anchor = 'end'

        d.add(String(lx, ly, txt, fontName='Helvetica-Bold', fontSize=6.5, fillColor=colors.HexColor('#222222'), textAnchor=anchor))

    # 3. Polígono da Avaliação Inicial (1ª)
    if scores_inicial and len(scores_inicial) == n:
        pontos_ini = []
        for i, a in enumerate(angulos):
            val = min(max(scores_inicial[i], 0), 10)
            r = (val / 10.0) * raio_max
            pontos_ini.extend([cx + r * math.cos(a), cy + r * math.sin(a)])
        d.add(Polygon(
            pontos_ini,
            strokeColor=cor_inicial,
            strokeWidth=1.8,
            fillColor=colors.Color(247/255, 127/255, 0/255, alpha=0.18)
        ))

    # 4. Polígono da Avaliação Atual (Última)
    if scores_atual and len(scores_atual) == n:
        pontos_atu = []
        for i, a in enumerate(angulos):
            val = min(max(scores_atual[i], 0), 10)
            r = (val / 10.0) * raio_max
            pontos_atu.extend([cx + r * math.cos(a), cy + r * math.sin(a)])
        d.add(Polygon(
            pontos_atu,
            strokeColor=cor_atual,
            strokeWidth=2.2,
            fillColor=colors.Color(0/255, 119/255, 182/255, alpha=0.30)
        ))

    # 5. Legenda inferior
    leg_y = 6
    # Item 1: Inicial
    d.add(Rect(cx - 150, leg_y, 16, 5, fillColor=colors.HexColor('#F77F00'), strokeColor=None))
    d.add(String(cx - 130, leg_y - 1, label_inicial, fontName='Helvetica', fontSize=8, fillColor=colors.HexColor('#444444')))

    # Item 2: Atual
    d.add(Rect(cx + 20, leg_y, 16, 5, fillColor=colors.HexColor('#0077B6'), strokeColor=None))
    d.add(String(cx + 40, leg_y - 1, label_atual, fontName='Helvetica-Bold', fontSize=8, fillColor=colors.HexColor('#005F8E')))

    return d


def gerar_relatorio_pdf_aluno(aluno, analytics):
    """
    Gera o relatório de progresso do aluno em PDF de alta qualidade.
    Retorna os bytes do PDF gerado.
    """
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        leftMargin=32,
        rightMargin=32,
        topMargin=28,
        bottomMargin=28
    )

    styles = getSampleStyleSheet()
    
    # Estilos customizados
    titulo_style = ParagraphStyle(
        'TituloDoc',
        parent=styles['Heading1'],
        fontName='Helvetica-Bold',
        fontSize=15,
        leading=18,
        textColor=colors.HexColor('#005F8E'),
        alignment=1,
        spaceAfter=2
    )

    subtitulo_style = ParagraphStyle(
        'SubtituloDoc',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=8.5,
        leading=11,
        textColor=colors.HexColor('#555555'),
        alignment=1,
        spaceAfter=10
    )

    secao_titulo_style = ParagraphStyle(
        'SecaoTitulo',
        parent=styles['Heading2'],
        fontName='Helvetica-Bold',
        fontSize=10,
        leading=13,
        textColor=colors.HexColor('#005F8E'),
        spaceBefore=8,
        spaceAfter=4
    )

    corpo_style = ParagraphStyle(
        'CorpoTexto',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=8.5,
        leading=12,
        textColor=colors.HexColor('#222222')
    )

    story = []

    # 1. Cabeçalho com Identidade Visual
    story.append(Paragraph("BEACH TENNIS — RELATÓRIO DE EVOLUÇÃO TÉCNICA", titulo_style))
    story.append(Paragraph("Prof. Everson Vicktor Silva Silveira · Circuito AIBT · Itabuna - BA", subtitulo_style))

    # Linha separadora
    story.append(Spacer(1, 2))

    # 2. Dados do Atleta & Resumo
    ultima = analytics.get('ultima_avaliacao')
    primeira = analytics.get('primeira_avaliacao')

    media_atual_str = f"{ultima.media:.1f}" if ultima else "—"
    media_ini_str = f"{primeira.media:.1f}" if primeira else "—"
    cat_atual = analytics.get('categoria_atual_label', '—')
    cat_inicial = analytics.get('categoria_inicial_label', '—')
    indice_atual_str = f"{analytics.get('indice_atual', 0):.1f}"
    indice_ini_str = f"{analytics.get('indice_inicial', 0):.1f}"
    diff = analytics.get('diff_geral', 0)
    diff_indice = analytics.get('diff_indice', 0)
    diff_str = f"+{diff:.1f}" if diff > 0 else f"{diff:.1f}"
    diff_indice_str = f"+{diff_indice:.1f}" if diff_indice > 0 else f"{diff_indice:.1f}"

    dados_atleta = [
        [
            Paragraph(f"<b>Atleta:</b> {aluno.nome}", corpo_style),
            Paragraph(f"<b>Categoria:</b> {cat_atual}", corpo_style),
            Paragraph(f"<b>Nível:</b> {aluno.nivel.capitalize()}", corpo_style),
        ],
        [
            Paragraph(f"<b>Lado:</b> {aluno.lado_dominante.capitalize()}", corpo_style),
            Paragraph(f"<b>Objetivo:</b> {aluno.objetivo.capitalize() if aluno.objetivo else 'Desenvolvimento'}", corpo_style),
            Paragraph(f"<b>Total de Avaliações:</b> {analytics.get('total_avaliacoes', 0)} ciclo(s)", corpo_style),
        ],
        [
            Paragraph(f"<b>Nota Inicial:</b> {media_ini_str} / 10 ({cat_inicial})", corpo_style),
            Paragraph(f"<b>Nota Atual:</b> <font color='#005F8E'><b>{media_atual_str} / 10</b></font> ({cat_atual})", corpo_style),
            Paragraph(f"<b>Índice Atual:</b> <font color='#E65100'><b>{indice_atual_str} / 100</b></font>", corpo_style),
        ],
        [
            Paragraph(f"<b>Variação da Nota:</b> <font color='#2E7D32'><b>{diff_str}</b></font>", corpo_style),
            Paragraph(f"<b>Variação do Índice:</b> <font color='#2E7D32'><b>{diff_indice_str}</b></font>", corpo_style),
            Paragraph(f"<b>Data de Emissão:</b> {date.today().strftime('%d/%m/%Y')}", corpo_style),
        ]
    ]

    t_atleta = Table(dados_atleta, colWidths=[200, 160, 170])
    t_atleta.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#F6F4EE')),
        ('BOX', (0, 0), (-1, -1), 1, colors.HexColor('#DCD7CC')),
        ('INNERGRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#E5E0D6')),
        ('PADDING', (0, 0), (-1, -1), 5),
    ]))
    story.append(t_atleta)
    story.append(Spacer(1, 6))

    if analytics.get('tem_multiplas_categorias'):
        story.append(Paragraph(
            f"<font color='#555555' size='7.5'>O atleta mudou de categoria ({cat_inicial} → {cat_atual}). "
            "A nota é atribuída dentro da categoria do ciclo; por isso ela pode cair na promoção. "
            "O Índice Técnico (0–100) desconta a diferença de dificuldade e representa a curva de aprendizado.</font>",
            corpo_style
        ))
        story.append(Spacer(1, 6))

    # 3. Gráfico Radar Vetorial
    if analytics.get('tem_avaliacoes'):
        criterios_labels = [label for _, label in CRITERIOS_AVALIACAO]
        criterios_keys = [k for k, _ in CRITERIOS_AVALIACAO]
        scores_ini = [primeira.get_nota(k) or 0 for k in criterios_keys] if primeira else []
        scores_atu = [ultima.get_nota(k) or 0 for k in criterios_keys] if ultima else []

        story.append(Paragraph("<b>Mapeamento Radar de Habilidades (Inicial vs Atual)</b>", secao_titulo_style))
        radar_drawing = gerar_grafico_radar_reportlab(
            scores_ini, scores_atu, criterios_labels,
            label_inicial=f'Avaliação Inicial ({cat_inicial})',
            label_atual=f'Avaliação Atual ({cat_atual})',
        )
        story.append(radar_drawing)
        story.append(Spacer(1, 6))

    # 4. Tabela de Critérios com Comparativo e Setas (↑ ↓ =)
    story.append(Paragraph("<b>Comparativo Técnico por Critério (Escala 1 a 10)</b>", secao_titulo_style))

    header_tabela = [
        'Critério Avaliado',
        f"1ª ({analytics.get('categoria_inicial', 'D')})",
        f"Atual ({analytics.get('categoria_atual', 'D')})",
        'Variação',
        'Índice (0–100)',
        'Status',
    ]
    linhas_tabela = [header_tabela]

    for c in analytics.get('comparativo_criterios', []):
        cor_txt = '#2E7D32' if c['diff'] > 0 else ('#C62828' if c['diff'] < 0 else '#666666')
        simbolo = c['simbolo']
        sinal = c['sinal']

        status_txt = "Evolução" if c['diff_indice'] > 0 else ("Ajuste" if c['diff_indice'] < 0 else "Mantido")

        linhas_tabela.append([
            c['label'],
            f"{c['nota_inicial']:.1f}",
            f"{c['nota_atual']:.1f}",
            f"{simbolo} {sinal}",
            f"{c['indice_atual']:.1f}",
            status_txt
        ])

    t_criterios = Table(linhas_tabela, colWidths=[165, 75, 85, 70, 75, 60])
    t_criterios.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#005F8E')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 7.5),
        ('ALIGN', (1, 0), (-1, -1), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#FAF8F5')]),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#E0DCD3')),
        ('FONTSIZE', (0, 1), (-1, -1), 7.5),
        ('PADDING', (0, 0), (-1, -1), 3.5),
    ]))
    story.append(t_criterios)
    story.append(Spacer(1, 8))

    # 5. Pareceres Técnicos e Metas
    if ultima:
        story.append(Paragraph("<b>Parecer Técnico & Diretrizes do Professor</b>", secao_titulo_style))

        pareceres_dados = [
            [
                Paragraph("<b>Pontos Fortes Demonstrados:</b>", corpo_style),
                Paragraph(ultima.pontos_fortes or "Não especificado.", corpo_style)
            ],
            [
                Paragraph("<b>Oportunidades de Desenvolvimento:</b>", corpo_style),
                Paragraph(ultima.pontos_melhorar or "Não especificado.", corpo_style)
            ],
            [
                Paragraph("<b>Metas para o Próximo Ciclo:</b>", corpo_style),
                Paragraph(ultima.metas_proximo_ciclo or "Não especificado.", corpo_style)
            ],
            [
                Paragraph("<b>Observações Gerais:</b>", corpo_style),
                Paragraph(ultima.comentarios or "Consistência e dedicação comprovadas nos treinos.", corpo_style)
            ]
        ]

        t_pareceres = Table(pareceres_dados, colWidths=[160, 370])
        t_pareceres.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#F2EFE9')),
            ('BACKGROUND', (1, 0), (1, -1), colors.white),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#DCD7CC')),
            ('PADDING', (0, 0), (-1, -1), 4),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ]))
        story.append(t_pareceres)
        story.append(Spacer(1, 10))

    # 6. Rodapé com Validação
    rodape_txt = Paragraph(
        "<font color='#777777'>Relatório emitido pela plataforma oficial de Beach Tennis. Professor Everson Vicktor Silva Silveira · Itabuna - BA.</font>",
        ParagraphStyle('Rodape', parent=styles['Normal'], fontName='Helvetica', fontSize=7.5, alignment=1)
    )
    story.append(rodape_txt)

    # Constrói o documento
    doc.build(story)
    pdf_bytes = buffer.getvalue()
    buffer.close()
    return pdf_bytes

