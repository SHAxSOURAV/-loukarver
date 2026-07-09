import asyncio
from motor.motor_asyncio import AsyncIOMotorClient

async def wipe_all_vibe_data():
    client = AsyncIOMotorClient("mongodb+srv://new_user_0:Q70h3dmIcznI8hrr@cluster0.f5qcyev.mongodb.net/?appName=Cluster0")
    db = client["loukarver"]
    
    print("Wiping vibe data...")
    
    res1 = await db.vibe_user_answers.delete_many({})
    print(f"Deleted {res1.deleted_count} user answers.")
    
    res2 = await db.vibe_daily_pool.delete_many({})
    print(f"Deleted {res2.deleted_count} daily card pools.")
    
    res3 = await db.vibe_cumulative_scores.delete_many({})
    print(f"Deleted {res3.deleted_count} cumulative scores.")
    
    # Reset all streaks
    res4 = await db.vibe_user_streaks.update_many(
        {},
        {"$set": {"last_answered_date": "00.00.0000", "current_streak": 0}}
    )
    print(f"Reset streaks for {res4.modified_count} users.")
    
    print("All vibe card data has been cleared!")

asyncio.run(wipe_all_vibe_data())
