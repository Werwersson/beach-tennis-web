import sys, re
sys.path.insert(0, '.')
from app import create_app

app = create_app()
app.config['WTF_CSRF_ENABLED'] = False
client = app.test_client()

with app.app_context():
    r = client.get('/')
    html = r.data.decode('utf-8')
    # Find all stat-number occurrences in raw HTML
    idx = 0
    while True:
        pos = html.find('stat-number', idx)
        if pos == -1:
            break
        snippet = html[pos:pos+200]
        print("SNIPPET:", repr(snippet[:200]))
        idx = pos + 1

