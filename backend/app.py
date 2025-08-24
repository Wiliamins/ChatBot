# backend/app.py (фрагмент upload)
import uuid, os
from fastapi import FastAPI, UploadFile, File
from document_parser import parse_file, parse_cms_content
from embeddings import generate_embedding
from qdrant_utils import QdrantManager

app = FastAPI()
qdrant = QdrantManager()

@app.post("/upload")
async def upload_file(file: UploadFile = File(...)):
    temp_path = os.path.join("/tmp", f"upload_{uuid.uuid4()}_{file.filename}")
    data = await file.read()
    with open(temp_path, "wb") as f:
        f.write(data)
    try:
        text = parse_file(temp_path)
        vec = generate_embedding(text)
        meta = {"source": file.filename, "file_type": os.path.splitext(file.filename)[1]}
        qdrant.insert_vector(str(uuid.uuid4()), vec, meta)
        return {"message": f"Uploaded: {file.filename}"}
    finally:
        try:
            os.remove(temp_path)
        except Exception:
            pass
