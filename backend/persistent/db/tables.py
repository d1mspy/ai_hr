from persistent.db.base import Base, WithId, With_created_at, With_updated_at
from sqlalchemy import Column, Text

# тут будут таблички

# тестовая табличка
class Test(Base, WithId, With_created_at, With_updated_at):
    __tablename__ = "test"
    string = Column(Text)
