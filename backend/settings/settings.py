import multiprocessing as mp

from pydantic import BaseModel
from pydantic_settings import BaseSettings, SettingsConfigDict
import config.config as c


class Postgres(BaseModel):
    database: str = c.PG_DATABASE
    host: str = c.PG_HOST
    port: int = c.PG_PORT
    username: str = c.PG_USER
    password: str = c.PG_PASSWORD
    

class Uvicorn(BaseModel):
    host: str = "0.0.0.0"
    port: int = 8000
    workers: int = mp.cpu_count()*2 + 1
    
class Analyzer(BaseModel):
    api_key: str = c.ANALYZER_API_KEY
    model_name: str = c.ANALYZER_MODEL
    temperature: float = 0.3
    url: str = c.ANALYZER_URL
    timeout_sec: float = 60.0
    

class _Settings(BaseSettings):
    pg: Postgres = Postgres()
    uvicorn: Uvicorn = Uvicorn()
    analyzer: Analyzer = Analyzer()
    
    model_config = SettingsConfigDict(env_file=".env", env_prefix="app_", env_nested_delimiter="__")
    
    
settings = _Settings()
 