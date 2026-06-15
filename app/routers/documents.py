import os
import shutil
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, Query, status
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, and_, or_
from app import models, schemas, auth
from app.database import get_db
from app.services.log_service import create_log
from app.services.notification_service import create_notification
from app.utils.archive_number import generate_archive_number
from typing import List, Optional
from datetime import datetime

router = APIRouter(prefix="/api/documents", tags=["documents"])

UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

# Tailles maximales (en octets) – ajustez selon vos besoins
MAX_FILE_SIZE = 50 * 1024 * 1024  # 50 Mo
ALLOWED_EXTENSIONS = {'.pdf', '.jpg', '.jpeg', '.png'}

def validate_file(file: UploadFile) -> None:
    """Vérifie la taille et l'extension du fichier."""
    # Vérification de l'extension
    ext = os.path.splitext(file.filename)[1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Type de fichier non autorisé. Extensions autorisées : {', '.join(ALLOWED_EXTENSIONS)}"
        )
    # La taille sera vérifiée après sauvegarde (car UploadFile ne donne pas accès à la taille avant lecture)

# ==================== CRÉER UN DOCUMENT ====================
@router.post("/", response_model=schemas.DocumentOut, status_code=status.HTTP_201_CREATED)
async def create_document(
    titre: str = Form(...),
    description: Optional[str] = Form(None),
    file_type: str = Form(...),
    ocr_text: Optional[str] = Form(None),
    categorie_id: int = Form(...),
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user)
):
    # Valider le fichier
    validate_file(file)
    
    archive_num = generate_archive_number()
    file_extension = os.path.splitext(file.filename)[1].lower()
    safe_filename = f"{archive_num}{file_extension}"
    file_location = os.path.join(UPLOAD_DIR, safe_filename)
    
    # Sauvegarder le fichier
    try:
        with open(file_location, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur lors de la sauvegarde du fichier : {e}")
    
    # Vérifier la taille après sauvegarde
    file_size = os.path.getsize(file_location)
    if file_size > MAX_FILE_SIZE:
        os.remove(file_location)  # Supprimer le fichier trop volumineux
        raise HTTPException(status_code=413, detail=f"Fichier trop volumineux. Taille maximale : {MAX_FILE_SIZE // (1024*1024)} Mo")
    if file_size == 0:
        os.remove(file_location)
        raise HTTPException(status_code=400, detail="Le fichier téléchargé est vide")
    
    # Créer le document en base
    new_doc = models.Document(
        titre=titre,
        description=description,
        file_path=file_location,
        file_type=file_type,
        numero_archive=archive_num,
        ocr_text=ocr_text,
        taille_fichier=file_size,
        user_id=current_user.id,
        categorie_id=categorie_id,
        date_scan=datetime.utcnow(),
        date_archivage=datetime.utcnow()
    )
    db.add(new_doc)
    await db.commit()
    await db.refresh(new_doc)
    
    await create_log(db, current_user.id, new_doc.id, "UPLOAD", f"Uploaded document {titre}", "0.0.0.0")
    await create_notification(db, current_user.id, "Document ajouté", f"Votre document {titre} a été archivé avec succès", "success")
    return new_doc

# ==================== LISTER LES DOCUMENTS (avec pagination) ====================
@router.get("/", response_model=List[schemas.DocumentOut])
async def get_documents(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    db: AsyncSession = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user)
):
    query = select(models.Document).where(models.Document.statut == "actif")
    if current_user.role != "admin":
        query = query.where(models.Document.user_id == current_user.id)
    query = query.order_by(models.Document.date_archivage.desc())
    result = await db.execute(query.offset(skip).limit(limit))
    return result.scalars().all()

# ==================== RECHERCHE AVANCÉE ====================
@router.get("/search")
async def search_documents(
    q: Optional[str] = Query(None),
    category_id: Optional[int] = Query(None),
    date_debut: Optional[datetime] = Query(None),
    date_fin: Optional[datetime] = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user)
):
    conditions = [models.Document.statut == "actif"]
    
    if q:
        conditions.append(
            or_(
                models.Document.titre.ilike(f"%{q}%"),
                models.Document.ocr_text.ilike(f"%{q}%")
            )
        )
    if category_id:
        conditions.append(models.Document.categorie_id == category_id)
    if date_debut:
        conditions.append(models.Document.date_scan >= date_debut)
    if date_fin:
        conditions.append(models.Document.date_scan <= date_fin)
    
    query = select(models.Document).where(and_(*conditions))
    if current_user.role != "admin":
        query = query.where(models.Document.user_id == current_user.id)
    query = query.order_by(models.Document.date_archivage.desc())
    result = await db.execute(query)
    return result.scalars().all()

