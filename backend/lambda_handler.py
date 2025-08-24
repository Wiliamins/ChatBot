from mangum import Mangum
# Импортируем FastAPI-приложение из твоего backend/app.py
# Важно: в app.py должен быть app = FastAPI()
from app import app

# Lambda handler для AWS (API Gateway -> Lambda -> FastAPI)
handler = Mangum(app)