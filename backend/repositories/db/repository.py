from persistent.db.tables import Test
from infrastructure.db.connect import pg_connection
from sqlalchemy import insert, select, update, delete

# класс для взаимодействия с базой данных
class Repository:
    def __init__(self):
        self._sessionmaker = pg_connection()
        
    # тестовая запись
    async def test_post(self, string: str) -> None:
        stmp = insert(Test).values({"string": string})
    
        async with self._sessionmaker() as session:
            await session.execute(stmp) 
            await session.commit()
    
    # тестовое получение всех записей
    async def test_get(self) -> list | None:
        stmp = select(Test.id, Test.created_at, Test.updated_at)
        
        async with self._sessionmaker() as session:
            resp = await session.execute(stmp)
            await session.commit()
        
        row = list(resp.fetchall())
        if len(row) == 0:
            return None
        
        keys = ["id", "created_at", "updated_at"]
        data = [dict(zip(keys, item)) for item in row]

        return data