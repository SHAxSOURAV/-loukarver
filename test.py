
import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
from app.core.config import settings

async def check():
    client = AsyncIOMotorClient(settings.MONGO_URL)
    db = client[settings.MONGO_DB_NAME]
    
    user_id = '6a486dfa63674360d30c48a4'
    cursor = db.vibe_check_connections.find({'user_id': user_id}, {'partner_id': 1})
    docs = await cursor.to_list(None)
    
    partner_ids = [d['partner_id'] for d in docs]
    print('pids', partner_ids)
    
    c2 = db.vibe_check_profiles.find({'user_id': {'$in': partner_ids}})
    pdocs = await c2.to_list(None)
    print('FOUND with $in:', len(pdocs))

asyncio.run(check())

