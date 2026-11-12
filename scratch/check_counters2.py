import sys
sys.path.insert(0, '.')
from app import create_app

app = create_app()
app.config['WTF_CSRF_ENABLED'] = False
client = app.test_client()

with app.app_context():
    r = client.get('/')
    html = r.data.decode('utf-8')
    
    # Verificar data-targets
    import re
    targets = re.findall(r'data-target="(\d+)"', html)
    print("data-targets encontrados:", targets)
    
    # Verificar que IntersectionObserver está no JS
    if 'IntersectionObserver' in html:
        print("OK: IntersectionObserver presente no HTML")
    else:
        print("ERRO: IntersectionObserver ausente!")
    
    # Verificar que nao tem mais animacao imediata sem observer
    if 'entry.isIntersecting' in html:
        print("OK: animacao so dispara quando visivel")
    
    # Verificar contagem de conquistas via rota
    print("\nStatus:", r.status_code)

