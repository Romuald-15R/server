from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app import models, schemas, auth
from app.database import get_db
from typing import List

router = APIRouter(prefix="/api/categories", tags=["categories"])

@router.get("/", response_model=List[schemas.CategoryOut])
async def get_categories(db: AsyncSession = Depends(get_db), current_user: models.User = Depends(auth.get_current_user)):
    result = await db.execute(select(models.Category))
    return result.scalars().all()

@router.post("/", response_model=schemas.CategoryOut)
async def create_category(
    cat: schemas.CategoryCreate,
    db: AsyncSession = Depends(get_db),
    current_admin: models.User = Depends(auth.get_current_admin)
):
    new_cat = models.Category(**cat.model_dump())
    db.add(new_cat)
    await db.commit()
    await db.refresh(new_cat)
    return new_cat

@router.put("/{cat_id}", response_model=schemas.CategoryOut)
async def update_category(
    cat_id: int,
    cat: schemas.CategoryCreate,
    db: AsyncSession = Depends(get_db),
    current_admin: models.User = Depends(auth.get_current_admin)
):
    category = await db.get(models.Category, cat_id)
    if not category:
        raise HTTPException(status_code=404, detail="Category not found")
    for key, value in cat.model_dump().items():
        setattr(category, key, value)
    await db.commit()
    await db.refresh(category)
    return category

@router.delete("/{cat_id}")
async def delete_category(
    cat_id: int,
    db: AsyncSession = Depends(get_db),
    current_admin: models.User = Depends(auth.get_current_admin)
):
    category = await db.get(models.Category, cat_id)
    if not category:
        raise HTTPException(status_code=404, detail="Category not found")
    await db.delete(category)
    await db.commit()
    return {"message": "Category deleted"}