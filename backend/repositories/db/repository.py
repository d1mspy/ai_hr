from infrastructure.db.connect import pg_connection
from sqlalchemy import insert, select, update, delete

# класс для взаимодействия с базой данных
class Repository:
    def __init__(self):
        self._sessionmaker = pg_connection()