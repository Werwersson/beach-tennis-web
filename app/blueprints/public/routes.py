import re
from datetime import datetime, date, timedelta
from flask import (Blueprint, render_template, request, redirect, url_for,
                   flash, Response, current_app)
from app.extensions import db
from app.models import (ConfiguracaoSite, Conquista, Modalidade, Turma,
                        Plano, Depoimento, GaleriaItem, MensagemContato)

public_bp = Blueprint('public', __name__)

DATA_NASCIMENTO_PADRAO = date(2004, 3, 10)


def calcular_idade_professor(data_nasc_ou_str=None, data_referencia=None):
    """Calcula a idade dinâmica do professor a partir da data de nascimento (padrão: 10/03/2004)."""
    if data_referencia is None:
        data_referencia = date.today()

    data_nasc = None
    if isinstance(data_nasc_ou_str, (date, datetime)):
        data_nasc = data_nasc_ou_str if isinstance(data_nasc_ou_str, date) else data_nasc_ou_str.date()
    elif isinstance(data_nasc_ou_str, str) and data_nasc_ou_str.strip():
        val = data_nasc_ou_str.strip()
        for fmt in ('%Y-%m-%d', '%d/%m/%Y', '%d-%m-%Y'):
            try:
                data_nasc = datetime.strptime(val, fmt).date()
                break
            except ValueError:
                pass

    if not data_nasc:
        data_nasc = DATA_NASCIMENTO_PADRAO

    idade = data_referencia.year - data_nasc.year - (
        (data_referencia.month, data_referencia.day) < (data_nasc.month, data_nasc.day)
    )
    return idade


def get_config_dict():
    """Retorna um dicionário com todas as configurações do site ou padrões."""
    configs_db = ConfiguracaoSite.query.all()
    config_dict = {c.chave: c.valor for c in configs_db if c.valor is not None and c.valor != ''}

    data_nasc_val = config_dict.get('data_nascimento_professor', '2004-03-10')
    idade_calc = calcular_idade_professor(data_nasc_val)

    padroes = {
        'nome_professor': 'Everson Vicktor Silva Silveira',
        'data_nascimento_professor': '2004-03-10',
        'idade_professor': str(idade_calc),
        'formacao_professor': 'Estudante de Sistemas de Informação',
        'destaque_ano': 'Líder do ranking AIBT 2026 em 3 categorias (Masc B, Masc Open e Mista B)',
        'titulo_hero': 'Aulas de Beach Tennis em Itabuna',
        'subtitulo_hero': 'Evolua sua técnica, tática e condicionamento na areia com acompanhamento profissional e análise de desempenho.',
        'cidade': 'Itabuna',
        'estado': 'BA',
        'nome_quadra': '',
        'endereco_quadra': '',
        'link_google_maps': '',
        'whatsapp': '',
        'mensagem_whatsapp': 'Olá Everson! Gostaria de informações sobre as aulas de Beach Tennis em Itabuna e agendar uma aula experimental.',
        'instagram': '',
        'email_contato': 'contato@beachtennis.com',
        'bio_resumo': (
            f'Olá, sou Everson Vicktor Silva Silveira, {idade_calc} anos, estudante de Sistemas de Informação, '
            'atleta competitivo de Beach Tennis, professor e criador desta plataforma. '
            'Em 2026, liderei o ranking do Circuito AIBT em 3 categorias simultâneas: Masculina B, '
            'Masculina Open e Mista B. Minha metodologia alia fundamentação técnica precisa, visão tática de jogo em dupla '
            'e acompanhamento de progresso ciclo a ciclo para iniciantes, intermediários e competidores.'
        ),
        'foto_professor': ''
    }

    # Preenche com padrões caso não exista no banco
    for k, v in padroes.items():
        if k not in config_dict:
            config_dict[k] = v

    # Garante idade sempre dinâmica e calculada
    config_dict['idade_professor'] = str(idade_calc)

    # Atualiza dinamicamente qualquer menção estática à idade em bio_resumo e sobre_texto
    padrao_idade_frase = re.compile(r'(\b(?:sou\s+[^,]+,\s*|Com\s*))\d+\s*anos', flags=re.IGNORECASE)
    if 'bio_resumo' in config_dict and config_dict['bio_resumo']:
        config_dict['bio_resumo'] = padrao_idade_frase.sub(rf'\g<1>{idade_calc} anos', config_dict['bio_resumo'])
    if 'sobre_texto' in config_dict and config_dict['sobre_texto']:
        config_dict['sobre_texto'] = padrao_idade_frase.sub(rf'\g<1>{idade_calc} anos', config_dict['sobre_texto'])

    return config_dict


