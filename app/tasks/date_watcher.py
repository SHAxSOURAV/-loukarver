import asyncio
from datetime import datetime, timezone
from app.services.dates import date_service
from app.services.notification import notification_service
from app.schemas.notification import NotificationCreate

async def watch_dates():
    # Delay initial execution to ensure FastAPI event loop and Motor connections are fully initialized
    await asyncio.sleep(10)
    while True:
        try:
            now = datetime.now(timezone.utc)
            # Find dates that are accepted, have an exact timestamp in the past, and haven't been notified yet
            query = {
                "status": "Accepted",
                "utc_timestamp": {"$lte": now, "$ne": None},
                "notification_fired": {"$ne": True}
            }
            
            cursor = date_service.dates_collection.find(query)
            async for doc in cursor:
                # Need to ask for completion
                for target_id in [doc["creator_id"], doc["partner_id"]]:
                    try:
                        await notification_service.create_notification(
                            user_id=target_id,
                            payload=NotificationCreate(
                                title="Date Completed?",
                                body="Did you complete your date? Tap to confirm.",
                                type="DATE_COMPLETION_REQUEST"
                            )
                        )
                    except Exception as e:
                        print(f"Failed to send completion notification to {target_id}: {e}")
                
                # Mark as fired
                await date_service.dates_collection.update_one(
                    {"_id": doc["_id"]},
                    {"$set": {"notification_fired": True}}
                )
                
        except Exception as e:
            print(f"Error in date_watcher: {e}")
            
        await asyncio.sleep(60) # Check every minute

def start_date_watcher():
    asyncio.create_task(watch_dates())
