"""
Umumiy yordamchi funksiyalar.
"""
import re

_TOKEN_RE = re.compile(r"<[^>]+>|[^<]+")
_TAG_NAME_RE = re.compile(r"^</?([a-zA-Z0-9]+)")
_VOID_TAGS = {"br"}


def safe_truncate_html(text: str, limit: int, suffix: str = "…") -> str:
    """
    Telegram HTML parse-mode uchun xavfsiz qisqartirish.
    Oddiy `text[:limit]` teglarni o'rtadan kesib, "can't parse entities"
    xatosiga olib kelishi mumkin. Bu funksiya:
    - faqat ko'rinadigan matn belgilarini sanaydi (teglarni emas),
    - kesish joyi tegning ichida bo'lmasligini ta'minlaydi,
    - охирида ochiq qolgan barcha teglarni to'g'ri yopadi.
    """
    if len(text) <= limit:
        return text

    budget = max(limit - len(suffix), 0)
    out = []
    open_tags = []
    visible = 0

    for token in _TOKEN_RE.findall(text):
        if token.startswith("<"):
            m = _TAG_NAME_RE.match(token)
            name = m.group(1).lower() if m else None
            if name and name not in _VOID_TAGS:
                if token.startswith("</"):
                    if open_tags and open_tags[-1] == name:
                        open_tags.pop()
                elif not token.endswith("/>"):
                    open_tags.append(name)
            out.append(token)
            continue

        remaining = budget - visible
        if remaining <= 0:
            break
        if len(token) <= remaining:
            out.append(token)
            visible += len(token)
        else:
            out.append(token[:remaining])
            visible += remaining
            break

    result = "".join(out) + suffix
    for tag in reversed(open_tags):
        result += f"</{tag}>"
    return result
