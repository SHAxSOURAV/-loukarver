from motor.motor_asyncio import AsyncIOMotorClient
from app.core.config import settings

class DatabaseManager:
    def __init__(self):
        self._client = None
        self._db = None

    @property
    def client(self) -> AsyncIOMotorClient:
        if self._client is None:
            self._client = AsyncIOMotorClient(settings.MONGO_URL)
        return self._client

    @property
    def db(self):
        if self._db is None:
            self._db = self.client[settings.MONGO_DB_NAME]
        return self._db

db_manager = DatabaseManager()

def get_client() -> AsyncIOMotorClient:
    return db_manager.client

def get_db():
    return db_manager.db
