from apscheduler.schedulers.asyncio import AsyncIOScheduler
from app.services.lifecycle import lifecycle_service
from app.services.relationships import relationship_service
from app.services.notification import notification_service
from app.schemas.notification import NotificationCreate, NotificationType
from datetime import datetime, timezone
import logging

logger = logging.getLogger(__name__)
scheduler = AsyncIOScheduler()

async def fire_watch_notification(session_id: str):
    logger.info(f"Firing scheduled watch notification for session: {session_id}")
    try:
        from app.services.watch import watch_service
        from bson import ObjectId
        doc = await watch_service.watch_sessions.find_one({"_id": ObjectId(session_id)})
        if doc and doc.get("is_accepted_user_1") and doc.get("is_accepted_user_2"):
            # Ensure it hasn't been fired manually or already
            if not doc.get("notification_fired"):
                await watch_service.watch_sessions.update_one({"_id": ObjectId(session_id)}, {"$set": {"notification_fired": True}})
                for uid in doc["user_ids"]:
                    await notification_service.schedule_notification(
                        sender_id="system",
                        payload=NotificationCreate(
                            recipient_id=uid,
                            title="It's Showtime!",
                            message=f"Time to watch {doc.get('show_name')}! Hit ready.",
                            type=NotificationType.SYSTEM,
                            scheduled_for=datetime.now(timezone.utc),
                            timezone="UTC"
                        )
                    )
    except Exception as e:
        logger.error(f"Error firing watch notification: {e}")

def schedule_watch_session(session_id: str, run_date: datetime):
    job_id = f"watch_{session_id}"
    # Remove existing job if any
    if scheduler.get_job(job_id):
        scheduler.remove_job(job_id)
    
    # Only schedule if the date is in the future
    if run_date > datetime.now(timezone.utc):
        scheduler.add_job(fire_watch_notification, 'date', run_date=run_date, args=[session_id], id=job_id)

async def _process_user_phase(u: dict):
    try:
        user_id = str(u["_id"])
        partner = u.get("partner")
        partner_id = partner.get("user_id") if partner else None
        if not partner_id:
            return
            
        data = await lifecycle_service.get_cycle_stats(user_id)
        if data and data.get("stats"):
            stats = data["stats"]
            days_since_start = stats["days_since_start"]
            avg_cycle = stats["cycle_length_used"]
            days_in_current_cycle = days_since_start % avg_cycle
            
            phase_entered = None
            if days_in_current_cycle == 0 and days_since_start > 0:
                phase_entered = "Menstrual"
            elif days_in_current_cycle == 5:
                phase_entered = "Follicular"
            elif days_in_current_cycle == 13:
                phase_entered = "Ovulatory"
            elif days_in_current_cycle == 16:
                phase_entered = "Luteal"
            
            if phase_entered:
                owner_name = u.get("name", "Your partner")
                await notification_service.schedule_notification(
                    sender_id=user_id,
                    payload=NotificationCreate(
                        recipient_id=partner_id,
                        type=NotificationType.CYCLE_UPDATE,
                        title="Phase Change",
                        message=f"{owner_name} just entered her {phase_entered} phase.",
                        scheduled_for=datetime.now(timezone.utc),
                        timezone="UTC"
                    )
                )
    except Exception as e:
        logger.error(f"Error processing phase change for user {u.get('_id')}: {e}")

async def check_phase_changes():
    """Nightly job to check female users' cycles and send notifications to partners on phase changes."""
    logger.info("Running nightly phase change check...")
    try:
        import asyncio
        # Target only female users with an active partner and sharing enabled
        cursor = relationship_service.collection.find({
            "gender": "Female",
            "partner.user_id": {"$exists": True, "$ne": None},
            "cycle_data_shared": {"$ne": False}
        })
        users = await cursor.to_list(length=None)
        
        # Process in concurrent chunks of 25 to avoid blocking the event loop
        chunk_size = 25
        for i in range(0, len(users), chunk_size):
            chunk = users[i:i + chunk_size]
            await asyncio.gather(*[_process_user_phase(u) for u in chunk])
            await asyncio.sleep(0.05)
    except Exception as e:
        logger.error(f"Error in check_phase_changes: {e}")

async def check_upcoming_dates():
    """Check for accepted dates happening in exactly 1 hour and send push notifications."""
    logger.info("Checking for upcoming dates...")
    try:
        from app.services.dates import date_service
        from datetime import timedelta
        
        now = datetime.now(timezone.utc)
        # Look for dates starting between 55 and 70 minutes from now
        start_time = now + timedelta(minutes=55)
        end_time = now + timedelta(minutes=70)
        
        cursor = date_service.dates_collection.find({
            "status": "Accepted",
            "utc_timestamp": {"$gte": start_time, "$lte": end_time},
            "notification_fired": {"$ne": True} # Only send once
        })
        
        dates = await cursor.to_list(length=None)
        for d in dates:
            # Mark as fired
            await date_service.dates_collection.update_one(
                {"_id": d["_id"]},
                {"$set": {"notification_fired": True}}
            )
            
            # Notify both partners
            users_to_notify = [d["creator_id"], d["partner_id"]]
            for uid in users_to_notify:
                await notification_service.schedule_notification(
                    sender_id="system",
                    payload=NotificationCreate(
                        recipient_id=uid,
                        type=NotificationType.SYSTEM,
                        title="🍷 Upcoming Date in 1 Hour!",
                        message=f"Your date at \"{d.get('where', 'Date')}\" starts in 1 hour! Tap to view details.",
                        scheduled_for=datetime.now(timezone.utc),
                        timezone="UTC",
                        metadata={"screen": "Dates", "date_id": str(d["_id"]), "action": "upcoming_reminder"}
                    )
                )
    except Exception as e:
        logger.error(f"Error in check_upcoming_dates: {e}")

def start_scheduler():
    # Run every day at midnight UTC
    scheduler.add_job(check_phase_changes, 'cron', hour=0, minute=0)
    # Run every 15 minutes to check for upcoming dates
    scheduler.add_job(check_upcoming_dates, 'cron', minute='*/15')
    scheduler.start()
