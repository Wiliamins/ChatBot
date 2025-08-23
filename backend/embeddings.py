# embeddings.py
# ------------------------------------------------------------
# Junior (PL): prosty wrapper na Sentence-Transformers:
#  - model all-MiniLM-L6-v2 (384D, szybki)
#  - zwracam listę floatów (Qdrant tak lubi)
# ------------------------------------------------------------
from sentence_transformers import SentenceTransformer

_model = None

def _get_model():
    global _model
    if _model is None:
        _model = SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2")
    return _model

def generate_embedding(text: str):
    model = _get_model()
    vec = model.encode([text], normalize_embeddings=True)[0]
    return vec.tolist()
