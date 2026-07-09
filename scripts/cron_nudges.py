import asyncio
import os
from datetime import datetime, timezone, timedelta
from motor.motor_asyncio import AsyncIOMotorClient

MONGO_URL = os.getenv("MONGO_URL", "mongodb://localhost:27017")
DB_NAME = "loukarver"

async def process_nudges():
    client = AsyncIOMotorClient(MONGO_URL)
    db = client[DB_NAME]
    connections = db["vibe_check_connections"]
    profiles = db["vibe_check_profiles"]
    
    now = datetime.now(timezone.utc)
    
    cursor = connections.find({"status": "active"})
    async for conn in cursor:
        stalled_since = conn.get("stalled_since")
        
        if not stalled_since:
            continue
        
        # Connection is stalled
        if stalled_since.tzinfo is None:
            stalled_since = stalled_since.replace(tzinfo=timezone.utc)
            
        stalled_days = (now - stalled_since).days
        silent_partner_id = conn.get("silent_partner_id")
        user_id = conn["user_id"]
        partner_id = conn["partner_id"]
        
        waiting_partner_id = user_id if silent_partner_id == partner_id else partner_id
        
        if stalled_days == 2:
            print(f"Push to {silent_partner_id}: An anchor is waiting. Answer to release the connection.")
        elif stalled_days == 4:
            print(f"Push to {silent_partner_id}: Still holding. Answer it, or release the connection.")
        elif stalled_days == 7:
            print(f"Push to {silent_partner_id}: FINAL NOTICE: Without an answer in 48 hours, this connection will be released.")
        elif stalled_days >= 9:
            print(f"Auto-releasing connection between {user_id} and {partner_id} due to 9 days silence.")
            await connections.update_many(
                {"$or": [
                    {"user_id": user_id, "partner_id": partner_id},
                    {"user_id": partner_id, "partner_id": user_id}
                ]},
                {"$set": {"status": "released", "released_at": now}}
            )

if __name__ == "__main__":
    asyncio.run(process_nudges())
