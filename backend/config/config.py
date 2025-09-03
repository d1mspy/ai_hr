import os
from dotenv import load_dotenv

load_dotenv()
PG_USER = str(os.getenv('APP_PG__USER'))
PG_HOST = str(os.getenv('APP_PG__HOST'))
PG_PORT = int((os.getenv('APP_PG__PORT')))
PG_PASSWORD = str(os.getenv('APP_PG__PASSWORD'))
PG_DATABASE = str(os.getenv('APP_PG__DATABASE'))