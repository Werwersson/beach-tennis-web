from datetime import date
from app import create_app
from app.blueprints.public.routes import calcular_idade_professor, get_config_dict

def test_idade_calculation():
    # Nascido em 10/03/2004
    nasc = date(2004, 3, 10)
    
    # 23/11/2026 (hoje) -> 22 anos
    assert calcular_idade_professor(nasc, date(2026, 11, 23)) == 22, "Falha em 2026-11-23"
    
    # 09/03/2027 (véspera do aniversário) -> 22 anos
    assert calcular_idade_professor(nasc, date(2027, 3, 9)) == 22, "Falha na véspera"
    
    # 10/03/2027 (aniversário de 23 anos) -> 23 anos
    assert calcular_idade_professor(nasc, date(2027, 3, 10)) == 23, "Falha no aniversário de 2027"
    
    # 10/03/2030 -> 26 anos
    assert calcular_idade_professor(nasc, date(2030, 3, 10)) == 26, "Falha em 2030"
    
    # Teste com string
    assert calcular_idade_professor('2004-03-10', date(2026, 11, 23)) == 22
    assert calcular_idade_professor('10/03/2004', date(2027, 3, 10)) == 23
    
    print("✓ Todos os testes matemáticos de calcular_idade_professor passaram com sucesso!")

def test_render_public():
    app = create_app('development')
    with app.app_context():
        client = app.test_client()
        resp = client.get('/')
        assert resp.status_code == 200, f"Status code {resp.status_code}"
        html = resp.get_data(as_text=True)
        assert "22 anos" in html, "Deveria conter '22 anos' renderizado"
        assert "Estudante de Sistemas de Informação" in html
        assert "Atleta & Professor" in html
        print("✓ Página pública renderizada corretamente com idade dinâmica de 22 anos!")

if __name__ == '__main__':
    test_idade_calculation()
    test_render_public()
