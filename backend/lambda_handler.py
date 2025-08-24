# backend/lambda_handler.py
# Обёртка для AWS Lambda. Импортирует твой FastAPI-приложение из app.py и
# превращает его в Lambda handler через Mangum.

from mangum import Mangum
from app import app  # <-- здесь важно: в app.py должен быть app = FastAPI()

handler = Mangum(app)
