def is_cor_escura(hex_color):
    """
    Retorna True se a cor for escura (necessitando texto claro para contraste),
    ou False se a cor for clara (necessitando texto escuro).
    Baseado na fórmula padrão ITU-R BT.709 de luminosidade perceptível.
    """
    if not hex_color or not isinstance(hex_color, str):
        return False
    hex_color = hex_color.strip().lstrip('#')
    if len(hex_color) == 3:
        hex_color = ''.join([c * 2 for c in hex_color])
    if len(hex_color) != 6:
        return False
    try:
        r = int(hex_color[0:2], 16)
        g = int(hex_color[2:4], 16)
        b = int(hex_color[4:6], 16)
        brilho = (r * 299 + g * 587 + b * 114) / 1000
        return brilho < 155
    except ValueError:
        return False
