from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine, AsyncSession
from settings.settings import settings

def pg_connection() -> async_sessionmaker[AsyncSession]:
    
    engine = create_async_engine(
        f"postgresql+asyncpg://{settings.pg.username}:{settings.pg.password}@"
        f"{settings.pg.host}:{settings.pg.port}/{settings.pg.database}"
        )
    return async_sessionmaker(autocommit=False, autoflush=False, bind=engine)
