# Beach Tennis Web

Plataforma de gestão para professor de Beach Tennis: alunos, turmas, aulas,
presenças, exercícios, avaliações técnicas com evolução por categoria, site
público e relatórios em PDF.

## Stack

- Python 3.11 + Flask 3
- SQLAlchemy / Flask-Migrate (SQLite no desenvolvimento, PostgreSQL em produção)
- Chart.js para os gráficos de evolução
- ReportLab para os relatórios em PDF
- Gunicorn no Render ou Vercel Functions no Vercel

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

O projeto funciona com qualquer PostgreSQL padrão. As opções gratuitas mais
comuns são **Neon** e **Supabase**.

### Neon

1. Crie uma conta e um projeto no Neon (https://neon.tech).
2. Copie a **connection string** (use a opção *Pooled connection* e mantenha
   `?sslmode=require`).
3. No servidor, configure `DATABASE_URL` com essa string.

### Supabase (alternativa)

1. Crie um projeto em https://supabase.com/dashboard.
2. Em **Project Settings → Database → Connection string**, escolha
   **Session pooler** (porta **5432**).
   - Use o session pooler, não a conexão direta: o Render não suporta IPv6 e a
     conexão direta do Supabase é IPv6 por padrão.
   - O session pooler preserva sessão e prepared statements, que é o modo mais
     seguro para este app com psycopg2/SQLAlchemy.
3. Copie a string no formato
   `postgresql://postgres.[PROJECT-REF]:[SENHA]@aws-0-[REGIAO].pooler.supabase.com:5432/postgres?sslmode=require`.
   Se a senha tiver caracteres especiais (`@`, `#`, `%`), URL-encode ou gere uma
   senha só com letras e números.
4. Configure `DATABASE_URL` no Render.

Projetos gratuitos do Supabase pausam após 7 dias sem atividade. Um acesso ao
site de vez em quando mantém o projeto ativo; se pausar, basta clicar em
**Resume project** no dashboard. O Neon suspende por inatividade, mas retoma
automaticamente na primeira conexão.

Exemplo de URL:

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

O projeto já está com o Git inicializado localmente na branch `main`. Falta
apenas criar o repositório remoto e enviar:

```bash
git add .
git commit -m "Atualizacoes do projeto"   # se houver mudancas pendentes
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

## Deploy no Vercel

O projeto está preparado para o Vercel:

- `wsgi.py` é o entrypoint detectado pelo runtime Python (Flask).
- `vercel.json` define `maxDuration` e roda `scripts/build_vercel.py`, que copia
  `app/static` para `public/static` (o Vercel não serve o `static_folder` do
  Flask).
- `.python-version` fixa Python 3.12.
- Uploads usam **Vercel Blob** quando `BLOB_STORE_ID`/`BLOB_READ_WRITE_TOKEN`
  estão presentes; localmente/Render continuam salvando em disco.
- Não há start command: as migrações e o seed são executados à parte (workflow
  `Inicializar banco online` ou comandos locais).

> O plano **Hobby do Vercel é restrito a uso não comercial**. Como este site
> divulga aulas e planos, o uso comercial exige o plano **Pro** (ou outro host,
> como o Render). O deploy técnico abaixo funciona nos dois planos.

### 1. Importar o projeto

1. Acesse https://vercel.com/new e importe o repositório
   `Werwersson/beach-tennis-web`.
2. Framework preset: **Flask** (ou deixe o Vercel detectar `wsgi.py`).
3. Ainda não faça o deploy final; primeiro crie o banco e o storage.

### 2. Banco PostgreSQL (Neon pelo Vercel)

1. No projeto do Vercel, abra **Storage → Create Database → Neon**.
2. Escolha a região e o plano gratuito.
3. Conecte o banco ao projeto nas environments **Production** e **Preview**.
   O Vercel injeta `DATABASE_URL` (pooler) e `DATABASE_URL_UNPOOLED` (direto).

A aplicação usa `DATABASE_URL`. Para migrações, use a URL **unpooled**.

### 3. Uploads (Vercel Blob)

1. **Storage → Create Database/Store → Blob**.
2. Escolha acesso **Public** (as imagens do site são públicas).
3. Conecte o store ao projeto. O Vercel injeta `BLOB_STORE_ID` e o token OIDC;
   o SDK `vercel-blob` cuida da autenticação em produção.

### 4. Variáveis de ambiente

Em **Settings → Environment Variables**, configure:

```env
FLASK_ENV=production
SECRET_KEY=<gere com python -c "import secrets; print(secrets.token_hex(32))">
ADMIN_EMAIL=professor@beachtennis.com
SEED_DEMO=0
```

`DATABASE_URL` e as variáveis do Blob são injetadas pelos Storage integrations.
`ADMIN_PASSWORD` não é necessária em runtime; ela é usada só na inicialização.

### 5. Inicializar o banco

O Vercel não executa `flask db upgrade`/`seed` sozinho. Use o workflow do GitHub:

1. Em **GitHub → Settings → Secrets and variables → Actions**, crie:
   - `DATABASE_URL`: a URL **unpooled** do banco
   - `SECRET_KEY`: a mesma chave do Vercel
   - `ADMIN_PASSWORD`: senha forte do primeiro admin
2. Vá em **Actions → Inicializar banco online → Run workflow**.
3. O workflow aplica as migrações e, se marcado, cria o admin e o conteúdo
   inicial. Com `SEED_DEMO=0`, não cria aluno, turmas, planos nem depoimentos
   de exemplo (apenas conquistas, modalidades e configurações base).

Alternativa: rode localmente com a URL unpooled:

```bash
export FLASK_ENV=production
export SECRET_KEY="..."
export DATABASE_URL="postgresql://..."
export ADMIN_EMAIL="professor@beachtennis.com"
export ADMIN_PASSWORD="senha-forte"
export SEED_DEMO=0
python -m flask --app wsgi db upgrade
python -m flask --app wsgi seed
```

### 6. Deploy

Faça o deploy/redeploy no Vercel. A URL será algo como
`https://beach-tennis-web.vercel.app`. Entre com `ADMIN_EMAIL` /
`ADMIN_PASSWORD` definidos na inicialização.

## Alternativa: Render + Neon

[![Deploy to Render](https://render.com/images/deploy-to-render-button.svg)](https://render.com/deploy?repo=https://github.com/Werwersson/beach-tennis-web)

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
