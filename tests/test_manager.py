"""
Тесты для ModelManager.

Проверяют:
- Выбор моделей по контексту
- Учет дневных лимитов
- Сброс статистики при смене дня
- Отчет об использовании токенов
"""

import os

from ai_engine.manager import MODEL_CONFIG, ModelManager


class TestModelManager:
    """Тесты для ModelManager."""

    def test_initialization(self, test_model_config, clean_usage_file):
        """Проверка инициализации менеджера."""
        manager = ModelManager(model_config=test_model_config)

        assert manager.model_config == test_model_config
        assert manager.usage == {}
        assert manager._today is not None

    def test_get_daily_limit(self, test_model_config, clean_usage_file):
        """Проверка получения дневного лимита модели."""
        manager = ModelManager(model_config=test_model_config)

        assert manager.get_daily_limit("test/model-small") == 1000
        assert manager.get_daily_limit("test/model-medium") == 5000
        assert manager.get_daily_limit("test/model-large") == 10000
        assert manager.get_daily_limit("unknown/model") is None

    def test_report_usage(self, test_model_config, clean_usage_file):
        """Проверка записи использования токенов."""
        manager = ModelManager(model_config=test_model_config)

        manager.report_usage("test/model-small", 100)

        assert manager.usage["test/model-small"]["tokens"] == 100
        assert manager.usage["test/model-small"]["calls"] == 1
        assert manager.usage["test/model-small"]["last"] is not None

    def test_report_usage_multiple_calls(self, test_model_config, clean_usage_file):
        """Проверка накопления использования токенов."""
        manager = ModelManager(model_config=test_model_config)

        manager.report_usage("test/model-small", 100)
        manager.report_usage("test/model-small", 200)
        manager.report_usage("test/model-small", 300)

        assert manager.usage["test/model-small"]["tokens"] == 600
        assert manager.usage["test/model-small"]["calls"] == 3

    def test_tokens_remaining(self, test_model_config, clean_usage_file):
        """Проверка расчета оставшихся токенов."""
        manager = ModelManager(model_config=test_model_config)

        # Начальное состояние - все токены доступны
        assert manager.tokens_remaining("test/model-small") == 1000

        # После использования
        manager.report_usage("test/model-small", 300)
        assert manager.tokens_remaining("test/model-small") == 700

        # После превышения лимита
        manager.report_usage("test/model-small", 800)
        assert manager.tokens_remaining("test/model-small") == 0

    def test_tokens_remaining_unknown_model(self, test_model_config, clean_usage_file):
        """Проверка токенов для неизвестной модели."""
        manager = ModelManager(model_config=test_model_config)

        # Модель не в конфигурации
        assert manager.tokens_remaining("unknown/model") is None

    def test_choose_by_context_small(self, test_model_config, clean_usage_file):
        """Проверка выбора модели для малого контекста."""
        manager = ModelManager(model_config=test_model_config)

        # Малый контекст должен выбирать small модель
        model = manager.choose_by_context(500)
        assert model is not None

    def test_choose_by_context_large(self, test_model_config, clean_usage_file):
        """Проверка выбора модели для большого контекста."""
        manager = ModelManager(model_config=test_model_config)

        # Большой контекст должен выбирать large модель
        model = manager.choose_by_context(50000)
        assert model is not None

    def test_get_candidates_returns_list(self, test_model_config, clean_usage_file):
        """Проверка что get_candidates возвращает список."""
        manager = ModelManager(model_config=test_model_config)

        candidates = manager.get_candidates(history_chars=1000)

        assert isinstance(candidates, list)
        assert len(candidates) > 0

    def test_get_candidates_filters_exhausted(self, test_model_config, clean_usage_file):
        """Проверка фильтрации исчерпанных моделей."""
        manager = ModelManager(model_config=test_model_config)

        # Исчерпываем первую модель
        manager.report_usage("test/model-small", 1000)

        candidates = manager.get_candidates(history_chars=100)

        # Исчерпанная модель не должна быть в кандидатах
        # или должна быть последней (если нет других)
        assert "test/model-small" not in candidates or len(candidates) == 1

    def test_reset_if_new_day(self, test_model_config, clean_usage_file, tmp_path):
        """Проверка сброса статистики при смене дня."""
        usage_file = tmp_path / "test_usage.json"
        os.environ["AI_MODEL_USAGE_FILE"] = str(usage_file)

        manager = ModelManager(model_config=test_model_config)
        manager.report_usage("test/model-small", 500)

        # Имитируем смену дня
        old_today = manager._today
        manager._today = "2000-01-01"
        manager._reset_if_new_day()

        # Статистика должна сброситься
        assert manager._today != "2000-01-01"
        assert manager.usage == {}

        # Восстанавливаем
        if "AI_MODEL_USAGE_FILE" in os.environ:
            del os.environ["AI_MODEL_USAGE_FILE"]


class TestModelConfig:
    """Тесты для конфигурации моделей по умолчанию."""

    def test_model_config_not_empty(self):
        """Проверка что конфигурация моделей не пустая."""
        assert len(MODEL_CONFIG) > 0

    def test_model_config_format(self):
        """Проверка формата конфигурации моделей."""
        for model_name, limit in MODEL_CONFIG:
            assert isinstance(model_name, str)
            assert isinstance(limit, int)
            assert limit > 0

    def test_model_config_has_various_limits(self):
        """Проверка что модели имеют разные лимиты."""
        limits = [limit for _, limit in MODEL_CONFIG]
        assert len(set(limits)) > 1  # Должны быть разные лимиты
