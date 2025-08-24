# backend/embeddings.py
import os
import requests

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_EMBED_MODEL = os.getenv("OPENAI_EMBED_MODEL", "text-embedding-3-small")

class EmbeddingError(RuntimeError):
    pass

def generate_embedding(text: str) -> list[float]:
    """
    Генерация эмбеддинга через OpenAI REST API.
    Без SDK, чтобы не тащить лишние зависимости.
    """
    if not OPENAI_API_KEY:
        raise EmbeddingError("OPENAI_API_KEY is not set")

    # OpenAI ограничивает длину токенов — подрежем очень длинные строки
    text = (text or "").strip()
    if not text:
        return []

    resp = requests.post(
        "https://api.openai.com/v1/embeddings",
        headers={
            "Authorization": f"Bearer {OPENAI_API_KEY}",
            "Content-Type": "application/json",
        },
        json={
            "model": OPENAI_EMBED_MODEL,
            "input": text[:15000],  # простая защита от чрезмерно длинных инпутов
        },
        timeout=30,
    )
    if resp.status_code != 200:
        raise EmbeddingError(f"OpenAI embeddings error {resp.status_code}: {resp.text}")

    data = resp.json()
    return data["data"][0]["embedding"]
