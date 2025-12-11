import re
from html import escape

# Разрешённые теги в Telegram
ALLOWED_TAGS = {"b", "strong", "i", "em", "u", "s", "strike", "del", "code", "pre", "a", "blockquote", "span"}
ALLOWED_ATTRS = {"href", "class"}  # class разрешяем только для tg-spoiler

# Простая регулярка для тегов
TAG_RE = re.compile(r"</?([a-zA-Z0-9]+)([^>]*)>", re.IGNORECASE)

def _clean_attrs(attrs: str) -> str:
    # Оставим только href и class, экранируем значения
    out = ""
    for m in re.finditer(r'([a-zA-Z0-9_-]+)\s*=\s*"([^"]*)"', attrs):
        name, val = m.group(1).lower(), m.group(2)
        if name in ALLOWED_ATTRS:
            # разрешаем только span class="tg-spoiler" или любой class (можно ограничить)
            if name == "class":
                # безопасно оставить только tg-spoiler
                if "tg-spoiler" in val:
                    out += f' class="{escape(val)}"'
                # иначе — отбрасываем class
            else:
                out += f' {name}="{escape(val)}"'
    return out

def sanitize_html(text: str) -> str:
    """
    Очищает HTML-теги, оставляет только разрешённые теги и атрибуты
    и заменяет запрещённые теги на безопасные аналоги.
    """
    if not text:
        return ""

    # 1) Заменяем заголовки <h1..h6> на <b>ЗАГОЛОВОК</b>\n
    text = re.sub(r"</?h[1-6][^>]*>", "", text, flags=re.IGNORECASE)
    # 2) Заменяем <p> на <br>
    text = re.sub(r"</?p[^>]*>", "<br>", text, flags=re.IGNORECASE)
    # 3) Убираем <br> дубли
    text = re.sub(r"(?:\s*<br>\s*){2,}", "<br>", text, flags=re.IGNORECASE)

    # 4) Проходим по каждому тегу и либо оставляем очищенный, либо экранируем
    def _replace_tag(match):
        tag_name = match.group(1).lower()
        attrs = match.group(2) or ""
        is_end = match.group(0).startswith("</")
        if tag_name not in ALLOWED_TAGS:
            # если закрывающий тег запрещён — убираем его (не эскейпим чтобы не поставить сырой '<')
            return ""
        # разрешённые теги: чистим атрибуты
        clean_attrs = _clean_attrs(attrs)
        if is_end:
            return f"</{tag_name}>"
        else:
            return f"<{tag_name}{clean_attrs}>"

    text = TAG_RE.sub(_replace_tag, text)

    # 5) Экранируем любые оставшиеся угловые скобки, которые не часть тегов
    text = re.sub(r"<(?=[^a-zA-Z/])", "&lt;", text)
    text = re.sub(r"(?<![a-zA-Z0-9;])>", "&gt;", text)

    # 6) Удалим пустые теги <b></b> и т.д.
    text = re.sub(r"<([a-z0-9]+)>\s*</\1>", "", text, flags=re.IGNORECASE)

    return text