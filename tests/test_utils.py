import re

from utils import safe_truncate_html

_TAG_RE = re.compile(r"</?[a-zA-Z0-9]+>")


def test_no_truncation_needed():
    text = "<b>Salom</b> dunyo"
    assert safe_truncate_html(text, 100) == text


def test_truncates_plain_text():
    result = safe_truncate_html("abcdefghij", 5)
    assert result == "abcd…"
    assert len(result) == 5


def test_closes_open_bold_tag():
    text = "<b>Bu juda uzun matn bo'lib, kesilishi kerak</b>"
    result = safe_truncate_html(text, 15)
    assert result.startswith("<b>")
    assert result.endswith("</b>")
    # Yopiq teglar soni ochiq teglar soniga teng bo'lishi kerak
    assert result.count("<b>") == result.count("</b>")


def test_closes_nested_tags():
    text = "<b><i>Juda uzun ichma-ich teglangan matn shu yerda davom etadi</i></b>"
    result = safe_truncate_html(text, 20)
    assert result.count("<b>") == result.count("</b>")
    assert result.count("<i>") == result.count("</i>")
    # Ichki teg avval yopilishi kerak (to'g'ri nesting)
    assert result.index("</i>") < result.index("</b>")


def test_no_stray_angle_brackets():
    text = "<b>ab</b>cdefghij"
    result = safe_truncate_html(text, 6)
    stripped = _TAG_RE.sub("", result)
    assert "<" not in stripped and ">" not in stripped


def test_empty_text():
    assert safe_truncate_html("", 10) == ""


def test_exact_limit_not_truncated():
    text = "12345"
    assert safe_truncate_html(text, 5) == text
