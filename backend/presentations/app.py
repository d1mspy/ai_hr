from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from services.service import Service
from repositories.db.repository import Repository

app = FastAPI(title="ВТБ хак")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# тестовая pydantic модель
class Testdb(BaseModel):
    string: str

# экземпляр тестового класса сервиса
repository = Repository()
service = Service(repository)

@app.get("/")
async def test_endpoint() -> str:
    """
    тестовый эндпоинт
    """
    return "ok"

@app.post("/test")
async def test_post(testdb: Testdb) -> None:
    """
    тест базы данных
    """
    await service.test_post(testdb.string)

@app.get("/test")
async def test_get() -> list | None:
    """
    тест базы данных
    """
    data = await service.test_get()
    return data
