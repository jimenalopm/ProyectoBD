import os
from dotenv import load_dotenv

load_dotenv()

DB_USER = os.getenv("DB_USER", "SYS")
DB_PASSWORD = os.getenv("DB_PASSWORD", "")
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = int(os.getenv("DB_PORT", "1521"))
DB_SERVICE = os.getenv("DB_SERVICE", "XEPDB1")
DB_SYSDBA = os.getenv("DB_SYSDBA", "true").lower() == "true"
SECRET_KEY = os.getenv("SECRET_KEY", "dev")