# ==================== DÉTAIL D'UN DOCUMENT ====================
@router.get("/{doc_id}", response_model=schemas.DocumentOut)
async def get_document(
    doc_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user)
):
    doc = await db.get(models.Document, doc_id)
    if not doc or doc.statut != "actif":
        raise HTTPException(status_code=404, detail="Document not found")
    if current_user.role != "admin" and doc.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not your document")
    await create_log(db, current_user.id, doc_id, "VIEW", f"Viewed document {doc.titre}", "0.0.0.0")
    return doc

# ==================== TÉLÉCHARGER LE FICHIER ====================
@router.get("/{doc_id}/download")
async def download_document(
    doc_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user)
):
    doc = await db.get(models.Document, doc_id)
    if not doc or doc.statut != "actif":
        raise HTTPException(status_code=404, detail="Document not found")
    if current_user.role != "admin" and doc.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not your document")
    
    file_path = doc.file_path
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="File missing on server")
    
    filename = f"{doc.numero_archive}{os.path.splitext(file_path)[1]}"
    # Force le téléchargement (attachment) plutôt que l'affichage inline
    return FileResponse(
        file_path,
        filename=filename,
        media_type="application/octet-stream",
        headers={"Content-Disposition": f"attachment; filename=\"{filename}\""}
    )

# ==================== PRÉVISUALISATION DU FICHIER (image ou PDF inline) ====================
@router.get("/{doc_id}/file")
async def get_file_preview(
    doc_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user)
):
    doc = await db.get(models.Document, doc_id)
    if not doc or doc.statut != "actif":
        raise HTTPException(status_code=404, detail="Document not found")
    if current_user.role != "admin" and doc.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not your document")
    
    file_path = doc.file_path
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="File missing")
    
    # Déterminer le type MIME
    if doc.file_type == "pdf":
        media_type = "application/pdf"
    elif doc.file_type == "image":
        ext = os.path.splitext(file_path)[1].lower()
        if ext in [".jpg", ".jpeg"]:
            media_type = "image/jpeg"
        elif ext == ".png":
            media_type = "image/png"
        else:
            media_type = "application/octet-stream"
    else:
        media_type = "application/octet-stream"
    
    return FileResponse(file_path, media_type=media_type)

# ==================== MODIFIER UN DOCUMENT (CORRIGÉ AVEC REFRESH) ====================
@router.put("/{doc_id}")
async def update_document(
    doc_id: int,
    titre: Optional[str] = None,
    description: Optional[str] = None,
    categorie_id: Optional[int] = None,
    db: AsyncSession = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user)
):
    doc = await db.get(models.Document, doc_id)
    if not doc or doc.statut != "actif":
        raise HTTPException(status_code=404, detail="Document not found")
    if current_user.role != "admin" and doc.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not your document")
    
    if titre is not None:
        doc.titre = titre
    if description is not None:
        doc.description = description
    if categorie_id is not None:
        doc.categorie_id = categorie_id
    
    await db.commit()
    await db.refresh(doc)  # ✅ CORRECTION : Rafraîchit l'objet après modification
    
    await create_log(db, current_user.id, doc_id, "UPDATE", f"Updated document {doc.titre}", "0.0.0.0")
    return {"message": "Document updated", "document": doc}

# ==================== SUPPRIMER UN DOCUMENT (soft delete) ====================
@router.delete("/{doc_id}")
async def delete_document(
    doc_id: int,
    hard: bool = Query(False),
    db: AsyncSession = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user)
):
    doc = await db.get(models.Document, doc_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    if current_user.role != "admin" and doc.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not your document")
    
    if hard and current_user.role == "admin":
        if os.path.exists(doc.file_path):
            os.remove(doc.file_path)
        await db.delete(doc)
        await db.commit()
        await create_log(db, current_user.id, doc_id, "DELETE", f"Permanently deleted document {doc.titre}", "0.0.0.0")
        return {"message": "Document permanently deleted"}
    else:
        doc.statut = "supprime"
        await db.commit()
        await create_log(db, current_user.id, doc_id, "DELETE", f"Soft deleted document {doc.titre}", "0.0.0.0")
        return {"message": "Document deleted (soft)"}