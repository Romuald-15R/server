from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import func, select
from app import models, auth
from app.database import get_db
from datetime import datetime, timedelta

router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])

@router.get("/stats")
async def get_stats(
    db: AsyncSession = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user)
):
    base_query = select(models.Document).where(models.Document.statut == "actif")
    if current_user.role != "admin":
        base_query = base_query.where(models.Document.user_id == current_user.id)
    
    total_docs = await db.execute(select(func.count()).select_from(base_query.subquery()))
    total_docs = total_docs.scalar()
    
    # Docs par catégorie
    cat_stats = await db.execute(
        select(models.Category.nom, func.count(models.Document.id))
        .join(models.Document, models.Document.categorie_id == models.Category.id, isouter=True)
        .where(models.Document.statut == "actif")
        .group_by(models.Category.id)
    )
    categories = [{"nom": row[0], "count": row[1]} for row in cat_stats.all()]
    
    # Activités récentes (logs)
    recent_logs = await db.execute(
        select(models.Log).order_by(models.Log.created_at.desc()).limit(10)
    )
    logs_list = [{"action": log.action, "created_at": log.created_at.isoformat()} for log in recent_logs.scalars().all()]
    
    return {
        "total_documents": total_docs,
        "documents_by_category": categories,
        "recent_activities": logs_list
    }