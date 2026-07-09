import asyncio
from motor.motor_asyncio import AsyncIOMotorClient

async def check_db():
    client = AsyncIOMotorClient("mongodb://localhost:27017")
    db = client["loukarver"]
    
    docs = await db.vibe_user_answers.find({}).to_list(None)
    print("ALL USER ANSWERS:")
    for doc in docs:
        print(doc["user_id"], doc["date"], len(doc.get("answers", [])))
        
asyncio.run(check_db())
