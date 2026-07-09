import asyncio
import os
from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv

load_dotenv()
MONGO_URL = os.getenv('MONGO_URL', 'mongodb://localhost:27017')
DB_NAME = 'loukarver'

async def main():
    client = AsyncIOMotorClient(MONGO_URL)
    db = client[DB_NAME]
    
    # insert missing answer for lifestyle-pace-s01
    await db['vibe_user_answers'].update_many(
        {}, 
        {'$push': {'answers': {'question_id': 'lifestyle-pace-s01', 'selected_option': 'A'}}}
    )
    print('done')

asyncio.run(main())
