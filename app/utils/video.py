import re


def extrair_youtube_id(url):
    """
    Extrai o ID de 11 caracteres de qualquer formato de URL do YouTube:
    - https://www.youtube.com/watch?v=VIDEO_ID
    - https://youtu.be/VIDEO_ID
    - https://www.youtube.com/embed/VIDEO_ID
    - https://www.youtube.com/shorts/VIDEO_ID
    - https://m.youtube.com/watch?v=VIDEO_ID
    """
    if not url:
        return None
    url = url.strip()
    patterns = [
        r'(?:v=|\/v\/|embed\/|shorts\/)([0-9A-Za-z_-]{11})',
        r'youtu\.be\/([0-9A-Za-z_-]{11})',
    ]
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)
    return None


def converter_para_embed(url):
    """
    Converte qualquer URL de vídeo para o formato embed permitido em iframes.
    Resolve o erro 'A conexão com www.youtube.com foi recusada' (X-Frame-Options: SAMEORIGIN).
    """
    if not url:
        return ''
    url = url.strip()

    # 1. YouTube
    yt_id = extrair_youtube_id(url)
    if yt_id:
        return f"https://www.youtube.com/embed/{yt_id}"

    # 2. Vimeo
    vimeo_match = re.search(r'vimeo\.com\/(?:video\/)?([0-9]+)', url)
    if vimeo_match:
        vimeo_id = vimeo_match.group(1)
        return f"https://player.vimeo.com/video/{vimeo_id}"

    return url
