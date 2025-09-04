from fastapi import UploadFile, File, FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from services.service import Service
from repositories.db.repository import Repository
from schemas.docs import ParsedDocsResponse

app = FastAPI(title="ВТБ хак",
              docs_url='/docs',
              redoc_url='/redoc',
              openapi_url='/openapi.json',
              root_path="/api")

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

# экземпляры тестового класса сервиса и репозитория
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

@app.post("/compare", response_model=ParsedDocsResponse)
async def compare_docs(cv: UploadFile = File(...), vacancy: UploadFile = File(...)):
    """
    сравнение резюме и вакансии
    """
    for f in (cv, vacancy):
        if not f.filename.lower().endswith(".docx"):
            raise HTTPException(status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE, detail=f"Только .docx. Недопустим файл: {f.filename}")
    
    cv_bytes = await cv.read()
    vacancy_bytes = await vacancy.read()
    
    dto = await service.compare_docs(cv_bytes, vacancy_bytes)
    
    return {
        "cv": dto.cv.model_dump(),
        "vacancy": dto.vacancy.model_dump()
    }