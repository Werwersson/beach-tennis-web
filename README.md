# Beach Tennis Web

Plataforma de gestão para professor de Beach Tennis: alunos, turmas, aulas,
presenças, exercícios, avaliações técnicas com evolução por categoria, site
público e relatórios em PDF.

## Stack

- Python 3.11 + Flask 3
- SQLAlchemy / Flask-Migrate (SQLite no desenvolvimento, PostgreSQL em produção)
- Chart.js para os gráficos de evolução
- ReportLab para os relatórios em PDF
- Gunicorn para servir em produção

## Rodando localmente

```bash
python -m venv .venv
# Windows
.venv\Scripts\activate
# Linux/macOS
source .venv/bin/activate

pip install -r requirements.txt
copy .env.example .env   # Windows
# cp .env.example .env   # Linux/macOS
```

No `.env` local, use:

```env
FLASK_ENV=development
SECRET_KEY=dev-secret-local
DATABASE_URL=sqlite:///beach_tennis.db
SEED_DEMO=1
```

Depois:

```bash
python run.py
```

O `run.py` cria as tabelas e popula os dados iniciais (incluindo o aluno de
demonstração Lucas Silva, com a curva D → C). Acesse `http://127.0.0.1:5000`.

- Professor: `professor@beachtennis.com` / `admin123`
- Aluno demo: `aluno@beachtennis.com` / `aluno123`

> Troque essas senhas antes de publicar o site.

## Testes

```bash
python scratch/test_categoria_evolucao.py
python scratch/test_aluno_e_charts.py
python scratch/test_etapa5.py
```

Os testes que alteram dados usam cópias temporárias do banco quando executados
com `DATABASE_URL` apontando para um arquivo temporário.

## Banco de dados online (PostgreSQL)

O projeto já está preparado para PostgreSQL. A opção gratuita recomendada é o
**Neon** (https://neon.tech):

1. Crie uma conta e um projeto no Neon.
2. Copie a **connection string** (use a opção *Pooled connection* e mantenha
   `?sslmode=require`).
3. No servidor, configure `DATABASE_URL` com essa string.

Exemplo:

```env
DATABASE_URL=postgresql://usuario:senha@ep-xyz-pooler.us-east-2.aws.neon.tech/neondb?sslmode=require
```

O `config.py` normaliza automaticamente URLs antigas `postgres://` para
`postgresql://`.

### Migrações

O schema é versionado com Alembic:

```bash
python -m flask --app wsgi db upgrade
```

Para criar uma nova migração depois de alterar modelos:

```bash
python -m flask --app wsgi db migrate -m "descricao da mudanca"
python -m flask --app wsgi db upgrade
```

Em produção, as migrações e o seed rodam automaticamente no start command
(vide `Procfile` e `render.yaml`). O seed é idempotente e **não redefine** a
senha de um admin existente.

## Publicando no GitHub

O projeto não tem repositório Git inicializado. Na raiz:

```bash
git init
git add .
git commit -m "Beach Tennis Web: plataforma completa com evolução por categoria"
```

Crie o repositório no GitHub e envie. Com o GitHub CLI autenticado:

```bash
gh auth login
gh repo create beach-tennis-web --public --source=. --remote=origin --push
```

Sem o `gh`:

```bash
git branch -M main
git remote add origin https://github.com/SEU-USUARIO/beach-tennis-web.git
git push -u origin main
```

O `.gitignore` já protege `.env`, bancos SQLite, `instance/`, uploads e
`__pycache__`. **Nunca** comite o `.env` nem o banco local.

## Deploy no Render + Neon

1. Suba o código no GitHub.
2. Crie o banco no Neon e copie a connection string.
3. No Render, escolha **New → Blueprint** e selecione o repositório. O
   `render.yaml` já define o serviço web, o build e o start command.
4. Preencha as variáveis solicitadas:
   - `DATABASE_URL`: connection string do Neon
   - `ADMIN_PASSWORD`: senha forte para o primeiro acesso
5. Clique em **Apply**. O primeiro deploy executa:
   - `python -m flask --app wsgi db upgrade`
   - `python -m flask --app wsgi seed`
   - `gunicorn wsgi:app`

Se preferir criar o serviço manualmente no Render:

- **Runtime:** Python
- **Build command:** `pip install -r requirements.txt`
- **Start command:**
  `python -m flask --app wsgi db upgrade && python -m flask --app wsgi seed && gunicorn wsgi:app --workers 2 --bind 0.0.0.0:$PORT`
- **Variáveis:** `FLASK_ENV=production`, `SECRET_KEY` (gerada), `DATABASE_URL`,
  `ADMIN_EMAIL`, `ADMIN_PASSWORD`, `SEED_DEMO=0`, `PYTHON_VERSION=3.11.9`.

Depois do deploy, acesse a URL e entre com `ADMIN_EMAIL` / `ADMIN_PASSWORD`.

### Trocar a senha do admin

Atualize `ADMIN_PASSWORD` no painel do Render e execute, no Shell do serviço:

```bash
python -m flask --app wsgi set-admin-password
```

Se o Shell não estiver disponível no plano gratuito, rode o comando
temporariamente no start command e remova depois.

## Uploads de imagens

Por padrão, as imagens vão para `app/static/uploads` (ou para `UPLOAD_FOLDER`).
No plano gratuito do Render o disco é **efêmero**: as imagens enviadas são
perdidas a cada deploy.

Opções:

- Render Disk (pago): monte em `/var/data` e configure
  `UPLOAD_FOLDER=/var/data/uploads`.
- Railway com volume persistente: configure `UPLOAD_FOLDER=/data/uploads`.
- Cloudinary/S3 (evolução futura): armazenar as imagens fora do servidor.

## Alternativa: Railway

1. Crie um projeto no Railway a partir do repositório do GitHub.
2. Adicione o plugin **PostgreSQL**.
3. Configure as variáveis `FLASK_ENV`, `SECRET_KEY`, `ADMIN_EMAIL`,
   `ADMIN_PASSWORD`, `SEED_DEMO=0` e `UPLOAD_FOLDER`.
4. O `Procfile` já contém o start command com migrações, seed e Gunicorn.

## Estrutura

```text
app/
  blueprints/      rotas (público, auth, admin, aluno)
  models/          modelos SQLAlchemy
  templates/       Jinja2
  static/          CSS, JS e uploads
  utils/           analytics, PDF, decorators
migrations/        versões Alembic
seed.py            dados iniciais idempotentes
run.py             servidor local
wsgi.py            entrada de produção (Gunicorn)
render.yaml        blueprint do Render
Procfile           start command para Render/Railway/Heroku
```

## Segurança

- Gere `SECRET_KEY` com `python -c "import secrets; print(secrets.token_hex(32))"`.
- Use uma senha forte em `ADMIN_PASSWORD`.
- Mantenha `FLASK_ENV=production` no servidor (`DEBUG` desligado).
- O seed não recria nem reseta a senha do admin em deploys seguintes.
- Em produção, o app exige `SECRET_KEY` e `DATABASE_URL`; sem elas o processo
  falha com uma mensagem clara.
