from fastapi import UploadFile, File, Path, FastAPI, HTTPException, status, WebSocket, Request, WebSocketDisconnect
from contextlib import asynccontextmanager
from utils.websocket import ConnectionManager
from services.parsing_service import ParsingService
from services.match_service import MatchService
from llm_compare.llm_module import LLMAnalyzer
from services.user import UserService
from utils.voice.сhunk_processor import chunk_processor
from settings.settings import settings
from repositories.db.repository import Repository
from schemas.docs import ParsingAndLLMResponse, InterviewDTO
from utils.websocket import ConnectionManager, AudioConnectionManager, MessageType
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from repositories.db.repository import Repository
import asyncio
from datetime import datetime
import json
import base64
from utils.handling_llm import llm
import httpx
import numpy as np
import logging

# глобальный http-клиент
async_client: httpx.AsyncClient | None = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.http_client = httpx.AsyncClient(timeout=settings.analyzer.timeout_sec)
    yield
    await app.state.http_client.aclose()

app = FastAPI(title="ВТБ хак",
              docs_url='/docs',
              redoc_url='/redoc',
              openapi_url='/openapi.json',
              root_path="/api",
              lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# экземпляры классов сервисов и репозитория
repository = Repository()
parsing_service = ParsingService(repository)
matching_service = MatchService(parsing_service)
user_service = UserService()

@app.get("/")
async def test_endpoint() -> str:
    """
    тестовый эндпоинт
    """
    return "ok"


@app.post("/compare", response_model=ParsingAndLLMResponse)
async def compare_docs(request: Request, cv: UploadFile = File(...), vacancy: UploadFile = File(...)):
    """
    сравнение резюме и вакансии
    """
    for f in (cv, vacancy):
        if not f.filename.lower().endswith(".docx"):
            raise HTTPException(status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
                                detail=f"Только .docx. Недопустим файл: {f.filename}")
    
    cv_bytes = await cv.read()
    vac_bytes = await vacancy.read()
    if not cv_bytes or not vac_bytes:
        raise HTTPException(status_code=400, detail="Один из файлов пустой")    
        
    text = await matching_service.docs_to_text(cv_bytes, vac_bytes)
    dto = await matching_service.compare_docs(cv_bytes, vac_bytes)
    dto.text = text

    resp = ParsingAndLLMResponse(details=dto.decision.get("details", None))

    if dto.decision["decision"] != "reject":
        analyzer = LLMAnalyzer()
        analyzer.set_data(text.cv_text, text.vac_text)
        ok = await analyzer.analyze(request.app.state.http_client)
        if not ok:
            raise HTTPException(status_code=502, detail="LLM не смогло вернуть валидный JSON")
        else:
            resp.decision = analyzer.decision
            resp.score = analyzer.match_percentage
            resp.reasons = analyzer.candidate_feedback
            
            interview_dto = InterviewDTO(
                summary=analyzer.compressed_data,
                meta=analyzer.vacancy_meta,
                hard_topics=analyzer.hard_interview_topics,
                soft_topics=analyzer.soft_interview_topics
            )
            
            user_id = await user_service.put_user(interview_dto)
            encrypted_user_id = await user_service.get_encrypted_id(user_id)
            resp.link = f"http://localhost/interview/{encrypted_user_id}"
            
            return resp

    resp.decision = dto.decision["decision"]
    resp.score = dto.decision["score"]*100
    resp.reasons = dto.decision["reasons"][0] if dto.decision["reasons"] else None
    return resp

class TestWebSocketRequest(BaseModel):
    user_id: int = 123
    chunks_count: int = 5
    chunk_delay: float = 0.1
    
audio_manager = AudioConnectionManager(dto=None, chunk_processor=chunk_processor, llm_model=llm)

@app.websocket("/interview/{encrypted_user_id}")
async def websocket_audio_endpoint(websocket: WebSocket, encrypted_user_id: str = Path(...)):
    user_id = await user_service.validate_user(id=encrypted_user_id)
    if user_id is None:
        await websocket.close(code=4401)
        return

    dto = await user_service.get_data_by_id(user_id)
    audio_manager.data = dto
    audio_manager.set()

    # СНАЧАЛА проверяем возможность коннекта, ПОТОМ accept
    if not await audio_manager.connect(websocket, user_id):
        await websocket.close(code=1008, reason="Session already active")
        return

    await websocket.accept()

    try:
        while True:
            msg = await websocket.receive()
            t = msg.get("type")

            if t == "websocket.receive":
                if "text" in msg and msg["text"] is not None:
                    try:
                        msg_data = json.loads(msg["text"])
                    except Exception as e:
                        await audio_manager.send_message(user_id, json.dumps(
                            {"type": "error", "message": f"Bad JSON: {e}"}
                        ))
                        continue

                    mt = msg_data.get("type")
                    try:
                        msg_type = MessageType(mt)
                    except Exception:
                        await audio_manager.send_message(user_id, json.dumps(
                            {"type": "error", "message": f"Unknown type: {mt}"}
                        ))
                        continue

                    if msg_type == MessageType.AUDIO_START:
                        await audio_manager.handle_audio_start(user_id, msg_data)
                    elif msg_type == MessageType.AUDIO_CHUNK:
                        await audio_manager.handle_audio_chunk(user_id, msg_data)
                    elif msg_type == MessageType.AUDIO_END:
                        await audio_manager.handle_audio_end(user_id, msg_data)
                        break
                    else:
                        await audio_manager.send_message(user_id, json.dumps(
                            {"type": "error", "message": f"Unsupported: {msg_type}"}
                        ))

                elif "bytes" in msg and msg["bytes"] is not None:
                    await audio_manager.send_message(user_id, json.dumps(
                        {"type": "error", "message": "Binary frames not supported; send base64 JSON"}
                    ))

            elif t == "websocket.disconnect":
                await audio_manager.disconnect(user_id)
                break

    except WebSocketDisconnect as e:
        await audio_manager.disconnect(user_id)
    except Exception as e:
        # Ключевое: залогировать стек, а не молча закрыть
        logging.exception("WS loop error")
        try:
            await audio_manager.send_message(user_id, json.dumps(
                {"type": "error", "message": f"Connection error: {e}"}
            ))
        finally:
            await audio_manager.disconnect(user_id)


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

# class user_id(BaseModel):
#     number: int
# class encrypted(BaseModel):
#     user_id: str
# from utils.encrypt_id import encrypt_user_id
# @app.post("/encrypt", response_model=encrypted)
# async def encrypt(id: user_id):
#     dto = await encrypt_user_id(id)
#     resp = encrypted(user_id=dto)
#     return resp