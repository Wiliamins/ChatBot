# api/app.py — минимальный тест, что python3.11-функции реально работают
from fastapi import FastAPI

app = FastAPI()

@app.get("/api/health")
def health():
    return {"ok": True}
