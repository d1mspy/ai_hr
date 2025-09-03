from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from repositories.db.repository import Repository

app = FastAPI(title="МТС хак")

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

# экземпляр тестового класса для взаимодействия с бд
repository = Repository()

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
    await repository.test_post(testdb.string)

@app.get("/test")
async def test_get() -> list | None:
    """
    тест базы данных
    """
    data = await repository.test_get()
    return data
