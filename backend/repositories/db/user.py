from persistent.db.tables import User
from infrastructure.db.connect import pg_connection
from sqlalchemy import insert, select, update, delete, exists
import json


class UserRepository:
    def __init__(self):
        self._sessionmaker = pg_connection()
        
    # тестовая запись
    async def put_user(self, resume:json) -> None:
        stmp = insert(User).values({"resume": resume}).returning(User.id)
    
        async with self._sessionmaker() as session:
            result = await session.execute(stmp)
            await session.commit()
            
            # Получаем ID вставленной записи
            user_id = result.scalar()
            
        return user_id
    
    
    async def get_json_by_id(self, user_id) -> list | None:
        stmp = select(User.resume).where(User.id==user_id)
        
        async with self._sessionmaker() as session:
            resp = await session.execute(stmp)
            await session.commit()
        
        row = resp.fetchall()
        if len(row) == 0:
            return None

        result = row[0]
        return result
    
    async def check_user(self, user_id):
        stmp = select(exists().where(User.id == user_id))
        
        async with self._sessionmaker() as session:
            result = await session.execute(stmp)
            exists_flag = result.scalar()  # Возвращает True/False
            
        return bool(exists_flag)