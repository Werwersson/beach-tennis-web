import sys
sys.path.insert(0, '.')
from app import create_app
from app.models.configuracao import ConfiguracaoSite

app = create_app()
app.config['WTF_CSRF_ENABLED'] = False
client = app.test_client()

with app.app_context():
    wa = ConfiguracaoSite.query.filter_by(chave='whatsapp').first()
    ig = ConfiguracaoSite.query.filter_by(chave='instagram').first()
    print(f"WhatsApp no banco: {wa.valor if wa else 'NAO ENCONTRADO'}")
    print(f"Instagram no banco: {ig.valor if ig else 'NAO ENCONTRADO'}")

    r = client.get('/')
    html = r.data.decode('utf-8')

    import re
    # Checar link gerado do whatsapp
    wa_links = re.findall(r'href="(https://wa\.me/[^"]+)"', html)
    ig_links = re.findall(r'href="(https://instagram\.com/[^"]+)"', html)

    print(f"\nLinks WhatsApp na pagina ({len(wa_links)}):")
    for l in set(wa_links):
        print(f"  {l}")

    print(f"\nLinks Instagram na pagina ({len(ig_links)}):")
    for l in set(ig_links):
        print(f"  {l}")

    # Instagram exibido (texto visivel)
    ig_display = re.findall(r'bi-instagram[^<]*</i>([^<]+)', html)
    print(f"\nInstagram exibido: {ig_display}")

