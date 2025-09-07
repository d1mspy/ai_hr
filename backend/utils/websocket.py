from fastapi import WebSocket
from typing import Dict, Optional
import asyncio
from pydantic import BaseModel
import numpy as np
from enum import Enum
from typing import Dict, Optional
import logging
from utils.voice.сhunk_processor import chunk_processor, ChunkProcessAns
from datetime import datetime
import json
import base64

class MessageType(str, Enum):
    AUDIO_START = "audio_start"
    AUDIO_CHUNK = "audio_chunk" 
    AUDIO_END = "audio_end"
    PROCESSING_START = "processing_start"
    PROCESSING_END = "processing_end"
    PROCESSING_RESULT = "processing_result"
    ERROR = "error"

class WSMessage(BaseModel):
    type: MessageType
    user_id: int
    data: Optional[dict] = None
    chunk: Optional[bytes] = None
    timestamp: float

class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[int, WebSocket] = {}
        self.connection_times: Dict[int, datetime] = {}
        self.lock = asyncio.Lock()
        self.logger = logging.getLogger(__name__)

    async def connect(self, websocket: WebSocket, user_id: int) -> bool:
        async with self.lock:
            if user_id in self.active_connections:
                self.logger.warning(f"User {user_id} already connected")
                return False
            
            try:
                await websocket.accept()
                self.active_connections[user_id] = websocket
                self.connection_times[user_id] = datetime.now()
                self.logger.info(f"User {user_id} connected successfully")
                return True
            except Exception as e:
                self.logger.error(f"Connection failed for user {user_id}: {e}")
                return False

    async def disconnect(self, user_id: int):
        async with self.lock:
            if user_id in self.active_connections:
                try:
                    await self.active_connections[user_id].close()
                except:
                    pass
                del self.active_connections[user_id]
                del self.connection_times[user_id]
                self.logger.info(f"User {user_id} disconnected")

    def is_user_connected(self, user_id: int) -> bool:
        return user_id in self.active_connections

    async def send_message(self, user_id: int, message: str) -> bool:
        if not self.is_user_connected(user_id):
            return False
        
        try:
            await self.active_connections[user_id].send_text(message)
            return True
        except Exception as e:
            self.logger.error(f"Failed to send message to user {user_id}: {e}")
            await self.disconnect(user_id)
            return False

    async def send_bytes(self, user_id: int, data: bytes) -> bool:
        if not self.is_user_connected(user_id):
            return False
        
        try:
            await self.active_connections[user_id].send_bytes(data)
            return True
        except Exception as e:
            self.logger.error(f"Failed to send bytes to user {user_id}: {e}")
            await self.disconnect(user_id)
            return False

    async def broadcast(self, message: str):
        disconnected_users = []
        async with self.lock:
            for user_id, websocket in self.active_connections.items():
                try:
                    await websocket.send_text(message)
                except:
                    disconnected_users.append(user_id)
            
            for user_id in disconnected_users:
                await self.disconnect(user_id)

    def get_connection_info(self, user_id: int) -> Optional[dict]:
        if user_id not in self.active_connections:
            return None
        
        return {
            "connection_time": self.connection_times[user_id],
            "duration": (datetime.now() - self.connection_times[user_id]).total_seconds()
        }

    def get_connected_users(self) -> list:
        return list(self.active_connections.keys())

    def get_connections_count(self) -> int:
        return len(self.active_connections)
    
    

