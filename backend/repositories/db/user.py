from persistent.db.tables import User
from infrastructure.db.connect import pg_connection
from sqlalchemy import insert, select, update, delete, exists
from typing import List, Dict, Optional
from schemas.docs import InterviewDTO


class UserRepository:
    def __init__(self):
        self._sessionmaker = pg_connection()
        
    # тестовая запись
    async def put_user(self, 
                       summary: str, 
                       meta: str, 
                       hard_topics: List[Dict[str, str]], 
                       soft_topics: List[Dict[str, str]],
                    ) -> int | None:
        
        stmp = insert(User).values({"summary": summary, 
                                    "meta": meta, 
                                    "hard_topics": hard_topics, 
                                    "soft_topics": soft_topics,
                                    }).returning(User.id)
    
        async with self._sessionmaker() as session:
            result = await session.execute(stmp)
            await session.commit()
            
            # Получаем ID вставленной записи
            user_id = result.scalar()
            
        return user_id
    
    
    async def get_data_by_id(self, user_id: int) -> Optional[InterviewDTO]:
        stmt = (
            select(
                User.summary.label("summary"),
                User.meta.label("meta"),
                User.hard_topics.label("hard_topics"),
                User.soft_topics.label("soft_topics"),
            ).where(User.id == user_id).limit(1)
        )

        async with self._sessionmaker() as session:
            res = await session.execute(stmt)
            row = res.mappings().first()

        if row is None:
            return None

        return InterviewDTO(
            summary=row["summary"] or "",
            meta=row["meta"] or "",
            hard_topics=row["hard_topics"] or [],
            soft_topics=row["soft_topics"] or [],
        )
    
    async def check_user(self, user_id) -> bool:
        stmp = select(exists().where(User.id == user_id))
        
        async with self._sessionmaker() as session:
            result = await session.execute(stmp)
            exists_flag = result.scalar()  # Возвращает True/False
            
        return bool(exists_flag)