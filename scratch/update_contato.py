import sys
sys.path.insert(0, '.')
from app import create_app
from app.models.configuracao import ConfiguracaoSite
from app.extensions import db

app = create_app()
with app.app_context():
    updates = {
        'whatsapp': '5573999969999',
        'instagram': 'eversonvicktor',
    }
    for chave, valor in updates.items():
        cfg = ConfiguracaoSite.query.filter_by(chave=chave).first()
        if cfg:
            cfg.valor = valor
            print(f'Atualizado: {chave} = {valor}')
        else:
            novo = ConfiguracaoSite(chave=chave, valor=valor)
            db.session.add(novo)
            print(f'Criado: {chave} = {valor}')
    db.session.commit()
    print('Salvo com sucesso!')

