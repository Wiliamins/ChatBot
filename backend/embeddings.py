from sentence_transformers import SentenceTransformer

# Загружаем одну модель на процесс
_model = SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2")

def generate_embedding(text: str):
    """
    Возвращает список float длиной 384 для строки text.
    """
    if not text:
        text = ""
    vec = _model.encode([text], normalize_embeddings=True)[0]
    return vec.tolist()
