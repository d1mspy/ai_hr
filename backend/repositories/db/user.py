from persistent.db.tables import User
from infrastructure.db.connect import pg_connection
from sqlalchemy import insert, select, update, delete
import json


class UserRepository:
    def __init__(self):
        self._sessionmaker = pg_connection()
        
    # тестовая запись
    async def put_user(self, resume:json) -> None:
        stmp = insert(User).values({"resume": resume})
    
        async with self._sessionmaker() as session:
            await session.execute(stmp) 
            await session.commit()
    
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