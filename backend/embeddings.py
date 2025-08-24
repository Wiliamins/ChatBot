# backend/embeddings.py
import os
import requests
from typing import List

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_BASE = os.getenv("OPENAI_BASE", "https://api.openai.com/v1")
OPENAI_EMBED_MODEL = os.getenv("OPENAI_EMBED_MODEL", "text-embedding-3-small")
# text-embedding-3-small -> 1536-мерные вектора

class EmbeddingError(RuntimeError):
    pass

def generate_embedding(text: str) -> List[float]:
    """
    Вычисляет эмбеддинг в OpenAI. Для больших текстов желательно заранее нарезать на чанки
    и усреднять/брать max (но для MVP можно одним куском).
    """
    if not OPENAI_API_KEY:
        raise EmbeddingError("OPENAI_API_KEY is not set")

    resp = requests.post(
        f"{OPENAI_BASE}/embeddings",
        headers={
            "Authorization": f"Bearer {OPENAI_API_KEY}",
            "Content-Type": "application/json",
        },
        json={
            "model": OPENAI_EMBED_MODEL,
            "input": text
        },
        timeout=30
    )
    if resp.status_code != 200:
        raise EmbeddingError(f"OpenAI error {resp.status_code}: {resp.text}")

    data = resp.json()
    vec = data["data"][0]["embedding"]
    # OpenAI возвращает list[float]; размер для text-embedding-3-small = 1536
    return vec
