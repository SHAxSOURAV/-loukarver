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

async def check_phase_changes():
    """Nightly job to check female users' cycles and send notifications to partners on phase changes."""
    logger.info("Running nightly phase change check...")
    try:
        # Find all female users
        cursor = relationship_service.collection.find({"gender": "Female"})
        users = await cursor.to_list(length=None)
        
        for u in users:
            user_id = str(u["_id"])
            partner = u.get("partner")
            partner_id = partner.get("user_id") if partner else None
            is_shared = u.get("cycle_data_shared", True)
            
            if partner_id and is_shared:
                data = await lifecycle_service.get_cycle_stats(user_id)
                if data and data.get("stats"):
                    stats = data["stats"]
                    # If days_since_start > avg_cycle, it resets via modulo in get_cycle_stats
                    # But get_cycle_stats returns days_since_start and cycle_length_used
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
        logger.error(f"Error in check_phase_changes: {e}")

def start_scheduler():
    # Run every day at midnight UTC
    scheduler.add_job(check_phase_changes, 'cron', hour=0, minute=0)
    scheduler.start()