@public_bp.route('/')
def index():
    cfg = get_config_dict()

    # 1. Conquistas e contadores dinâmicos calculados do banco
    conquistas = Conquista.query.order_by(Conquista.ano.desc(), Conquista.ordem.asc(), Conquista.id.asc()).all()
    
    total_titulos = sum(1 for c in conquistas if c.colocacao == 'campeao')
    total_vices = sum(1 for c in conquistas if c.colocacao == 'vice')
    total_terceiros = sum(1 for c in conquistas if c.colocacao == '3_lugar')
    total_podios = len(conquistas)
    rankings_lider = 3  # Masc B, Masc Open e Mista B (Circuito AIBT 2026)

    # 2. Modalidades ativas
    modalidades = Modalidade.query.filter_by(ativo=True).order_by(Modalidade.ordem.asc()).all()

    # 3. Horários das Turmas ativas (com vagas disponíveis)
    turmas_ativas = Turma.query.filter_by(ativa=True).order_by(Turma.horario_inicio.asc()).all()

    # 4. Planos e Valores ativos
    planos = Plano.query.filter_by(ativo=True).order_by(Plano.ordem.asc()).all()

    # 5. Depoimentos aprovados
    depoimentos = Depoimento.query.filter_by(aprovado=True).order_by(Depoimento.ordem.asc()).all()

    # 6. Galeria de fotos e vídeos
    galeria = GaleriaItem.query.filter_by(ativo=True).order_by(GaleriaItem.ordem.asc()).all()

    # Formatação do link de WhatsApp
    whatsapp_link = None
    whatsapp_raw = cfg.get('whatsapp', '').strip()
    if whatsapp_raw:
        num_limpo = re.sub(r'\D', '', whatsapp_raw)
        if len(num_limpo) in (10, 11) and not num_limpo.startswith('55'):
            num_limpo = f'55{num_limpo}'
        msg_enc = re.sub(r'\s+', '%20', cfg.get('mensagem_whatsapp', ''))
        whatsapp_link = f"https://wa.me/{num_limpo}?text={msg_enc}"

    return render_template(
        'public/index.html',
        cfg=cfg,
        conquistas=conquistas,
        total_titulos=total_titulos,
        total_vices=total_vices,
        total_terceiros=total_terceiros,
        total_podios=total_podios,
        rankings_lider=rankings_lider,
        modalidades=modalidades,
        turmas=turmas_ativas,
        planos=planos,
        depoimentos=depoimentos,
        galeria=galeria,
        whatsapp_link=whatsapp_link
    )


@public_bp.route('/contato', methods=['POST'])
def enviar_contato():
    """
    Processa o formulário de contato público com proteção anti-spam:
    - Campo honeypot (website_url) oculto para robôs
    - Limite de taxa de envio por IP (máx 5 mensagens na última hora)
    """
    # 1. Proteção Honeypot
    honeypot = request.form.get('website_url', '').strip()
    if honeypot:
        # Robô preencheu campo oculto; descarta silenciosamente
        flash('Mensagem recebida com sucesso! Entraremos em contato em breve.', 'success')
        return redirect(url_for('public.index') + '#contato')

    nome = request.form.get('nome', '').strip()
    telefone = request.form.get('telefone', '').strip()
    mensagem = request.form.get('mensagem', '').strip()
    ip_cliente = request.remote_addr or request.headers.get('X-Forwarded-For', '')

    if not nome or not telefone or not mensagem:
        flash('Por favor, preencha todos os campos do formulário.', 'warning')
        return redirect(url_for('public.index') + '#contato')

    # 2. Limite de envios por IP (máximo 5 por hora)
    uma_hora_atras = datetime.utcnow() - timedelta(hours=1)
    envios_recentes = MensagemContato.query.filter(
        MensagemContato.ip == ip_cliente,
        MensagemContato.criado_em >= uma_hora_atras
    ).count()

    if envios_recentes >= 5:
        flash('Muitas mensagens enviadas recentemente deste dispositivo. Aguarde um momento ou fale diretamente pelo WhatsApp.', 'warning')
        return redirect(url_for('public.index') + '#contato')

    # Salva a mensagem no banco
    nova_msg = MensagemContato(
        nome=nome,
        telefone=telefone,
        mensagem=mensagem,
        ip=ip_cliente,
        criado_em=datetime.utcnow()
    )
    db.session.add(nova_msg)
    db.session.commit()

    # Redireciona para o WhatsApp com a mensagem pré-preenchida
    cfg_contato = {r.chave: r.valor for r in ConfiguracaoSite.query.all()}
    whatsapp_num = re.sub(r'\D', '', cfg_contato.get('whatsapp', '5573999969999'))
    texto_wa = (
        f"Olá Everson! Me chamo {nome}.\n"
        f"Telefone: {telefone}\n\n"
        f"{mensagem}"
    )
    texto_enc = texto_wa.replace(' ', '%20').replace('\n', '%0A')
    wa_url = f"https://wa.me/{whatsapp_num}?text={texto_enc}"
    return redirect(wa_url)


@public_bp.route('/robots.txt')
def robots():
    """Arquivo robots.txt para indexação amigável por motores de busca."""
    base_url = request.url_root.rstrip('/')
    conteudo = f"""User-agent: *
Allow: /
Disallow: /admin/
Disallow: /aluno/
Disallow: /auth/

Sitemap: {base_url}/sitemap.xml
"""
    return Response(conteudo, mimetype='text/plain')


@public_bp.route('/sitemap.xml')
def sitemap():
    """Sitemap XML oficial para SEO."""
    base_url = request.url_root.rstrip('/')
    hoje_iso = date.today().isoformat()
    xml = f"""<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
  <url>
    <loc>{base_url}/</loc>
    <lastmod>{hoje_iso}</lastmod>
    <changefreq>weekly</changefreq>
    <priority>1.0</priority>
  </url>
  <url>
    <loc>{base_url}/auth/login</loc>
    <lastmod>{hoje_iso}</lastmod>
    <changefreq>monthly</changefreq>
    <priority>0.5</priority>
  </url>
</urlset>
"""
    return Response(xml, mimetype='application/xml')
