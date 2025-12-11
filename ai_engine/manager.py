# ai_engine/manager.py
import os
import json
import time
from typing import List, Optional

USAGE_FILE = os.getenv("AI_MODEL_USAGE_FILE", "ai_model_usage.json")
# Пример конфигурации моделей: (name, daily_token_limit)
MODEL_CONFIG = [
    ("mistralai/Mistral-Large-Instruct-2411", 200_000),  # large — условный лимит токенов/день
    ("deepseek-ai/DeepSeek-R1-0528", 150_000),
    ("mistralai/Magistral-Small-2506", 80_000),
    ("meta-llama/Llama-3.3-70B-Instruct", 100_000),
]

# Пример выбора по контексту (можно упрощать/расширять)
CONTEXT_TO_MODEL = [
    (3000, "mistralai/Magistral-Small-2506"),
    (8000, "deepseek-ai/DeepSeek-R1-0528"),
    (99999999, "mistralai/Mistral-Large-Instruct-2411"),
]


def _load_usage() -> dict:
    if not os.path.exists(USAGE_FILE):
        return {}
    try:
        with open(USAGE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}

def _save_usage(d: dict):
    with open(USAGE_FILE, "w", encoding="utf-8") as f:
        json.dump(d, f, ensure_ascii=False, indent=2)


class ModelManager:
    def __init__(self, model_config=MODEL_CONFIG):
        self.model_config = model_config
        self.usage = _load_usage()
        self._today = self._current_day()

    def _current_day(self) -> str:
        return time.strftime("%Y-%m-%d")

    def _reset_if_new_day(self):
        today = self._current_day()
        if self._today != today:
            self.usage = {}
            self._today = today
            _save_usage(self.usage)

    def get_daily_limit(self, model_name: str) -> Optional[int]:
        for name, limit in self.model_config:
            if name == model_name:
                return limit
        return None

    def _ensure_model_entry(self, model_name: str):
        self._reset_if_new_day()
        if model_name not in self.usage:
            self.usage[model_name] = {"tokens": 0, "calls": 0, "last": None}

    def report_usage(self, model_name: str, tokens: int):
        """Добавить расход токенов (примерно)"""
        self._ensure_model_entry(model_name)
        self.usage[model_name]["tokens"] += tokens
        self.usage[model_name]["calls"] += 1
        self.usage[model_name]["last"] = time.time()
        _save_usage(self.usage)

    def tokens_remaining(self, model_name: str) -> Optional[int]:
        self._ensure_model_entry(model_name)
        limit = self.get_daily_limit(model_name)
        if limit is None:
            return None
        used = self.usage.get(model_name, {}).get("tokens", 0)
        return max(0, limit - used)

    def choose_by_context(self, total_chars: int) -> str:
        """Быстрый выбор модели по длине контекста"""
        for limit, model in CONTEXT_TO_MODEL:
            if total_chars <= limit:
                return model
        return CONTEXT_TO_MODEL[-1][1]

    def get_candidates(self, history_chars: int) -> List[str]:
        """
        Возвращает список кандидатов в порядке приоритета, учитывает дневные лимиты.
        Сначала – модель, подходящая по контексту, затем остальные по конфигу.
        """
        self._reset_if_new_day()
        primary = self.choose_by_context(history_chars)
        models = [m for m, _ in self.model_config]
        # put primary first if present
        if primary in models:
            models.remove(primary)
            candidates = [primary] + models
        else:
            candidates = models
        # filter out exhausted models
        filtered = []
        for m in candidates:
            rem = self.tokens_remaining(m)
            if rem == 0:
                # пропускаем полностью исчерпанные модели
                continue
            filtered.append(m)
        return filtered