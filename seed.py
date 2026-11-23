import os
import sys
from datetime import datetime, date, time, timedelta
from app import create_app
from app.extensions import db
from app.models import (Usuario, Aluno, MetaAluno, Turma, TurmaAluno,
                        Exercicio, Aula, AulaExercicio, Avaliacao,
                        AvaliacaoNota, ConfiguracaoSite, Conquista,
                        Modalidade, Plano, Depoimento, GaleriaItem,
                        Partida, PontoPartida)

app = create_app(os.environ.get('FLASK_ENV', 'development'))

sys.stdout.reconfigure(encoding='utf-8', errors='replace')

def seed_database():
    with app.app_context():
        db.create_all()
        seed_demo = os.environ.get('SEED_DEMO', '1').lower() not in ('0', 'false', 'no')

        # 1. PROFESSOR / ADMIN
        admin_email = os.environ.get('ADMIN_EMAIL', 'professor@beachtennis.com').strip().lower()
        admin_senha = os.environ.get('ADMIN_PASSWORD', 'admin123')
        admin_nome = os.environ.get('ADMIN_NOME', 'Everson Vicktor Silva Silveira')
        if os.environ.get('FLASK_ENV', '').lower() == 'production' and admin_senha == 'admin123':
            raise RuntimeError(
                'Defina ADMIN_PASSWORD com uma senha forte antes de rodar o seed em produção.'
            )
        professor = Usuario.query.filter_by(email=admin_email).first()
        if not professor:
            professor = Usuario(
                nome=admin_nome,
                email=admin_email,
                perfil='admin',
                ativo=True
            )
            professor.set_senha(admin_senha)
            db.session.add(professor)
            print(f"Sucesso: Usuário professor criado ({admin_email})!")
        else:
            # Não sobrescreve nome nem senha de um admin já configurado.
            professor.ativo = True
            print("Sucesso: Usuário professor já existente (dados preservados).")

        # 2. CONFIGURAÇÕES DO SITE
        configs_padrao = {
            'nome_professor': 'Everson Vicktor Silva Silveira',
            'data_nascimento_professor': '2004-03-10',
            'formacao_professor': 'Estudante de Sistemas de Informação',
            'idade_professor': '22',
            'subtitulo_hero': 'Líder do ranking AIBT 2026 em 3 categorias',
            'sobre_texto': (
                'Atleta competitivo de Beach Tennis, professor e criador desta plataforma. '
                'Com 22 anos e estudante de Sistemas de Informação, uno a paixão pelo esporte '
                'com inovação tecnológica para acelerar a evolução de cada aluno dentro e fora de quadra. '
                'Em 2026, consolidei a liderança no ranking do Circuito AIBT nas categorias Masculina B, '
                'Masculina Open e Mista B, somando 16 pódios oficiais.'
            ),
            'cidade': 'Itabuna (BA)',
            'nome_quadra': 'Arena Beach Tennis Itabuna (exemplo)',
            'endereco': 'Itabuna - BA (endereço em breve)',
            'whatsapp': '5573999969999',
            'whatsapp_mensagem': 'Olá Everson! Gostaria de agendar uma aula experimental de Beach Tennis em Itabuna.',
            'instagram': 'eversonvicktor',
            'link_google_maps': 'https://maps.google.com/?q=Itabuna+BA'
        }
        for chave, val in configs_padrao.items():
            cfg = ConfiguracaoSite.query.filter_by(chave=chave).first()
            if not cfg:
                db.session.add(ConfiguracaoSite(chave=chave, valor=val))
            elif not cfg.valor:
                cfg.valor = val

        # 3. 16 CONQUISTAS OFICIAIS (2025 e 2026)
        conquistas_existentes = Conquista.query.count()
        if conquistas_existentes == 0:
            lista_conquistas = [
                # 2026 - Títulos (Campeão)
                (2026, 'campeao', 'Masculina B', 'Campeão Masc B (1ª Etapa)', 'Circuito AIBT', True, 1),
                (2026, 'campeao', 'Masculina B', 'Campeão Masc B (2ª Etapa)', 'Circuito AIBT', True, 2),
                (2026, 'campeao', 'Mista B', 'Campeão Mista B (1ª Etapa)', 'Circuito AIBT', True, 3),
                (2026, 'campeao', 'Mista B', 'Campeão Mista B (2ª Etapa)', 'Circuito AIBT', True, 4),
                (2026, 'campeao', 'Open Masc A/B', 'Campeão Open Masc A/B', 'Circuito AIBT', True, 5),
                # 2026 - Vices
                (2026, 'vice', 'Masculina B', 'Vice-campeão Masc B (1ª Etapa)', 'Circuito AIBT', False, 6),
                (2026, 'vice', 'Masculina B', 'Vice-campeão Masc B (2ª Etapa)', 'Circuito AIBT', False, 7),
                (2026, 'vice', 'Masculina B', 'Vice-campeão Masc B (3ª Etapa)', 'Circuito AIBT', False, 8),
                (2026, 'vice', 'Mista B', 'Vice-campeão Mista B (1ª Etapa)', 'Circuito AIBT', False, 9),
                (2026, 'vice', 'Mista B', 'Vice-campeão Mista B (2ª Etapa)', 'Circuito AIBT', False, 10),
                (2026, 'vice', 'Mista Open', 'Vice-campeão Mista Open', 'Circuito AIBT', False, 11),
                (2026, 'vice', 'Open Masc A/B', 'Vice-campeão Open Masc A/B', 'Circuito AIBT', False, 12),
                # 2026 - 3º Lugar
                (2026, '3_lugar', 'Open Masc A/B', '3º Lugar Open Masc A/B', 'Circuito AIBT', False, 13),
                # 2025 - Vices primeiro, Masc D por último (ponto de partida da evolução)
                (2025, 'vice', 'Masculina B', 'Vice-campeão Masc B', 'Circuito AIBT', False, 14),
                (2025, 'vice', 'Open Masc', 'Vice-campeão Open Masc', 'Circuito AIBT', False, 15),
                (2025, 'campeao', 'Masculina D', 'Campeão Masc D', 'Circuito AIBT', True, 16),
            ]
            for ano, colocacao, cat, tit, tor, dest, ordm in lista_conquistas:
                db.session.add(Conquista(
                    ano=ano, colocacao=colocacao, categoria=cat,
                    titulo=tit, torneio=tor, destaque=dest, ordem=ordm
                ))
            print("Sucesso: 16 Conquistas cadastradas!")

        # 4. MODALIDADES DE AULA
        if Modalidade.query.count() == 0:
            modalidades = [
                Modalidade(
                    nome='Individual',
                    descricao='Treino exclusivo focado 100% nas suas metas, ajustes biomecânicos e ritmo de jogo personalizado.',
                    icone='bi-person-fill',
                    publico_alvo='Todos os níveis (Iniciante ao Avançado)',
                    duracao_estimada='60 min',
                    ordem=1, destaque=True, ativo=True
                ),
                Modalidade(
                    nome='Em Duplas',
                    descricao='Sincronia tática de dupla, cobertura de rede, comunicação e padrões de jogadas competitivas.',
                    icone='bi-people-fill',
                    publico_alvo='Duplas já formadas ou em formação',
                    duracao_estimada='60 a 90 min',
                    ordem=2, destaque=False, ativo=True
                ),
                Modalidade(
                    nome='Turma Regular',
                    descricao='Aulas dinâmicas e energéticas em turmas de 4 a 6 alunos, combinando técnica e simulação de jogo.',
                    icone='bi-collection-fill',
                    publico_alvo='Iniciantes a Intermediários',
                    duracao_estimada='60 min',
                    ordem=3, destaque=False, ativo=True
                ),
                Modalidade(
                    nome='Iniciante',
                    descricao='Passo a passo com introdução segura: empunhaduras, movimentação na areia e fundamentos de saque e voleio.',
                    icone='bi-flag-fill',
                    publico_alvo='Quem nunca jogou ou está começando',
                    duracao_estimada='60 min',
                    ordem=4, destaque=False, ativo=True
                ),
                Modalidade(
                    nome='Intermediário',
                    descricao='Ganho de aceleração, smash com salto, transição defesa-ataque e posicionamento refinado.',
                    icone='bi-lightning-charge-fill',
                    publico_alvo='Praticantes regulares',
                    duracao_estimada='60 min',
                    ordem=5, destaque=False, ativo=True
                ),
                Modalidade(
                    nome='Avançado',
                    descricao='Treinamento de alto rendimento, intensidade física, estratégia de torneio e consistência sob pressão.',
                    icone='bi-trophy-fill',
                    publico_alvo='Atletas de competição (Categorias B/Open)',
                    duracao_estimada='90 min',
                    ordem=6, destaque=False, ativo=True
                ),
                Modalidade(
                    nome='Kids',
                    descricao='Iniciação lúdica e divertida para crianças de 6 a 12 anos, desenvolvendo coordenação e gosto pelo esporte.',
                    icone='bi-emoji-smile-fill',
                    publico_alvo='Crianças de 6 a 12 anos',
                    duracao_estimada='50 min',
                    ordem=7, destaque=False, ativo=True
                )
            ]
            db.session.add_all(modalidades)
            print("Sucesso: 7 Modalidades cadastradas!")

        # 5. TURMAS ATIVAS (Para horários automáticos no site)
        if seed_demo and Turma.query.count() == 0:
            turma1 = Turma(
                nome='Turma Terça & Quinta Noite',
                nivel='iniciante',
                dias_semana='1,3',
                horario_inicio=time(18, 30),
                horario_fim=time(19, 30),
                local='Arena Beach Tennis Itabuna - Quadra 1',
                vagas=6,
                ativa=True
            )
            turma2 = Turma(
                nome='Turma Sábado Manhã - Intermediário',
                nivel='intermediario',
                dias_semana='5',
                horario_inicio=time(8, 0),
                horario_fim=time(9, 30),
                local='Arena Beach Tennis Itabuna - Quadra 2',
                vagas=6,
                ativa=True
            )
            db.session.add_all([turma1, turma2])
            print("Sucesso: Turmas de exemplo criadas!")

        # 6. PLANOS E VALORES (Marcados como exemplo)
        if seed_demo and Plano.query.count() == 0:
            planos = [
                Plano(
                    nome='Plano 2x por Semana (exemplo)',
                    descricao="2 aulas semanais em turma reduzida\nAcesso completo à plataforma do aluno\nAvaliação técnica periódica a cada 60 dias\nBolinhas de treino fornecidas",
                    preco=260.00,
                    periodo='mensal',
                    aulas_por_semana=2,
                    destaque=False,
                    ativo=True,
                    ordem=1
                ),
                Plano(
                    nome='Plano 3x por Semana (exemplo)',
                    descricao="3 aulas semanais para aceleração rápida\nAcesso total à plataforma com gráficos e histórico\nAvaliação técnica mensal com vídeo-análise\nDesconto em clínicas e torneios internos",
                    preco=350.00,
                    periodo='mensal',
                    aulas_por_semana=3,
                    destaque=True,
                    ativo=True,
                    ordem=2
                ),
                Plano(
                    nome='Aula Avulsa / Experimental (exemplo)',
                    descricao="1 aula de 60 minutos\nDiagnóstico inicial de nível e objetivos\nEquipamento fornecido se necessário\nAgendamento flexível de acordo com disponibilidade",
                    preco=60.00,
                    periodo='avulso',
                    aulas_por_semana=1,
                    destaque=False,
                    ativo=True,
                    ordem=3
                )
            ]
            db.session.add_all(planos)
            print("Sucesso: Planos de exemplo criados!")

        # 7. DEPOIMENTOS (Exemplo aprovados)
        if seed_demo and Depoimento.query.count() == 0:
            deps = [
                Depoimento(
                    nome='Camila Rocha (exemplo)',
                    texto='As aulas com o professor Everson transformaram meu jogo! A metodologia focada na técnica e a análise de vídeo na plataforma facilitaram muito ver onde eu estava errando no saque.',
                    aprovado=True,
                    destaque=True,
                    ordem=1
                ),
                Depoimento(
                    nome='Rodrigo Mendonça (exemplo)',
                    texto='Treino de alto nível em Itabuna. O acompanhamento periódico com radar de habilidades dá uma motivação extra a cada treino.',
                    aprovado=True,
                    destaque=True,
                    ordem=2
                )
            ]
            db.session.add_all(deps)
            print("Sucesso: Depoimentos de exemplo criados!")

        # 8. ALUNO PADRÃO DE TESTE (Lucas Silva) — apenas quando SEED_DEMO != 0
        aluno_user = Usuario.query.filter_by(email='aluno@beachtennis.com').first() if seed_demo else None
        if not seed_demo:
            print("Seed de demonstração desativado (SEED_DEMO=0). Nenhum aluno de teste criado.")
        elif not aluno_user:
            aluno_user = Usuario(
                nome='Lucas Silva',
                email='aluno@beachtennis.com',
                perfil='aluno',
                ativo=True
            )
            aluno_user.set_senha('aluno123')
            db.session.add(aluno_user)
            db.session.flush()

            aluno = Aluno(
                usuario_id=aluno_user.id,
                nome='Lucas Silva',
                telefone='73988887777',
                data_nascimento=date(1996, 4, 15),
                nivel='intermediario',
                categoria='C',
                lado_dominante='destro',
                objetivo='competicao',
                ativo=True
            )
            db.session.add(aluno)
            db.session.flush()

            meta1 = MetaAluno(aluno_id=aluno.id, descricao='Aprimorar saque com spin e voleio de bloqueio', prazo=date.today() + timedelta(days=30))
            db.session.add(meta1)

            # Avaliação 1 (Inicial — ainda na categoria D)
            aval1 = Avaliacao(
                aluno_id=aluno.id,
                data=date.today() - timedelta(days=120),
                categoria='D',
                pontos_fortes='Ótima dedicação e bom condicionamento de base.',
                pontos_melhorar='Trabalhar terminação do saque e voleio de aproximação.',
                metas_proximo_ciclo='Consolidar movimentação na areia.',
                comentarios='Primeiro ciclo avaliativo, na categoria D.'
            )
            db.session.add(aval1)
            db.session.flush()

            notas1 = {
                'saque': 8.0, 'forehand': 8.0, 'backhand': 7.5, 'voleio': 8.0, 'smash': 8.5,
                'bandeja_defesa': 7.5, 'deslocamento': 8.0, 'posicionamento_dupla': 8.0,
                'leitura_jogo': 8.0, 'condicionamento': 8.5, 'mental_foco': 8.0
            }
            for crit, val in notas1.items():
                db.session.add(AvaliacaoNota(avaliacao_id=aval1.id, criterio=crit, nota=val))

            # Avaliação 2 (Primeiro ciclo na categoria C — nota bruta cai,
            # porque agora a comparação é com atletas da categoria C)
            aval2 = Avaliacao(
                aluno_id=aluno.id,
                data=date.today() - timedelta(days=60),
                categoria='C',
                pontos_fortes='Adaptação rápida ao ritmo da categoria C.',
                pontos_melhorar='Ajustar posicionamento de transição rápida.',
                metas_proximo_ciclo='Trabalhar voleio curto e bloqueio defensivo.',
                comentarios='Promoção para a categoria C. A nota é relativa aos novos pares.'
            )
            db.session.add(aval2)
            db.session.flush()

            notas2 = {
                'saque': 7.0, 'forehand': 7.5, 'backhand': 6.5, 'voleio': 7.0, 'smash': 8.0,
                'bandeja_defesa': 6.5, 'deslocamento': 7.0, 'posicionamento_dupla': 7.5,
                'leitura_jogo': 7.5, 'condicionamento': 8.0, 'mental_foco': 7.5
            }
            for crit, val in notas2.items():
                db.session.add(AvaliacaoNota(avaliacao_id=aval2.id, criterio=crit, nota=val))

            # Avaliação 3 (Ciclo atual na categoria C — a curva de aprendizado sobe)
            aval3 = Avaliacao(
                aluno_id=aluno.id,
                data=date.today() - timedelta(days=5),
                categoria='C',
                pontos_fortes='Grande salto técnico no saque, forehand mais firme e excelente leitura tática.',
                pontos_melhorar='Ajustar posicionamento de transição rápida.',
                metas_proximo_ciclo='Trabalhar voleio curto e bloqueio defensivo.',
                comentarios='Evolução notável em todos os quesitos dentro da categoria C.',
                link_video_analise='https://www.youtube.com/watch?v=dQw4w9WgXcQ'
            )
            db.session.add(aval3)
            db.session.flush()

            notas3 = {
                'saque': 7.8, 'forehand': 8.0, 'backhand': 7.2, 'voleio': 7.8, 'smash': 8.5,
                'bandeja_defesa': 7.2, 'deslocamento': 7.6, 'posicionamento_dupla': 8.0,
                'leitura_jogo': 8.2, 'condicionamento': 8.5, 'mental_foco': 8.2
            }
            for crit, val in notas3.items():
                db.session.add(AvaliacaoNota(avaliacao_id=aval3.id, criterio=crit, nota=val))

            # Vincula à turma e aula futura
            turma = Turma.query.filter_by(ativa=True).first()
            if turma:
                ta = TurmaAluno(turma_id=turma.id, aluno_id=aluno.id, ativo=True)
                db.session.add(ta)
                db.session.flush()

                aula_futura = Aula(
                    turma_id=turma.id,
                    data_hora=datetime.now() + timedelta(days=2, hours=3),
                    duracao_minutos=90,
                    objetivo='Treino técnico de voleio na rede e saque angulado',
                    status='agendada'
                )
                db.session.add(aula_futura)

            print("Sucesso: Aluno padrão Lucas Silva criado com 3 avaliações (D -> C) e curva de evolução!")
        else:
            aluno_user.ativo = True

        # 9. PARTIDA DEMO DO BT TRACKER (SCOUT REAL DOS RELATÓRIOS OFICIAIS)
        if seed_demo and Partida.query.count() == 0:
            aluno_padrao = Aluno.query.first()
            partida_demo = Partida(
                titulo='Final Circuito AIBT 2026 — Masculina B',
                data=date.today() - timedelta(days=7),
                torneio='Circuito AIBT 2026',
                categoria='Masculina B',
                fase='Final',
                local='Arena Itabuna (Quadra Central)',
                jogador1_nome='Everson Vicktor',
                jogador2_nome='Lucas Silva',
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
                observacoes='Grande final do Circuito AIBT com vento moderado. Destaque para os smashes e variações de saque aberto.'
            )
            db.session.add(partida_demo)
            db.session.flush()

            # Lances reais da partida oficial do BT Tracker
            amostra_pontos = [
                (4, 1, 3, 'erro_nao_forcado', 'Smash', 'Esquerda', '2', 'Bom', 'No sacador', 'Boa', '0x0 15x0', None, 45, 60, 50, 15, 'Erro não forçado de Smash de Carlos Mendes'),
                (4, 2, 4, 'winner', 'Smash', 'Esquerda', '3', 'Bom', 'Meio', 'Regular', '0x0 15x15', None, 60, 80, 20, 25, 'Winner de Smash de Rafael Costa'),
                (4, 2, 1, 'erro_nao_forcado', 'Avanço com Forehand', 'Esquerda', '4', 'Bom', 'No sacador', 'Regular', '0x0 15x30', None, 30, 20, 35, 95, 'Erro não forçado de Avanço de Everson Vicktor'),
                (4, 1, 4, 'erro_saque', None, 'Esquerda', '5', 'Erro', None, None, '0x0 30x30', None, 65, 85, 65, 45, 'Erro de Saque de Rafael Costa'),
                (4, 1, 4, 'erro_saque', None, 'Esquerda', '3', 'Erro', None, None, '0x0 40x30', None, 65, 85, 50, 48, 'Erro de Saque de Rafael Costa'),
                (4, 2, 4, 'winner', 'Gancho', 'Esquerda', '2', 'Bom', 'Lob', 'Regular', '0x0 40x40', 'Bola na Fita', 70, 75, 25, 20, 'Winner de Gancho de Rafael Costa [40x40 Decisivo]'),
                (4, 2, 4, 'forcou_erro', 'Lob Chutado com Forehand', 'Esquerda', '3', 'Bom', 'Meio', 'Ruim', '0x1', None, 50, 80, 80, 15, 'Rafael Costa forçou o erro com Lob Chutado'),

                (2, 2, 2, 'erro_saque', None, 'Direita', '1', 'Erro', None, None, '0x1 0x15', None, 35, 15, 35, 52, 'Erro de Saque de Lucas Silva'),
                (2, 2, 2, 'erro_saque', None, 'Direita', '1', 'Erro', None, None, '0x1 0x30', None, 35, 15, 45, 53, 'Erro de Saque de Lucas Silva'),
                (2, 2, 4, 'winner', 'Smash', 'Direita', '3', 'Regular', 'No sacador', 'Boa', '0x1 0x40', None, 65, 80, 30, 20, 'Winner de Smash de Rafael Costa'),
                (2, 1, 4, 'erro_devolucao', None, 'Direita', '2', 'Bom', 'No sacador', 'Erro', '0x1 15x40', None, 40, 20, 70, 70, 'Erro de devolução de Rafael Costa'),
                (2, 2, 4, 'forcou_erro', 'Smash', 'Direita', '3', 'Regular', 'Meio', 'Ruim', '0x2', None, 75, 75, 40, 25, 'Rafael Costa forçou o erro com Smash'),

                (3, 2, 4, 'winner', 'Smash', 'Direita', '3', 'Bom', 'No sacador', 'Regular', '0x2 0x15', None, 65, 80, 25, 15, 'Winner de Smash de Rafael Costa'),
                (3, 2, 4, 'winner', 'Lob Chutado com Forehand', 'Direita', '3', 'Bom', 'Meio', 'Regular', '0x2 0x30', 'Bola na Linha', 70, 75, 20, 10, 'Winner de Lob Chutado de Rafael Costa'),
                (3, 1, 2, 'winner', 'Lob Chutado com Backhand', 'Direita', '2', 'Regular', 'No sacador', 'Boa', '0x2 15x30', None, 40, 25, 80, 85, 'Winner de Lob Chutado de Lucas Silva'),
                (3, 2, 2, 'erro_devolucao', None, 'Direita', '4', 'Bom', 'No parceiro', 'Erro', '0x2 15x40', 'Bola na Fita', 35, 85, 30, 30, 'Erro de devolução de Lucas Silva'),
                (3, 1, 2, 'forcou_erro', 'Smash', 'Direita', '3', 'Regular', 'Meio', 'Regular', '0x2 30x40', None, 45, 30, 65, 80, 'Lucas Silva forçou erro com Smash'),
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
                (3, 2, 2, 'erro_devolucao', None, 'Direita', '3', 'Bom', 'No sacador', 'Erro', '2x4 30x15', None, 45, 20, 35, 85, 'Erro de devolução de Lucas Silva'),
                (3, 1, 3, 'erro_saque', None, 'Direita', '4', 'Erro', None, None, '2x4 40x15', None, 35, 85, 30, 45, 'Erro de Saque de Carlos Mendes'),
                (3, 2, 4, 'winner', 'Lob Chutado com Forehand', 'Direita', '3', 'Bom', 'Meio', 'Regular', '2x4 40x30', None, 70, 80, 25, 15, 'Winner de Lob Chutado de Rafael Costa'),
                (3, 1, 3, 'erro_nao_forcado', 'Lob Chutado com Forehand', 'Direita', '3', 'Bom', 'Meio', 'Regular', '3x4', None, 35, 75, 35, 5, 'Erro não forçado de Lob Chutado de Carlos Mendes'),
            ]

            for idx, pt in enumerate(amostra_pontos, start=1):
                ponto = PontoPartida(
                    partida_id=partida_demo.id,
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

            print("Sucesso: Partida oficial do BT Tracker com 42 lances cadastrada!")

        db.session.commit()
        print("\n=== BANCO DE DADOS POPULADO COM SUCESSO! ===")
        print(f"Professor (Admin): {admin_email}")
        if seed_demo:
            print("Aluno de demonstração: aluno@beachtennis.com / aluno123")

if __name__ == '__main__':
    seed_database()
