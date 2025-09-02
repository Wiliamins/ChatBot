# api/app.py (если тут держишь сам app) ИЛИ backend/app.py (если импортируешь его)
from fastapi import FastAPI
app = FastAPI(root_path="/api")  # важно!

@app.get("/health")              # без /api в декораторе
def health():
    return {"ok": True}
