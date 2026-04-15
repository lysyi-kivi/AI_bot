import logging
import os

from openai import AsyncOpenAI

logger = logging.getLogger("ai_bot.ai_engine.summarizer")

client = AsyncOpenAI(
    api_key=os.getenv("IOINTELLIGENCE_API_KEY"), base_url=os.getenv("AI_BASE_URL")
)

SUMMARIZER_MODEL = os.getenv("SUMMARIZER_MODEL", "mistralai/Magistral-Small-2506")


async def summarize_messages(history: list[dict]) -> str:
    """
    Принимает список сообщений (role/content) и возвращает краткий summary.
    По идее: вызываем небольшую модель-инструктор.
    """
    if not history:
        return ""

    # Собираем текст для summary
    # Берём первые N сообщений (или всю длинную пачку) для компактного summary
    payload = "Сжать следующую историю диалога в 1–2 коротких абзаца, сохранить ключевые факты, цели пользователя и важные предпочтения:\n\n"
    for m in history:
        role = m.get("role", "")
        content = m.get("content", "")
        payload += f"{role.upper()}: {content}\n"

    messages = [
        {
            "role": "system",
            "content": "Ты — ассистент. Сжать историю в 1-2 абзаца русским языком.",
        },
        {"role": "user", "content": payload},
    ]

    try:
        completion = await client.chat.completions.create(
            model=SUMMARIZER_MODEL,
            messages=messages,
            temperature=0.2,
            max_completion_tokens=300,
            stream=False,
        )
        ret = completion.choices[0].message.content.strip()
        return ret
    except Exception as e:
        # если summarizer недоступен — fallback: простая конкатенация первых 400 символов
        logger.warning(f"Summarizer error: {e}", exc_info=True)
        raw = " ".join(m.get("content", "") for m in history)[:400]
        return raw
