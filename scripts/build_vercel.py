"""Copia os arquivos estáticos para public/ no build do Vercel.

O Vercel serve arquivos estáticos a partir de public/**, e não do
app.static_folder do Flask. Este script mantém o CSS, JS e imagens em
public/static sem duplicar os uploads locais.
"""
import shutil
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
ORIGEM = RAIZ / 'app' / 'static'
DESTINO = RAIZ / 'public' / 'static'


def main():
    if not ORIGEM.exists():
        raise SystemExit(f'Pasta de estáticos não encontrada: {ORIGEM}')

    if DESTINO.exists():
        shutil.rmtree(DESTINO)
    DESTINO.parent.mkdir(parents=True, exist_ok=True)

    shutil.copytree(
        ORIGEM,
        DESTINO,
        ignore=shutil.ignore_patterns('uploads', '__pycache__', '*.pyc'),
    )
    print(f'Estáticos copiados para {DESTINO}')


if __name__ == '__main__':
    main()
