from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from app import models, schemas, auth
from app.database import get_db
from app.services.log_service import create_log
from typing import List
import os
import shutil

router = APIRouter(prefix="/api/users", tags=["users"])

# ==================== LISTE TOUS LES UTILISATEURS (admin only) ====================
@router.get("/", response_model=List[schemas.UserOut])
async def get_users(
    db: AsyncSession = Depends(get_db),
    current_admin: models.User = Depends(auth.get_current_admin)
):
    result = await db.execute(select(models.User))
    return result.scalars().all()

# ==================== PROFIL PERSONNEL ====================
@router.get("/me", response_model=schemas.UserOut)
async def get_me(current_user: models.User = Depends(auth.get_current_user)):
    return current_user

@router.put("/me", response_model=schemas.UserOut)
async def update_me(
    user_update: schemas.UserUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user)
):
    if user_update.password:
        user_update.password = auth.get_password_hash(user_update.password)
    for key, value in user_update.model_dump(exclude_unset=True).items():
        setattr(current_user, key, value)
    await db.commit()
    await db.refresh(current_user)
    await create_log(db, current_user.id, None, "UPDATE_PROFILE", f"Updated own profile", "0.0.0.0")
    return current_user

# ==================== UPLOAD PHOTO DE PROFIL ====================
@router.post("/me/photo")
async def upload_profile_photo(
    photo: UploadFile = File(...),
    current_user: models.User = Depends(auth.get_current_user),
    db: AsyncSession = Depends(get_db)
):
    # Créer le dossier uploads/profiles s'il n'existe pas
    upload_dir = "uploads/profiles"
    os.makedirs(upload_dir, exist_ok=True)
    
    # Générer un nom de fichier unique
    file_extension = os.path.splitext(photo.filename)[1]
    safe_filename = f"user_{current_user.id}_{current_user.nom.replace(' ', '_')}{file_extension}"
    file_path = os.path.join(upload_dir, safe_filename)
    
    # Sauvegarder le fichier
    try:
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(photo.file, buffer)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Could not save file: {e}")
    
    # Mettre à jour le chemin dans la base
    current_user.photo_profil = file_path
    await db.commit()
    await db.refresh(current_user)
    
    await create_log(db, current_user.id, None, "UPDATE_PROFILE", f"Changed profile photo", "0.0.0.0")
    return {"photo_url": file_path, "message": "Photo uploaded successfully"}

# ==================== CHANGER LE RÔLE D'UN UTILISATEUR (admin only) ====================
@router.put("/{user_id}/role")
async def change_user_role(
    user_id: int,
    role_data: dict,
    db: AsyncSession = Depends(get_db),
    current_admin: models.User = Depends(auth.get_current_admin)
):
    new_role = role_data.get("role")
    if new_role not in ["admin", "employee"]:
        raise HTTPException(status_code=400, detail="Invalid role. Must be 'admin' or 'employee'")
    
    user = await db.get(models.User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    old_role = user.role
    user.role = new_role
    await db.commit()
    
    await create_log(db, current_admin.id, None, "MANAGE_USER", 
                     f"Changed user {user.email} role from {old_role} to {new_role}", "0.0.0.0")
    return {"message": "Role updated successfully", "new_role": new_role}

# ==================== CHANGER LE STATUT (bloquer/débloquer) ====================
@router.put("/{user_id}/status")
async def toggle_user_status(
    user_id: int,
    statut: str,
    db: AsyncSession = Depends(get_db),
    current_admin: models.User = Depends(auth.get_current_admin)
):
    if statut not in ["actif", "bloque"]:
        raise HTTPException(status_code=400, detail="Invalid status")
    
    user = await db.get(models.User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    old_status = user.statut
    user.statut = statut
    await db.commit()
    
    await create_log(db, current_admin.id, None, "MANAGE_USER", 
                     f"Changed user {user.email} status from {old_status} to {statut}", "0.0.0.0")
    return {"message": "Status updated"}

# ==================== SUPPRIMER UN UTILISATEUR (admin only) ====================
@router.delete("/{user_id}")
async def delete_user(
    user_id: int,
    db: AsyncSession = Depends(get_db),
    current_admin: models.User = Depends(auth.get_current_admin)
):
    user = await db.get(models.User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Empêcher la suppression de son propre compte (optionnel)
    if user.id == current_admin.id:
        raise HTTPException(status_code=400, detail="Cannot delete your own account")
    
    await db.delete(user)
    await db.commit()
    await create_log(db, current_admin.id, None, "DELETE_USER", f"Deleted user {user.email} (ID: {user_id})", "0.0.0.0")
    return {"message": "User deleted successfully"}