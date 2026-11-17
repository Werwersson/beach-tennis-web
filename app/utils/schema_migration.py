from sqlalchemy import text, inspect
from ..extensions import db


def garantir_esquema_banco():
    """
    Garante que todas as tabelas e colunas necessárias existam no banco de dados.
    Resolve o erro 'UndefinedColumn: column partidas.status does not exist' no PostgreSQL
    (Neon/Supabase/Vercel Postgres) e SQLite, onde db.create_all() não adiciona colunas a tabelas
    que já foram criadas anteriormente.
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

        # 2. Atualiza tabela 'partidas' com colunas faltantes
        if 'partidas' in tables:
            cols_partidas = [c['name'] for c in inspector.get_columns('partidas')]
            comandos_partidas = [
                ('status', "VARCHAR(20) DEFAULT 'aprovada'"),
                ('criada_por_aluno_id', "INTEGER"),
                ('comentario_professor', "TEXT"),
                ('validada_em', "TIMESTAMP" if 'postgres' in dialect else "DATETIME"),
                ('placar_detalhado', "VARCHAR(100)"),
                ('duracao_minutos', "INTEGER"),
                ('observacoes', "TEXT"),
            ]

            with db.engine.begin() as conn:
                for col_name, col_def in comandos_partidas:
                    if col_name not in cols_partidas:
                        try:
                            if 'postgres' in dialect:
                                conn.execute(text(f"ALTER TABLE partidas ADD COLUMN IF NOT EXISTS {col_name} {col_def};"))
                            else:
                                conn.execute(text(f"ALTER TABLE partidas ADD COLUMN {col_name} {col_def};"))
                        except Exception:
                            pass

                if 'postgres' in dialect:
                    try:
                        conn.execute(text("CREATE INDEX IF NOT EXISTS idx_partidas_status ON partidas (status);"))
                        conn.execute(text("CREATE INDEX IF NOT EXISTS idx_partidas_criada_por_aluno_id ON partidas (criada_por_aluno_id);"))
                    except Exception:
                        pass

        # 3. Atualiza tabela 'pontos_partida' com colunas faltantes se necessário
        if 'pontos_partida' in tables:
            cols_pontos = [c['name'] for c in inspector.get_columns('pontos_partida')]
            comandos_pontos = [
                ('placar_texto', "VARCHAR(50)"),
                ('tipo_golpe', "VARCHAR(80)"),
                ('posicao_sacador', "VARCHAR(20)"),
                ('direcao_saque', "VARCHAR(30)"),
                ('qualidade_saque', "VARCHAR(20)"),
                ('direcao_devolucao', "VARCHAR(30)"),
                ('qualidade_devolucao', "VARCHAR(20)"),
                ('situacao_adicional', "VARCHAR(50)"),
                ('duracao_ponto', "VARCHAR(20)"),
                ('x_origem', "FLOAT"),
                ('y_origem', "FLOAT"),
                ('x_destino', "FLOAT"),
                ('y_destino', "FLOAT"),
                ('x_quique', "FLOAT"),
                ('y_quique', "FLOAT"),
            ]

            with db.engine.begin() as conn:
                for col_name, col_def in comandos_pontos:
                    if col_name not in cols_pontos:
                        try:
                            if 'postgres' in dialect:
                                conn.execute(text(f"ALTER TABLE pontos_partida ADD COLUMN IF NOT EXISTS {col_name} {col_def};"))
                            else:
                                conn.execute(text(f"ALTER TABLE pontos_partida ADD COLUMN {col_name} {col_def};"))
                        except Exception:
                            pass

    except Exception:
        try:
            db.session.rollback()
        except Exception:
            pass
