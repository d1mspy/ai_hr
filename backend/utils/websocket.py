from fastapi import WebSocket
from typing import Dict, Optional
import asyncio
from pydantic import BaseModel
import numpy as np
from enum import Enum
import logging
from .voice.сhunk_processor import ChunkProcessor, ChunkProcessAns
from handling_llm import ResponseStatus, InterviewResponse
from typing import Dict, List, Optional, Callable
from utils.voice.voice_generator import VoiceGenerator
import json
import base64
from datetime import datetime
import torch

class MessageType(str, Enum):
    AUDIO_START = "audio_start"
    AUDIO_CHUNK = "audio_chunk" 
    AUDIO_END = "audio_end"
    PROCESSING_START = "processing_start"
    PROCESSING_END = "processing_end"
    PROCESSING_RESULT = "processing_result"
    ERROR = "error"
    LLM_RESPONSE = "llm_response"  # Новый тип для ответов LLM
    AUDIO_RESPONSE = "audio_response"  # Новый тип для аудио ответов

class WSMessage(BaseModel):
    type: MessageType
    user_id: int
    data: Optional[dict] = None
    chunk: Optional[bytes] = None
    timestamp: float

# Инициализация голосового генератора (должна быть где-то в конфигурации)
voice_generator = VoiceGenerator()

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
    def __init__(self, 
                 chunk_processor: ChunkProcessor, 
                 llm_model,  # Модель LLM
                 process_text_callback: Optional[Callable] = None):
        super().__init__()
        self.voice_generator = voice_generator  # Генератор голоса
        self.chunk_processor = chunk_processor  # Процессор аудио чанков
        self.llm_model = llm_model  # Модель LLM
        self.process_text_callback = process_text_callback  # Колбэк для обработки текста
        
        self.is_session_active = False
        self.session_start_time = None
        self.chunks_processed = 0
        self.active_user_id = None
        
        # Состояние для накопления текста
        self.current_interview_text = ""
        self.pending_user_response = ""
        self.awaiting_user_response = False

    async def handle_audio_start(self, user_id: int, data: dict):
        """Начало сессии"""
        if self.is_session_active:
            await self.send_error(user_id, "Another session is already active")
            return
            
        self.is_session_active = True
        self.active_user_id = user_id
        self.session_start_time = datetime.now()
        self.chunks_processed = 0
        self.chunk_processor.reset()
        
        # Сбрасываем состояние текста
        self.current_interview_text = ""
        self.pending_user_response = ""
        self.awaiting_user_response = False
        
        await self.send_message(user_id, json.dumps({
            'type': MessageType.PROCESSING_START,
            'message': 'Ready to receive audio'
        }))

    async def handle_audio_chunk(self, user_id: int, data: dict):
        """Обработка чанка с накоплением текста"""
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
            
            result = await self.chunk_processor(audio_float)
            self.chunks_processed += 1
            
            await self.handle_model_result(user_id, result)
            
        except Exception as e:
            await self.send_error(user_id, f"Processing error: {e}")

    async def handle_model_result(self, user_id: int, result: ChunkProcessAns):
        """Обработка результата от ChunkProcessor"""
        if result.status == 'ok':
            # Модель приняла чанк, продолжаем отправлять следующие
            pass
            
        elif result.status == 'answer':
            # ⭐⭐ КОНКАТЕНАЦИЯ ПРЕДЛОЖЕНИЙ ⭐⭐
            self.pending_user_response += result.content + " "
            self.current_interview_text += result.content + " "
            # Просто накапливаем текст, ничего не отправляем
            
        elif result.status == 'stop_answer':
            # ⭐⭐ ФИНАЛЬНЫЙ ТЕКСТ - ОТПРАВЛЯЕМ В LLM ⭐⭐
            self.pending_user_response += result.content + " "
            self.current_interview_text += result.content + " "
            
            # ⭐⭐ ПЕРЕДАЕМ ВЕСЬ НАКОПЛЕННЫЙ ТЕКСТ В LLM ⭐⭐
            if self.process_text_callback and self.awaiting_user_response:
                llm_response = await self.process_text_callback(
                    user_id=user_id,
                    text=self.pending_user_response.strip(),  # Весь накопленный текст
                    llm_model=self.llm_model,
                    connection_manager=self
                )
                
                # Генерируем аудио из ответа LLM
                await self.send_llm_response_in_audio(user_id, llm_response.text)
                
                self.pending_user_response = ""  # Сбрасываем для следующего ответа
            
        elif result.status == 'bad':
            await self.send_error(user_id, f"Model error: {result.content}")
            await self.force_end_session()

    async def send_llm_response_in_audio(self, user_id: int, response_text: str):
        """Генерация аудио и отправка чанков через вебсокет"""
        if not self.is_user_connected(user_id):
            return False
        
        try:
            # Генерируем аудио
            audio_tensor = self.voice_generator(response_text)
            
            # Конвертируем в bytes
            audio_numpy = audio_tensor.numpy().astype(np.int16)
            audio_bytes = audio_numpy.tobytes()
            
            # Разбиваем на чанки для отправки
            chunk_size = 512  # Размер чанка
            for i in range(0, len(audio_bytes), chunk_size):
                chunk = audio_bytes[i:i+chunk_size]
                
                # Отправляем чанк аудио
                await self.send_bytes(user_id, chunk)
                
                # Небольшая задержка для избежания перегрузки
                await asyncio.sleep(0.01)
            
            # Отправляем сообщение о завершении аудио
            await self.send_message(user_id, json.dumps({
                'type': MessageType.AUDIO_RESPONSE,
                'status': 'completed',
                'timestamp': datetime.now().timestamp()
            }))
            
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to generate/send audio for user {user_id}: {e}")
            return False

    async def handle_audio_end(self, user_id: int, data: dict):
        """Завершение сессии"""
        if not self.is_session_active or user_id != self.active_user_id:
            return
            
        # ОБРАБАТЫВАЕМ ПОСЛЕДНИЙ НАКОПЛЕННЫЙ ТЕКСТ
        if self.pending_user_response.strip() and self.process_text_callback and self.awaiting_user_response:
            llm_response = await self.process_text_callback(
                user_id=user_id,
                text=self.pending_user_response.strip(),
                llm_model=self.llm_model,
                connection_manager=self
            )
            
            # Отправляем текстовый ответ LLM
            await self.send_message(user_id, json.dumps({
                'type': MessageType.LLM_RESPONSE,
                'text': llm_response.text,
                'current_topic': llm_response.current_topic,
                'timestamp': datetime.now().timestamp()
            }))
            
            # Генерируем аудио из ответа LLM и отправляем
            await self.send_llm_response_in_audio(user_id, llm_response.text)
        
        await self.force_end_session()
        
        await self.send_message(user_id, json.dumps({
            'type': MessageType.PROCESSING_END,
            'message': 'Audio session completed',
            'full_text': self.current_interview_text.strip()
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
            self.awaiting_user_response = False
            self.pending_user_response = ""