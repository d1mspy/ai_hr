from persistent.db.base import Base, WithId, With_created_at, With_updated_at
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy import Column, Text


class User(Base, WithId, With_created_at, With_updated_at):
    __tablename__ = "user"
    resume = Column(JSONB)
    