from fastapi import FastAPI
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))   # даём видеть пакет backend

# ВРЕМЕННЫЙ безопасный импорт с отладкой
app = FastAPI()

try:
    from backend.app import app as fastapi_app  # в backend/app.py: app = FastAPI(root_path="/api")
    app = fastapi_app
except Exception as e:
    import traceback
    @app.get("/__boot")
    def boot():
        return {"import_error": str(e), "trace": traceback.format_exc()}

@app.get("/health")  # на всякий случай базовый health
def health():
    return {"ok": True}
