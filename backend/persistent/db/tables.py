from persistent.db.base import Base, WithId, With_created_at, With_updated_at
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy import Column, Text, INTEGER


class User(Base, With_created_at, With_updated_at):
    __tablename__ = "user"
    id = Column(INTEGER, primary_key=True)
    summary = Column(Text, nullable=False)
    meta = Column(Text, nullable=False)
    hard_topics = Column(JSONB, nullable=False)
    soft_topics = Column(JSONB, nullable=False)
    