# api/app.py — минимальный тест, что runtime=python3.11 используется
from fastapi import FastAPI
app = FastAPI()

@app.get("/api/health")
def health():
    return {"ok": True}
