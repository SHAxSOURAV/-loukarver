import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
import os
from dotenv import load_dotenv

async def main():
    load_dotenv()
    uri = os.getenv("MONGODB_URI", "mongodb://localhost:27017")
    client = AsyncIOMotorClient(uri)
    db = client[os.getenv("DATABASE_NAME", "loukarver")]
    
    user = await db.users.find_one({"email": "x5@yopmail.com"})
    print("User found:", user)

if __name__ == "__main__":
    asyncio.run(main())
