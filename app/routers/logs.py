from fastapi import APIRouter, Depends, Query, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from app import models, schemas, auth
from app.database import get_db
from typing import List, Optional
from datetime import datetime
import io
import csv

router = APIRouter(prefix="/api/logs", tags=["logs"])

# ==================== LISTE DES LOGS (avec pagination, filtres) ====================
@router.get("/", response_model=List[schemas.LogOut])
async def get_logs(
    skip: int = Query(0, ge=0, description="Nombre d'éléments à ignorer"),
    limit: int = Query(100, ge=1, le=1000, description="Nombre maximum de logs à retourner"),
    action: Optional[str] = Query(None, description="Filtrer par action (LOGIN, UPLOAD, etc.)"),
    start_date: Optional[datetime] = Query(None, description="Date de début (ISO 8601)"),
    end_date: Optional[datetime] = Query(None, description="Date de fin (ISO 8601)"),
    db: AsyncSession = Depends(get_db),
    current_admin: models.User = Depends(auth.get_current_admin)
):
    """
    Récupère les logs système. Accessible uniquement aux administrateurs.
    - Pagination avec `skip` et `limit`
    - Filtre par action
    - Filtre par plage de dates
    """
    conditions = []
    if action:
        conditions.append(models.Log.action == action)
    if start_date:
        conditions.append(models.Log.created_at >= start_date)
    if end_date:
        conditions.append(models.Log.created_at <= end_date)
    
    query = select(models.Log).order_by(models.Log.created_at.desc())
    if conditions:
        query = query.where(and_(*conditions))
    query = query.offset(skip).limit(limit)
    
    result = await db.execute(query)
    return result.scalars().all()

# ==================== EXPORT CSV ====================
@router.get("/export")
async def export_logs_csv(
    action: Optional[str] = Query(None),
    start_date: Optional[datetime] = Query(None),
    end_date: Optional[datetime] = Query(None),
    db: AsyncSession = Depends(get_db),
    current_admin: models.User = Depends(auth.get_current_admin)
):
    """
    Exporte les logs filtrés au format CSV.
    """
    conditions = []
    if action:
        conditions.append(models.Log.action == action)
    if start_date:
        conditions.append(models.Log.created_at >= start_date)
    if end_date:
        conditions.append(models.Log.created_at <= end_date)
    
    query = select(models.Log).order_by(models.Log.created_at.desc())
    if conditions:
        query = query.where(and_(*conditions))
    
    result = await db.execute(query)
    logs = result.scalars().all()
    
    # Création du fichier CSV en mémoire
    output = io.StringIO()
    writer = csv.writer(output, delimiter=';')
    writer.writerow(['ID', 'Utilisateur ID', 'Document ID', 'Action', 'Description', 'Adresse IP', 'Date (UTC)'])
    
    for log in logs:
        writer.writerow([
            log.id,
            log.user_id,
            log.document_id if log.document_id else '',
            log.action,
            log.description_action if log.description_action else '',
            log.ip_address if log.ip_address else '',
            log.created_at.isoformat()
        ])
    
    output.seek(0)
    filename = f"logs_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    
    return StreamingResponse(
        iter([output.getvalue().encode('utf-8-sig')]),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )