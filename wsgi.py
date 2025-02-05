import os
import database
from app import app

database.DB_PATH = os.environ.get("DATABASE")
if not database.DB_PATH:
    raise RuntimeError("DATABASE environment variable is not set")

database.create_tables()