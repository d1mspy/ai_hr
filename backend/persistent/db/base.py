from sqlalchemy.orm import declarative_base
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy import Column, Text, DateTime
from datetime import datetime
import uuid

Base = declarative_base()

# класс для добавления столбца id в таблицу
class WithId:
    __abstract__ = True

    id = Column(UUID(as_uuid=True), default=uuid.uuid4, primary_key=True)


# класс для добавления поля created_at
class With_created_at():
    __abstract__ = True
    
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    

# класс для добавления поля updated_at
class With_updated_at():
    __abstract__ = True
    
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
