from fastapi import UploadFile, File, FastAPI, HTTPException, status, WebSocket, WebSocketException, status
from utils.websocket import ConnectionManager
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from services.service import Service
from repositories.db.user import UserRepository
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


manager = ConnectionManager()

@app.websocket("/interview/{user_id}")
async def interview(websocket: WebSocket, user_id: int):
    # Ром, все просто, тут проверка, подключен ли уже пользователь
    if manager.is_user_connected(user_id):
        raise WebSocketException(
            code=status.WS_1013_TRY_AGAIN_LATER,
            reason="User already connected. Please try again later."
        )
    
    # Тут попытка подключиться
    connected = await manager.connect(websocket, user_id)
    if not connected:
        raise WebSocketException(
            code=status.WS_1013_TRY_AGAIN_LATER,
            reason="User already connected. Please try again later."
        )
    #это логика-затычка, пока забей
    try:
        while True:
            data = await websocket.receive_text()
            await websocket.send_text(f"User {user_id}: {data}")
            
    except Exception as e:
        print(f"Error for user {user_id}: {e}")
    finally:
        manager.disconnect(user_id)