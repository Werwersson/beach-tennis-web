"""Categorias competitivas do beach tennis e regras de comparação.

A nota de uma avaliação é atribuída DENTRO da categoria do atleta, ou seja, ela
compara o aluno com os adversários daquela categoria. Quando o atleta sobe de
categoria (ex.: D → C), a mesma qualidade técnica tende a receber uma nota menor,
porque a régua de comparação subiu.

Para que o gráfico de evolução não confunda essa queda com retrocesso, o sistema
calcula o **Índice Técnico** (0 a 100) aplicando o peso da categoria:

    índice = (nota_média / 10) * peso_da_categoria * 100

Com isso:
- a **Nota na Categoria** (0 a 10) mostra exatamente a nota atribuída pelo
  professor, inclusive caindo na promoção de categoria;
- a **Curva de Aprendizado** (índice 0 a 100) desconta a diferença de dificuldade
  entre as categorias e mostra o ganho técnico real do atleta.

Os pesos são intencionalmente simples e podem ser ajustados neste único lugar.
"""

CATEGORIAS_BEACH_TENNIS = [
    ('D', 'Categoria D'),
    ('C', 'Categoria C'),
    ('B', 'Categoria B'),
    ('A', 'Categoria A'),
    ('Open', 'Open'),
]

# Peso de dificuldade de cada categoria (0 a 1).
# Uma nota 10,0 em Open equivale ao índice 100; a mesma nota em D vale 70.
CATEGORIA_PESOS = {
    'D': 0.70,
    'C': 0.80,
    'B': 0.88,
    'A': 0.95,
    'Open': 1.00,
}

# Ordem crescente das categorias (D é a base, Open é o topo).
CATEGORIA_ORDEM = {'D': 1, 'C': 2, 'B': 3, 'A': 4, 'Open': 5}

CATEGORIA_PADRAO = 'D'


def normalizar_categoria(valor, padrao=CATEGORIA_PADRAO):
    """Retorna a sigla canônica da categoria (D, C, B, A ou Open)."""
    if valor is None:
        return padrao
    texto = str(valor).strip()
    if texto in CATEGORIA_PESOS:
        return texto
    for sigla in CATEGORIA_PESOS:
        if sigla.lower() == texto.lower():
            return sigla
    return padrao


def categoria_label(valor):
    """Rótulo amigável da categoria (ex.: 'Categoria C')."""
    sigla = normalizar_categoria(valor)
    return dict(CATEGORIAS_BEACH_TENNIS).get(sigla, f'Categoria {sigla}')


def categoria_curta(valor):
    """Sigla da categoria (ex.: 'C')."""
    return normalizar_categoria(valor)


def peso_categoria(valor):
    """Peso de dificuldade da categoria (0 a 1)."""
    return CATEGORIA_PESOS[normalizar_categoria(valor)]


def ordem_categoria(valor):
    """Posição da categoria na escada D < C < B < A < Open."""
    return CATEGORIA_ORDEM[normalizar_categoria(valor)]


def calcular_indice(media, categoria):
    """Converte uma média (0 a 10) da categoria em Índice Técnico (0 a 100)."""
    if media is None:
        return 0.0
    return round(float(media) * peso_categoria(categoria) * 10, 1)