class AudioConnectionManager(ConnectionManager):
    def __init__(self, chunk_processor = chunk_processor):
        super().__init__()
        self.chunk_processor = chunk_processor
        self.is_session_active = False
        self.session_start_time = None
        self.chunks_processed = 0
        self.active_user_id = None  # Добавляем отслеживание активного пользователя

    async def connect(self, websocket: WebSocket, user_id: int) -> bool:
        """Переопределяем connect для проверки активной сессии"""
        async with self.lock:
            # ⭐⭐ ПРОВЕРЯЕМ ЕСТЬ ЛИ АКТИВНАЯ СЕССИЯ ⭐⭐
            if self.is_session_active:
                self.logger.warning(f"Rejected connection for user {user_id}: session already active")
                return False
            
            if user_id in self.active_connections:
                self.logger.warning(f"User {user_id} already connected")
                return False
            
            try:
                await websocket.accept()
                self.active_connections[user_id] = websocket
                self.connection_times[user_id] = datetime.now()
                self.logger.info(f"User {user_id} connected successfully")
                return True
            except Exception as e:
                self.logger.error(f"Connection failed for user {user_id}: {e}")
                return False

    async def handle_audio_start(self, user_id: int, data: dict):
        """Начало сессии с проверкой"""
        if self.is_session_active:
            await self.send_error(user_id, "Another session is already active")
            return
            
        self.is_session_active = True
        self.active_user_id = user_id  # Запоминаем кто начал сессию
        self.session_start_time = datetime.now()
        self.chunks_processed = 0
        self.chunk_processor.reset()  # Сбрасываем состояние процессора
        
        await self.send_message(user_id, json.dumps({
            'type': MessageType.PROCESSING_START,
            'message': 'Ready to receive audio'
        }))

    async def handle_audio_chunk(self, user_id: int, data: dict):
        """Обработка чанка с проверкой прав"""
        if not self.is_session_active:
            await self.send_error(user_id, "No active session")
            return
            
        if user_id != self.active_user_id:
            await self.send_error(user_id, "Not authorized for this session")
            return
            
        try:
            chunk_data = base64.b64decode(data['chunk'])
            audio_array = np.frombuffer(chunk_data, dtype=np.int16)
            audio_float = audio_array.astype(np.float32) / 32768.0
            
            # ⭐⭐ ВЫЗОВ ТВОЕГО ChunkProcessor ⭐⭐
            result = await self.chunk_processor(audio_float)
            self.chunks_processed += 1
            
            await self.handle_model_result(user_id, result)
            
        except Exception as e:
            await self.send_error(user_id, f"Processing error: {e}")

    async def handle_model_result(self, user_id: int, result: ChunkProcessAns):
        """Обработка результата от ChunkProcessor"""
        if result.status == 'ok':
            # Модель приняла чанк, продолжаем
            pass
            
        elif result.status == 'answer':
            # Отправляем распознанный текст
            await self.send_message(user_id, json.dumps({
                'type': MessageType.PROCESSING_RESULT,
                'status': 'success',
                'text': result.content,
                'timestamp': datetime.now().timestamp()
            }))
            
        elif result.status == 'bad':
            # Отправляем ошибку и завершаем сессию
            await self.send_error(user_id, f"Model error: {result.content}")
            await self.force_end_session()

    async def handle_audio_end(self, user_id: int, data: dict):
        """Завершение сессии с проверкой прав"""
        if not self.is_session_active or user_id != self.active_user_id:
            return
            
        await self.force_end_session()
        
        await self.send_message(user_id, json.dumps({
            'type': MessageType.PROCESSING_END,
            'message': 'Audio session completed'
        }))

    async def force_end_session(self):
        """Принудительное завершение сессии"""
        if self.is_session_active:
            duration = (datetime.now() - self.session_start_time).total_seconds()
            self.logger.info(f"Session ended. Chunks: {self.chunks_processed}, Duration: {duration:.1f}s")
            
            self.is_session_active = False
            self.session_start_time = None
            self.chunks_processed = 0
            self.active_user_id = None
    
    async def send_error(self, user_id: int, error_message: str) -> bool:
        """Отправка сообщения об ошибке"""
        if not self.is_user_connected(user_id):
            return False
        
        try:
            error_data = json.dumps({
                'type': MessageType.ERROR,
                'error': error_message,
                'timestamp': datetime.now().timestamp(),
                'user_id': user_id
            })
            await self.active_connections[user_id].send_text(error_data)
            self.logger.error(f"Error sent to user {user_id}: {error_message}")
            return True
        except Exception as e:
            self.logger.error(f"Failed to send error to user {user_id}: {e}")
            await self.disconnect(user_id)
            return False

    async def disconnect(self, user_id: int):
        """При отключении завершаем сессию если это активный пользователь"""
        async with self.lock:
            if user_id == self.active_user_id:
                await self.force_end_session()
                
            if user_id in self.active_connections:
                try:
                    await self.active_connections[user_id].close()
                except:
                    pass
                del self.active_connections[user_id]
                del self.connection_times[user_id]
                self.logger.info(f"User {user_id} disconnected")