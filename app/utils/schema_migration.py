from sqlalchemy import text, inspect
from ..extensions import db


def garantir_esquema_banco():
    """
    Garante que todas as tabelas e colunas necessárias existam no banco de dados.
    Resolve o erro 'UndefinedColumn' no PostgreSQL (Neon/Supabase/Vercel Postgres)
    e SQLite, onde db.create_all() não adiciona colunas a tabelas já criadas.
    """
    try:
        # 1. Cria tabelas que ainda não existem
        db.create_all()
    except Exception:
        try:
            db.session.rollback()
        except Exception:
            pass

    try:
        inspector = inspect(db.engine)
        tables = inspector.get_table_names()
        dialect = db.engine.dialect.name.lower()
        is_postgres = 'postgres' in dialect

        # 2. Atualiza tabela 'alunos' com 'cor_fundo' se faltar
        if 'alunos' in tables:
            cols_alunos = [c['name'] for c in inspector.get_columns('alunos')]
            if 'cor_fundo' not in cols_alunos:
                try:
                    with db.engine.begin() as conn:
                        if is_postgres:
                            conn.execute(text("ALTER TABLE alunos ADD COLUMN IF NOT EXISTS cor_fundo VARCHAR(30) DEFAULT '#F8F6F2';"))
                        else:
                            conn.execute(text("ALTER TABLE alunos ADD COLUMN cor_fundo VARCHAR(30) DEFAULT '#F8F6F2';"))
                except Exception:
                    pass

        # 3. Atualiza tabela 'partidas' com colunas faltantes
        if 'partidas' in tables:
            cols_partidas = [c['name'] for c in inspector.get_columns('partidas')]
            comandos_partidas = [
                ('status', "VARCHAR(20) DEFAULT 'aprovada'"),
                ('criada_por_aluno_id', "INTEGER"),
                ('comentario_professor', "TEXT"),
                ('validada_em', "TIMESTAMP" if is_postgres else "DATETIME"),
                ('placar_detalhado', "VARCHAR(100)"),
                ('duracao_minutos', "INTEGER"),
                ('observacoes', "TEXT"),
                ('set4_dupla1', "INTEGER DEFAULT 0"),
                ('set4_dupla2', "INTEGER DEFAULT 0"),
                ('video_url', "VARCHAR(200)"),
            ]

            for col_name, col_def in comandos_partidas:
                if col_name not in cols_partidas:
                    try:
                        with db.engine.begin() as conn:
                            if is_postgres:
                                conn.execute(text(f"ALTER TABLE partidas ADD COLUMN IF NOT EXISTS {col_name} {col_def};"))
                            else:
                                conn.execute(text(f"ALTER TABLE partidas ADD COLUMN {col_name} {col_def};"))
                    except Exception:
                        pass

            if is_postgres:
                try:
                    with db.engine.begin() as conn:
                        conn.execute(text("CREATE INDEX IF NOT EXISTS idx_partidas_status ON partidas (status);"))
                        conn.execute(text("CREATE INDEX IF NOT EXISTS idx_partidas_criada_por_aluno_id ON partidas (criada_por_aluno_id);"))
                except Exception:
                    pass

        # 3. Atualiza tabela 'pontos_partida' com colunas faltantes
        if 'pontos_partida' in tables:
            cols_pontos = [c['name'] for c in inspector.get_columns('pontos_partida')]
            comandos_pontos = [
                ('set_num', "INTEGER DEFAULT 1"),
                ('placar_texto', "VARCHAR(50)"),
                ('tipo_golpe', "VARCHAR(80)"),
                ('posicao_sacador', "VARCHAR(20)"),
                ('direcao_saque', "VARCHAR(30)"),
                ('qualidade_saque', "VARCHAR(20)"),
                ('direcao_devolucao', "VARCHAR(30)"),
                ('qualidade_devolucao', "VARCHAR(20)"),
                ('saque_dificil', "BOOLEAN DEFAULT FALSE" if is_postgres else "BOOLEAN DEFAULT 0"),
                ('situacao_adicional', "VARCHAR(50)"),
                ('duracao_ponto', "VARCHAR(20)"),
                ('x_origem', "FLOAT"),
                ('y_origem', "FLOAT"),
                ('x_destino', "FLOAT"),
                ('y_destino', "FLOAT"),
                ('x_quique', "FLOAT"),
                ('y_quique', "FLOAT"),
                ('origem_x', "FLOAT"),
                ('origem_y', "FLOAT"),
                ('destino_x', "FLOAT"),
                ('destino_y', "FLOAT"),
                ('descricao_lance', "VARCHAR(250)"),
            ]

            for col_name, col_def in comandos_pontos:
                if col_name not in cols_pontos:
                    try:
                        with db.engine.begin() as conn:
                            if is_postgres:
                                conn.execute(text(f"ALTER TABLE pontos_partida ADD COLUMN IF NOT EXISTS {col_name} {col_def};"))
                            else:
                                conn.execute(text(f"ALTER TABLE pontos_partida ADD COLUMN {col_name} {col_def};"))
                    except Exception:
                        pass

            # Fallback explícito e direto para saque_dificil (garante mesmo se cache de colunas falhar)
            try:
                with db.engine.begin() as conn:
                    if is_postgres:
                        conn.execute(text("ALTER TABLE pontos_partida ADD COLUMN IF NOT EXISTS saque_dificil BOOLEAN DEFAULT FALSE;"))
                    else:
                        conn.execute(text("ALTER TABLE pontos_partida ADD COLUMN saque_dificil BOOLEAN DEFAULT 0;"))
            except Exception:
                pass

        # 4. Migração e normalização de vídeos da galeria para o formato de embed
        if 'galeria_itens' in tables:
            try:
                from app.utils.video import converter_para_embed
                with db.engine.begin() as conn:
                    res = conn.execute(text("SELECT id, url_video FROM galeria_itens WHERE url_video IS NOT NULL;")).fetchall()
                    for row in res:
                        item_id, url = row[0], row[1]
                        if url:
                            url_embed = converter_para_embed(url)
                            if url_embed != url:
                                conn.execute(
                                    text("UPDATE galeria_itens SET url_video = :url WHERE id = :id"),
                                    {'url': url_embed, 'id': item_id}
                                )
            except Exception:
                pass

    except Exception:
        try:
            db.session.rollback()
        except Exception:
            pass
