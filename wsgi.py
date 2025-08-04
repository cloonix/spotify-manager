import os
import database
from app import app

database.DB_PATH = os.environ.get("DATABASE", "spotify_manager.db")
database.create_tables()