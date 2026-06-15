from sqlalchemy.ext.asyncio import AsyncSession
from app import models

async def create_log(db: AsyncSession, user_id: int, document_id: int | None, action: str, description: str, ip: str):
    log = models.Log(
        user_id=user_id,
        document_id=document_id,
        action=action,
        description_action=description,
        ip_address=ip
    )
    db.add(log)
    await db.commit()