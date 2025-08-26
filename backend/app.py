from fastapi import FastAPI, File, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import os
import uuid
from pathlib import Path
from document_parser import parse_file, parse_cms_content, normalize_key
from embeddings import generate_embedding
from qdrant_utils import QdrantManager

app = FastAPI(root_path="/api")

ALLOWED = os.getenv("ALLOWED_ORIGINS", "http://localhost:3000").split(",")
@app.get("/api/health")
def health():
    return {"ok": True}

app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in ALLOWED if o.strip()],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

qdrant = QdrantManager()


LATEST_SOURCE: str | None = None


class Query(BaseModel):
    query: str


class CMSContent(BaseModel):
    content: dict


def candidate_keys(user_query: str) -> list[str]:

    qn = normalize_key(user_query)
    if qn in ("name", "project name"):
        return ["project name", "project codename"]
    if qn == "project codename":
        return ["project codename", "project name"]
    return [qn]


@app.post("/upload")
async def upload_file(file: UploadFile = File(...)):
    safe_name = Path(file.filename).name
    tmp_path = f"/tmp/temp_{safe_name}"
    with open(tmp_path, "wb") as f:
        f.write(await file.read())

    try:
        pairs = parse_file(tmp_path, filename=file.filename)
        file_type = os.path.splitext(file.filename)[1].lower()

        for seq, p in enumerate(pairs):
            payload = {
                "q": p["q"],
                "q_norm": p["q_norm"],
                "a": p.get("a"),
                "text": p.get("text", f'{p["q"]}: {p.get("a","")}'),
                "source": file.filename,
                "source_type": "file",
                "file_type": file_type,
                "seq": seq,
            }
            vec = generate_embedding(payload["text"])
            qdrant.insert_vector(str(uuid.uuid4()), vec, payload)

        global LATEST_SOURCE
        LATEST_SOURCE = file.filename

        return {"message": f"File processed and stored: {file.filename}", "pairs": len(pairs)}
    except Exception as e:
        return {"error": str(e)}
    finally:
        try:
            os.remove(tmp_path)
        except Exception:
            pass


@app.post("/cms")
async def upload_cms(cms: CMSContent):
    try:
        pairs = parse_cms_content(cms.content)
        for seq, p in enumerate(pairs):
            payload = {
                "q": p["q"],
                "q_norm": p["q_norm"],
                "a": p.get("a"),
                "text": p.get("text", f'{p["q"]}: {p.get("a","")}'),
                "source": "cms",
                "source_type": "cms",
                "file_type": "json",
                "seq": seq,
            }
            vec = generate_embedding(payload["text"])
            qdrant.insert_vector(str(uuid.uuid4()), vec, payload)

        global LATEST_SOURCE
        LATEST_SOURCE = "cms"

        return {"message": "CMS content processed and stored", "pairs": len(pairs)}
    except Exception as e:
        return {"error": str(e)}


@app.post("/query")
async def query(query: Query):
    
    try:
        if not LATEST_SOURCE:
            return {"answer": "No relevant information found."}

        keys = candidate_keys(query.query)

        for k in keys:
            pts = qdrant.search_exact_key(k, source_filter=LATEST_SOURCE, limit=1)
            if pts:
                pay = pts[0].payload or {}
                val = pay.get("a") or pay.get("text")
                if val:
                    return {"answer": val, "source": LATEST_SOURCE}

        return {"answer": "No relevant information found."}
    except Exception as e:
        return {"error": str(e)}
