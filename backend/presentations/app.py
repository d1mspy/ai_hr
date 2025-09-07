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
import asyncio
import websockets
from datetime import datetime
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

@app.websocket("/test-audio")
async def test_audio_websocket(websocket: WebSocket):
    """
    ТЕСТОВЫЙ эндпоинт для проверки AudioConnectionManager
    Имитирует работу фронтенда - отправляет тестовые аудио данные
    """
    await websocket.accept()
    print("✅ Test Audio WebSocket client connected")
    
    try:
        user_id = 999  # Тестовый user_id
        
        # 1. Подключаемся через твой менеджер
        if not await audio_manager.connect(websocket, user_id):
            await websocket.send_json({
                "type": "error",
                "error": "Connection rejected",
                "timestamp": datetime.now().timestamp()
            })
            return
        
        # 2. Отправляем AUDIO_START
        start_message = {
            "type": "audio_start",
            "user_id": user_id,
            "timestamp": datetime.now().timestamp()
        }
        await websocket.send_text(json.dumps(start_message))
        print("📨 Sent AUDIO_START")
        
        # 3. Отправляем тестовые аудио чанки
        for i in range(5):
            # Генерируем тестовый аудио сигнал (синусоида)
            t = np.linspace(0, 0.1, 512)
            frequency = 440 + i * 50  # Меняем частоту
            audio_signal = np.sin(2 * np.pi * frequency * t) * 32767
            audio_data = audio_signal.astype(np.int16)
            
            audio_bytes = audio_data.tobytes()
            audio_b64 = base64.b64encode(audio_bytes).decode('utf-8')
            
            chunk_message = {
                "type": "audio_chunk",
                "user_id": user_id,
                "chunk": audio_b64,
                "timestamp": datetime.now().timestamp()
            }
            await websocket.send_text(json.dumps(chunk_message))
            print(f"📨 Sent AUDIO_CHUNK {i+1}")
            
            # Ждем ответа или небольшую паузу
            try:
                response = await asyncio.wait_for(websocket.receive_text(), timeout=0.5)
                print(f"📩 Received: {response}")
            except asyncio.TimeoutError:
                pass  # Пропускаем если нет ответа
                
            await asyncio.sleep(0.2)
        
        # 4. Отправляем AUDIO_END
        end_message = {
            "type": "audio_end",
            "user_id": user_id,
            "timestamp": datetime.now().timestamp()
        }
        await websocket.send_text(json.dumps(end_message))
        print("📨 Sent AUDIO_END")
        
        # 5. Ждем финальный ответ
        try:
            final_response = await asyncio.wait_for(websocket.receive_text(), timeout=2.0)
            print(f"🎉 Final response: {final_response}")
        except asyncio.TimeoutError:
            print("⏰ Timeout waiting for final response")
        
    except WebSocketDisconnect:
        print("❌ Test client disconnected")
        await audio_manager.disconnect(user_id)
    except Exception as e:
        print(f"🔥 Test error: {e}")
        await websocket.send_json({
            "type": "error",
            "error": f"Test error: {str(e)}",
            "timestamp": datetime.now().timestamp()
        })
        await audio_manager.disconnect(user_id)
        
@app.websocket("/_ws_echo")
async def ws_echo(ws: WebSocket):
    await ws.accept()
    await ws.send_text("ok")
    while True:
        msg = await ws.receive_text()
        await ws.send_text(f"echo: {msg}")