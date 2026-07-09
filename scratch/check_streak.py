import asyncio
from motor.motor_asyncio import AsyncIOMotorClient

async def check():
    client = AsyncIOMotorClient("mongodb+srv://new_user_0:Q70h3dmIcznI8hrr@cluster0.f5qcyev.mongodb.net/?appName=Cluster0")
    db = client["loukarver"]
    
    user = await db.users.find_one({"email": "x2@yopmail.com"})
    if not user:
        print("User not found!")
        return
    
    print(f"Found User ID: {user['_id']}")
    print(f"Current stored streak: {user.get('current_streak')}")
    
    rituals = await db.ritual_completions.find({"user_id": str(user["_id"])}).to_list(length=100)
    print(f"Total rituals found: {len(rituals)}")
    
    dates = [r.get("completed_date") for r in rituals]
    print(f"Completed dates: {dates}")

if __name__ == "__main__":
    asyncio.run(check())
