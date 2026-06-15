from fastapi import Depends, HTTPException, status
from app import models, auth

async def get_current_active_user(current_user: models.User = Depends(auth.get_current_user)):
    if current_user.statut != "actif":
        raise HTTPException(status_code=400, detail="Inactive user")
    return current_user

async def get_current_admin(current_user: models.User = Depends(auth.get_current_user)):
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    return current_user