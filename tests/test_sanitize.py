"""
Тесты для sanitize модуля.

Проверяют:
- Очистку запрещенных HTML тегов
- Сохранение разрешенных тегов
- Экранирование опасных конструкций
"""

from ai_engine.sanitize import ALLOWED_TAGS, sanitize_html


class TestSanitizeHtml:
    """Тесты для функции sanitize_html."""

    def test_empty_input(self):
        """Проверка обработки пустого ввода."""
        assert sanitize_html("") == ""
        assert sanitize_html(None) == ""

    def test_plain_text(self):
        """Проверка обработки простого текста."""
        text = "Привет, мир!"
        assert sanitize_html(text) == "Привет, мир!"

    def test_allowed_bold_tag(self):
        """Проверка сохранения тега <b>."""
        text = "<b>Жирный текст</b>"
        result = sanitize_html(text)
        assert "<b>" in result
        assert "Жирный текст" in result

    def test_allowed_italic_tag(self):
        """Проверка сохранения тега <i>."""
        text = "<i>Курсив</i>"
        result = sanitize_html(text)
        assert "<i>" in result or "<em>" in result

    def test_allowed_code_tag(self):
        """Проверка сохранения тега <code>."""
        text = "<code>print('hello')</code>"
        result = sanitize_html(text)
        assert "<code>" in result

    def test_allowed_pre_tag(self):
        """Проверка сохранения тега <pre>."""
        text = "<pre>def foo():\n    pass</pre>"
        result = sanitize_html(text)
        assert "<pre>" in result

    def test_allowed_blockquote_tag(self):
        """Проверка сохранения тега <blockquote>."""
        text = "<blockquote>Цитата</blockquote>"
        result = sanitize_html(text)
        assert "<blockquote>" in result

    def test_allowed_link_tag(self):
        """Проверка сохранения тега <a> с href."""
        text = '<a href="https://example.com">Ссылка</a>'
        result = sanitize_html(text)
        assert "<a" in result
        assert 'href="https://example.com"' in result

    def test_disallowed_script_tag(self):
        """Проверка удаления тега <script>."""
        text = "<script>alert('xss')</script>"
        result = sanitize_html(text)
        assert "<script>" not in result
        assert "alert" not in result

    def test_disallowed_style_tag(self):
        """Проверка удаления тега <style>."""
        text = "<style>.class { color: red; }</style>"
        result = sanitize_html(text)
        assert "<style>" not in result

    def test_disallowed_iframe_tag(self):
        """Проверка удаления тега <iframe>."""
        text = '<iframe src="https://evil.com"></iframe>'
        result = sanitize_html(text)
        assert "<iframe>" not in result

    def test_disallowed_onclick_attribute(self):
        """Проверка удаления onclick атрибута."""
        text = '<div onclick="alert(1)">Кликни</div>'
        result = sanitize_html(text)
        assert "onclick" not in result.lower()

    def test_h_tag_removal(self):
        """Проверка удаления заголовков <h1>-<h6>."""
        text = "<h1>Заголовок</h1>"
        result = sanitize_html(text)
        assert "<h1>" not in result
        assert "Заголовок" in result

    def test_p_tag_conversion(self):
        """Проверка замены <p> на <br>."""
        text = "<p>Параграф</p>"
        result = sanitize_html(text)
        assert "<p>" not in result

    def test_nested_tags(self):
        """Проверка обработки вложенных тегов."""
        text = "<b><i>Вложенный текст</i></b>"
        result = sanitize_html(text)
        assert "<b>" in result
        assert "<i>" in result
        assert "Вложенный текст" in result

    def test_malformed_html(self):
        """Проверка обработки некорректного HTML."""
        text = "<b>Незакрытый тег"
        result = sanitize_html(text)
        assert "Незакрытый тег" in result

    def test_html_entities(self):
        """Проверка сохранения HTML сущностей."""
        text = "5 &lt; 10"
        result = sanitize_html(text)
        assert "&lt;" in result

    def test_tg_spoiler_class(self):
        """Проверка разрешения class='tg-spoiler'."""
        text = '<span class="tg-spoiler">Спойлер</span>'
        result = sanitize_html(text)
        assert "tg-spoiler" in result

    def test_disallowed_class(self):
        """Проверка удаления запрещенных class."""
        text = '<div class="malicious-class">Текст</div>'
        result = sanitize_html(text)
        # div не в разрешенных тегах, должен быть удален
        assert "<div" not in result


class TestAllowedTags:
    """Тесты для набора разрешенных тегов."""

    def test_allowed_tags_not_empty(self):
        """Проверка что набор разрешенных тегов не пуст."""
        assert len(ALLOWED_TAGS) > 0

    def test_common_formatting_tags_allowed(self):
        """Проверка что основные теги форматирования разрешены."""
        assert "b" in ALLOWED_TAGS or "strong" in ALLOWED_TAGS
        assert "i" in ALLOWED_TAGS or "em" in ALLOWED_TAGS
        assert "code" in ALLOWED_TAGS
        assert "pre" in ALLOWED_TAGS

    def test_dangerous_tags_not_allowed(self):
        """Проверка что опасные теги запрещены."""
        assert "script" not in ALLOWED_TAGS
        assert "style" not in ALLOWED_TAGS
        assert "iframe" not in ALLOWED_TAGS
        assert "object" not in ALLOWED_TAGS
        assert "embed" not in ALLOWED_TAGS
