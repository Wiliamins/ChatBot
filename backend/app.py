import os
import re
import uuid
from typing import Optional, List

from fastapi import FastAPI, File, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel


from qdrant_client.http.models import Filter, FieldCondition, MatchValue

from document_parser import parse_file, iter_kv_pairs_from_text, iter_json_flat_kv
from embeddings import generate_embedding
from qdrant_utils import QdrantManager

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

qdrant = QdrantManager()

#  Priorytet "ostatniego źródła" 
LATEST_SOURCE: Optional[str] = None
LATEST_SOURCE_TYPE: Optional[str] = None  # "file" / "cms"

class Query(BaseModel):
    query: str

class CMSContent(BaseModel):
    content: dict

@app.get("/")
def health():
    return {"status": "ok"}

#Normalizacja i aliasy 
_norm = re.compile(r"[^a-z0-9 ]+")

def norm_key(s: str) -> str:
    """Junior (PL): normalizuję klucz do porównań."""
    s = (s or "").lower().strip()
    s = _norm.sub(" ", s)
    return re.sub(r"\s+", " ", s)

# Bezpieczne aliasy → klucz kanoniczny (takie klucze mamy w danych)
SAFE_MAP = {
    "name": "project codename",
    "project codename": "project codename",
    "codename": "project codename",

    "project name": "project name",       
    "project title": "project name",

    "project": "project",                  
    "date": "delivery date",
    "delivery date": "delivery date",
    "deadline": "delivery date",
    "due date": "delivery date",

    "office": "office city",
    "office city": "office city",
    "location": "office city",
    "where is the office": "office city",
    "where is office": "office city",
    "city": "office city",

    "headcount": "headcount",
    "employees": "headcount",
    "team size": "headcount",
    "people": "headcount",

    "ceo": "ceo",

    "support hours": "support hours",
    "working hours": "support hours",
    "work hours": "support hours",
    "hours": "support hours",

    "sla": "sla",
    "service level": "sla",
    "service level agreement": "sla",

    "contact email": "contact email",
    "email": "contact email",

    "tech stack": "tech stack",
    "main stack": "main stack",
    "stack": "tech stack",
    "technology": "tech stack",

    "developer": "developer",

    "overview": "overview",
}

def map_query_to_key(q: str) -> Optional[str]:
    qn = norm_key(q)
    if qn in SAFE_MAP:
        return SAFE_MAP[qn]
    if " " not in qn and qn:  # pojedyncze słowo → traktuję jako klucz
        return qn
    return None

# Wstawianie punktów 
def _insert_kv(source: str, source_type: str, q: str, a: str, seq: int, raw_text: Optional[str] = None):
    payload = {
        "source": source,
        "source_type": source_type,
        "file_type": "json" if source_type == "cms" else os.path.splitext(source)[1],
        "q": q.strip(),
        "a": a.strip(),
        "q_norm": norm_key(q),
        "seq": int(seq),  
        "text": (raw_text or f"{q}: {a}")[:1000],
    }
  
    vec = generate_embedding(f"{q} {a[:100]}")
    qdrant.insert_vector(str(uuid.uuid4()), vec, payload)

#Upload pliku
@app.post("/upload")
async def upload_file(file: UploadFile = File(...)):
    global LATEST_SOURCE, LATEST_SOURCE_TYPE

    tmp = f"temp_{file.filename}"
    with open(tmp, "wb") as f:
        f.write(await file.read())

    try:
        text = parse_file(tmp)
        pairs = list(iter_kv_pairs_from_text(text))

        qdrant.wipe_source(file.filename)

        if pairs:
            for it in pairs:
                _insert_kv(file.filename, "file", it["q"], it["a"], it.get("seq", 0), it.get("text"))
        

        LATEST_SOURCE = file.filename
        LATEST_SOURCE_TYPE = "file"
        return {"message": "File processed and stored", "pairs": len(pairs)}
    except Exception as e:
        return {"error": str(e)}
    finally:
        try:
            os.remove(tmp)
        except:
            pass

# ===== CMS =====
@app.post("/cms")
async def upload_cms(cms: CMSContent):
    global LATEST_SOURCE, LATEST_SOURCE_TYPE
    try:
        flat = list(iter_json_flat_kv(cms.content or {}))
        qdrant.wipe_source("cms")
        if flat:
            for it in flat:
                _insert_kv("cms", "cms", it["q"], it["a"], it.get("seq", 0), it.get("text"))

        LATEST_SOURCE = "cms"
        LATEST_SOURCE_TYPE = "cms"
        return {"message": "CMS content processed and stored", "pairs": len(flat)}
    except Exception as e:
        return {"error": str(e)}

# ===== Query =====
def _select_latest_by_seq(points) -> Optional[dict]:
    """Junior (PL): z listy rekordów wybieram payload z największym 'seq'."""
    best = None
    for r in points or []:
        p = getattr(r, "payload", {}) or {}
        if p.get("a"):
            if best is None or int(p.get("seq", -1)) > int(best.get("seq", -1)):
                best = p
    return best

@app.post("/query")
async def query(q: Query):
    try:
        target = map_query_to_key(q.query)
        target_norm = norm_key(target) if target else None

        
        if target_norm:
            # 1a. Priorytet: ostatnie źródło
            if LATEST_SOURCE:
                flt = Filter(must=[
                    FieldCondition(key="q_norm", match=MatchValue(value=target_norm)),
                    FieldCondition(key="source", match=MatchValue(value=LATEST_SOURCE)),
                ])
                scoped = qdrant.fetch_all(flt)
                best = _select_latest_by_seq(scoped)
                if best:
                    return {"answer": best.get("a", "").strip(), "source": best.get("source")}

            # 1b. Globalnie
            flt_all = Filter(must=[FieldCondition(key="q_norm", match=MatchValue(value=target_norm))])
            all_hits = qdrant.fetch_all(flt_all)
            best = _select_latest_by_seq(all_hits)
            if best:
                return {"answer": best.get("a", "").strip(), "source": best.get("source")}

            # Nie ma takiego klucza nigdzie
            if LATEST_SOURCE:
                return {"answer": "No relevant information found in the latest source.", "source": LATEST_SOURCE}
            return {"answer": "No relevant information found."}

        # 2) Jeśli nie rozpoznaliśmy klucza — fallback: semantyczne wyszukiwanie i zwrot pary
        qvec = generate_embedding(q.query)
        if LATEST_SOURCE:
            flt = Filter(must=[FieldCondition(key="source", match=MatchValue(value=LATEST_SOURCE))])
            scoped = qdrant.search_vectors(qvec, limit=10, query_filter=flt)
            if scoped:
                p = scoped[0].payload or {}
                if p.get("q") and p.get("a"):
                    return {"answer": p["a"], "source": p.get("source")}
                return {"answer": f"Based on {p.get('source','unknown')}: {p.get('text','Relevant information found.')}"}

        results = qdrant.search_vectors(qvec, limit=10)
        if results:
            p = results[0].payload or {}
            if p.get("q") and p.get("a"):
                return {"answer": p["a"], "source": p.get("source")}
            return {"answer": f"Based on {p.get('source','unknown')}: {p.get('text','Relevant information found.')}"}

        return {"answer": "No relevant information found."}

    except Exception as e:
        return {"answer": f"Error: {e}"}
