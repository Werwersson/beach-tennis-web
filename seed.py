import os
import sys
from datetime import datetime, date, time, timedelta
from app import create_app
from app.extensions import db
from app.models import (Usuario, Aluno, MetaAluno, Turma, TurmaAluno,
                        Exercicio, Aula, AulaExercicio, Avaliacao,
                        AvaliacaoNota, ConfiguracaoSite, Conquista,
                        Modalidade, Plano, Depoimento, GaleriaItem)

app = create_app(os.environ.get('FLASK_ENV', 'development'))

sys.stdout.reconfigure(encoding='utf-8', errors='replace')

def seed_database():
    with app.app_context():
        db.create_all()

        # 1. PROFESSOR / ADMIN
        admin_email = os.environ.get('ADMIN_EMAIL', 'professor@beachtennis.com').strip().lower()
        admin_senha = os.environ.get('ADMIN_PASSWORD', 'admin123')
        admin_nome = os.environ.get('ADMIN_NOME', 'Everson Vicktor Silva Silveira')
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
            professor.nome = admin_nome
            professor.ativo = True
            # Nunca redefine a senha de um admin existente (evita reset em cada deploy).
            print("Sucesso: Usuário professor já existente (senha preservada).")

        # 2. CONFIGURAÇÕES DO SITE
        configs_padrao = {
            'nome_professor': 'Everson Vicktor Silva Silveira',
            'idade_professor': '22 anos. Estudante de Sistemas de Informação',
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
        if Turma.query.count() == 0:
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
        if Plano.query.count() == 0:
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
        if Depoimento.query.count() == 0:
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
        seed_demo = os.environ.get('SEED_DEMO', '1').lower() not in ('0', 'false', 'no')
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

        db.session.commit()
        print("\n=== BANCO DE DADOS POPULADO COM SUCESSO! ===")
        print(f"Professor (Admin): {admin_email}")
        if seed_demo:
            print("Aluno de demonstração: aluno@beachtennis.com / aluno123")

if __name__ == '__main__':
    seed_database()
