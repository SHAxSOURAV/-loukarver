import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
import datetime
import zoneinfo

async def clean_db():
    client = AsyncIOMotorClient("mongodb+srv://new_user_0:Q70h3dmIcznI8hrr@cluster0.f5qcyev.mongodb.net/?appName=Cluster0")
    db = client["loukarver"]
    
    tz = zoneinfo.ZoneInfo("UTC")
    today_str = datetime.datetime.now(tz).strftime("%m.%d.%Y")
    
    # Drop today's answers
    res = await db.vibe_user_answers.delete_many({"date": today_str})
    print(f"Deleted {res.deleted_count} user_answers for today.")
    
    # Drop today's streak dates so they can restart today
    await db.vibe_user_streaks.update_many(
        {"last_answered_date": today_str},
        {"$set": {"last_answered_date": "00.00.0000", "current_streak": 0}}
    )
    print("Reset streaks for today.")
    
asyncio.run(clean_db())
