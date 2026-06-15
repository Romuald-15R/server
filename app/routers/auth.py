from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app import models, schemas, auth
from app.database import get_db
from app.services.log_service import create_log

router = APIRouter(prefix="/api/auth", tags=["auth"])

@router.post("/register", response_model=schemas.UserOut)
async def register(user: schemas.UserCreate, db: AsyncSession = Depends(get_db)):
    existing = await db.execute(select(models.User).where(models.User.email == user.email))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Email already registered")
    hashed = auth.get_password_hash(user.password)
    new_user = models.User(
        nom=user.nom, email=user.email, password_hash=hashed,
        role=user.role, telephone=user.telephone
    )
    db.add(new_user)
    await db.commit()
    await db.refresh(new_user)
    await create_log(db, new_user.id, None, "REGISTER", f"User {new_user.email} registered", "0.0.0.0")
    return new_user

@router.post("/login")
async def login(data: schemas.LoginRequest, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(models.User).where(models.User.email == data.email))
    user = result.scalar_one_or_none()
    if not user or not auth.verify_password(data.password, user.password_hash) or user.statut == "bloque":
        raise HTTPException(status_code=401, detail="Invalid credentials")
    token = auth.create_access_token({"sub": str(user.id), "role": user.role})
    await create_log(db, user.id, None, "LOGIN", f"User {user.email} logged in", "0.0.0.0")
    return {"access_token": token, "token_type": "bearer", "role": user.role, "user_id": user.id}