from fastapi import UploadFile, File, FastAPI, HTTPException, status, WebSocket, status, WebSocketDisconnect
from utils.websocket import ConnectionManager, AudioConnectionManager, MessageType, WSMessage
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from services.service import Service
from repositories.db.user import UserRepository
from repositories.db.repository import Repository
from schemas.docs import ParsedDocsResponse
import json


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

# экземпляры класса сервиса и репозитория
repository = Repository()
service = Service(repository)

@app.get("/")
async def test_endpoint() -> str:
    """
    тестовый эндпоинт
    """
    return "ok"

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
audio_manager = AudioConnectionManager(manager)

@app.websocket("/interview/{user_id}")
async def websocket_audio_endpoint(websocket: WebSocket, user_id: int):
    """Основной цикл обработки WebSocket сообщений"""
    manager = audio_manager
    
    if not await manager.connect(websocket, user_id):
        await websocket.close(code=1008, reason="Session already active")
        return
    
    try:
        while True:
            data = await websocket.receive_text()
            msg_data = json.loads(data)
            msg_type = MessageType(msg_data['type'])
            
            if msg_type == MessageType.AUDIO_START:
                await manager.handle_audio_start(user_id, msg_data)
                
            elif msg_type == MessageType.AUDIO_CHUNK:
                await manager.handle_audio_chunk(user_id, msg_data)
                
            elif msg_type == MessageType.AUDIO_END:
                await manager.handle_audio_end(user_id, msg_data)
                break
                
            else:
                await manager.send_error(user_id, f"Unknown message type: {msg_type}")
                
    except WebSocketDisconnect:
        await manager.disconnect(user_id)
    except Exception as e:
        await manager.send_error(user_id, f"Connection error: {e}")
        await manager.disconnect(user_id)