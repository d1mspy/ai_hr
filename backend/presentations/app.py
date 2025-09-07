from fastapi import UploadFile, File, FastAPI, HTTPException, status, WebSocket, WebSocketException, WebSocketDisconnect
from utils.websocket import ConnectionManager
from services.parsing_service import ParsingService
from services.match_service import MatchService
from repositories.db.repository import Repository
from schemas.docs import CompareResponse
from utils.websocket import ConnectionManager, AudioConnectionManager, MessageType, WSMessage
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from repositories.db.repository import Repository
from schemas.docs import ParsedDocsResponse
import asyncio
import websockets
import json
import base64
import numpy as np

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
parsing_service = ParsingService(repository)
matching_service = MatchService(parsing_service)

@app.get("/")
async def test_endpoint() -> str:
    """
    тестовый эндпоинт
    """
    return "ok"


@app.post("/compare", response_model=CompareResponse)
async def compare_docs(cv: UploadFile = File(...), vacancy: UploadFile = File(...)):
    """
    сравнение резюме и вакансии
    """
    for f in (cv, vacancy):
        if not f.filename.lower().endswith(".docx"):
            raise HTTPException(status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
                                detail=f"Только .docx. Недопустим файл: {f.filename}")

    cv_bytes = await cv.read()
    vacancy_bytes = await vacancy.read()

    dto = await matching_service.compare_docs(cv_bytes, vacancy_bytes)

    return dto


class TestWebSocketRequest(BaseModel):
    user_id: int = 123
    chunks_count: int = 5
    chunk_delay: float = 0.1
    

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


@app.post("/interview/test")
async def test_websocket_client(request: TestWebSocketRequest):
    """
    Запускает тестового WebSocket клиента для проверки сервера
    """
    try:
        # Этот код запускает клиента в фоне
        asyncio.create_task(run_test_client(request))
        return {"status": "test_started", "message": "Test client running in background"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Test failed: {e}")


@app.websocket("/interview/test")
async def run_test_client(request: TestWebSocketRequest):
    """Фоновая задача для тестового клиента"""
    uri = f"http://localhost/interview/{request.user_id}"
    
    try:
        async with websockets.connect(uri) as websocket:
            print("Test client connected to WebSocket server")
            
            # Отправляем AUDIO_START
            start_message = {
                "type": "audio_start",
                "user_id": request.user_id,
                "timestamp": 1234567890.0
            }
            await websocket.send(json.dumps(start_message))
            print("Sent AUDIO_START")
            
            # Отправляем чанки
            for i in range(request.chunks_count):
                audio_data = np.random.randint(-32768, 32767, 512, dtype=np.int16)
                audio_bytes = audio_data.tobytes()
                audio_b64 = base64.b64encode(audio_bytes).decode('utf-8')
                
                chunk_message = {
                    "type": "audio_chunk",
                    "user_id": request.user_id,
                    "chunk": audio_b64,
                    "timestamp": 1234567890.0 + i
                }
                await websocket.send(json.dumps(chunk_message))
                print(f"Sent AUDIO_CHUNK {i+1}")
                
                await asyncio.sleep(request.chunk_delay)
            
            # Завершаем сессию
            end_message = {
                "type": "audio_end", 
                "user_id": request.user_id,
                "timestamp": 1234567895.0
            }
            await websocket.send(json.dumps(end_message))
            print("Sent AUDIO_END")
            
            # Слушаем ответы
            async for message in websocket:
                data = json.loads(message)
                print(f"Server response: {data}")
                
    except Exception as e:
        print(f"Test client error: {e}")