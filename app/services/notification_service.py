from sqlalchemy.ext.asyncio import AsyncSession
from app import models

async def create_notification(db: AsyncSession, user_id: int, titre: str, message: str, type_: str = "info"):
    notif = models.Notification(
        user_id=user_id,
        titre=titre,
        message=message,
        type=type_
    )
    db.add(notif)
    await db.commit()