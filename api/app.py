# api/app.py
from fastapi import FastAPI
from pathlib import Path
import sys, os, traceback

app = FastAPI()  # НЕ ставим root_path здесь; он внутри backend/app.py

# даём питону видеть пакет backend из корня репо
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

boot_error = None

try:
    # ВАЖНО: в backend/app.py должно быть app = FastAPI(...), см. п.3
    from backend.app import app as fastapi_app
    app = fastapi_app  # подменяем на реальное приложение
except Exception as e:
    boot_error = e
    tb = traceback.format_exc()

    @app.get("/__boot")
    def __boot():
        # Показываем безопасно, чтобы понять, почему падает импорт
        return {
            "import_error": str(boot_error),
            "trace": tb.splitlines()[-25:]  # последние линии стека
        }

# Бэкап-эндпоинт на случай падения
@app.get("/health")
def _health():
    return {"ok": True, "backend_loaded": boot_error is None}
