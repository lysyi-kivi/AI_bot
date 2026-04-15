import logging
import math
import os

from openai import APIConnectionError, APIError, AsyncOpenAI, RateLimitError

from .manager import ModelManager
from .sanitize import sanitize_html
from .summarizer import summarize_messages

logger = logging.getLogger("ai_bot.ai_engine")

# клиент для основных запросов
client = AsyncOpenAI(api_key=os.getenv("IOINTELLIGENCE_API_KEY"), base_url=os.getenv("AI_BASE_URL"))

# менеджер моделей
model_manager = ModelManager()

# Параметры
SUMMARY_THRESHOLD_CHARS = int(
    os.getenv("SUMMARY_THRESHOLD_CHARS", "8000")
)  # если история больше — summarise
TOKEN_ESTIMATE_DIV = 4  # примерно chars/4 -> tokens estimate


def estimate_tokens_from_chars(chars: int) -> int:
    return max(1, math.ceil(chars / TOKEN_ESTIMATE_DIV))


async def ask_ai_engine(history: list[dict], session=None) -> str:
    """
    history: list[{"role": "user"/"assistant"/"system", "content": "..."}]
    session: SQLAlchemy session (необязательно; можно использовать для записи summary)
    """
    if history is None:
        history = []

    # 0) подсчёт длины
    total_chars = sum(len(m.get("content", "")) for m in history)
    # 1) если история очень длинная — сначала summarizer
    if total_chars > SUMMARY_THRESHOLD_CHARS:
        # берем старые сообщения: обычно первые элементы
        # предположим history отсортирован от старых к новым
        # возьмём первые половину (или те что старше)
        prefix = history[:-20]  # оставим последние 20 сообщений в явном виде, остальные сжимаем
        if prefix:
            summary_text = await summarize_messages(prefix)
            # заменяем prefix на одно сообщение summary
            summary_msg = {
                "role": "system",
                "content": f"Резюме предыдущих сообщений: {summary_text}",
            }
            history = [summary_msg] + history[-20:]
            total_chars = sum(len(m.get("content", "")) for m in history)

    # 2) получить кандидатов моделей
    candidates = model_manager.get_candidates(total_chars)
    if not candidates:
        # если все модели исчерпаны — вернуть дружелюбный ответ
        return "⚠️ Все модели сегодня исчерпали свои лимиты. Попробуйте позже."

    last_exception = None
    # 3) пробуем модели по очереди
    for model in candidates:
        try:
            # оценка токенов (приблизительно)
            est_tokens = estimate_tokens_from_chars(total_chars + 200)  # +200 для ответа
            # если модели осталось мало токенов — пропускаем
            rem = model_manager.tokens_remaining(model)
            if rem is not None and rem < est_tokens:
                logger.debug(f"Model {model} имеет недостаточно токенов: {rem} < {est_tokens}")
                continue

            logger.info(f"Запрос к модели {model} (~{est_tokens} токенов)")

            completion = await client.chat.completions.create(
                model=model,
                messages=[m for m in history],
                temperature=0.7,
                stream=False,
                max_completion_tokens=600,
            )
            # получили ответ
            raw_text = (completion.choices[0].message.content or "").strip()
            if not raw_text:
                logger.warning(f"Model {model} вернула пустой ответ")
                last_exception = Exception("Empty response")
                continue

            # 4) оценка потребл токенов и запись usage
            model_manager.report_usage(model, est_tokens + 50)  # +50 buffer
            logger.info(f"Модель {model} успешно обработала запрос")

            # 5) sanitize for Telegram
            safe_text = sanitize_html(raw_text)

            return safe_text

        except RateLimitError as e:
            logger.warning(f"Rate limit для модели {model}: {e}")
            last_exception = e
            continue
        except APIConnectionError as e:
            logger.error(f"Ошибка соединения с моделью {model}: {e}")
            last_exception = e
            continue
        except APIError as e:
            logger.error(f"API ошибка модели {model}: {e}")
            last_exception = e
            continue
        except Exception as e:
            logger.warning(f"Model {model} failed: {e}", exc_info=True)
            last_exception = e
            continue

    # если ни одна модель не помогла
    return "⚠️ Не удалось получить ответ от моделей. Попробуйте позже."
