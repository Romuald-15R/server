from pydantic import BaseModel, EmailStr
from datetime import datetime
from typing import Optional, List

# User
class UserBase(BaseModel):
    nom: str
    email: EmailStr
    role: str = "employee"
    telephone: Optional[str] = None
    statut: str = "actif"

class UserCreate(UserBase):
    password: str

class UserUpdate(BaseModel):
    nom: Optional[str] = None
    email: Optional[EmailStr] = None
    role: Optional[str] = None
    telephone: Optional[str] = None
    statut: Optional[str] = None
    password: Optional[str] = None

class UserOut(UserBase):
    id: int
    photo_profil: Optional[str] = None
    created_at: datetime
    class Config: from_attributes = True

class LoginRequest(BaseModel):
    email: str
    password: str

# Category
class CategoryBase(BaseModel):
    nom: str
    description: Optional[str] = None
    couleur: str = "#3498db"

class CategoryCreate(CategoryBase):
    pass

class CategoryOut(CategoryBase):
    id: int
    created_at: datetime
    class Config: from_attributes = True

# Document
class DocumentBase(BaseModel):
    titre: str
    description: Optional[str] = None
    file_type: str
    ocr_text: Optional[str] = None
    categorie_id: int

class DocumentCreate(DocumentBase):
    pass

class DocumentOut(DocumentBase):
    id: int
    numero_archive: str
    file_path: str
    taille_fichier: int
    date_scan: datetime
    date_archivage: datetime
    statut: str
    user_id: int
    class Config: from_attributes = True

# Log
class LogOut(BaseModel):
    id: int
    user_id: int
    document_id: Optional[int]
    action: str
    description_action: Optional[str]
    ip_address: Optional[str]
    created_at: datetime
    class Config: from_attributes = True

# Notification
class NotificationOut(BaseModel):
    id: int
    user_id: int
    titre: str
    message: str
    type: str
    is_read: bool
    created_at: datetime
    class Config: from_attributes = True

class NotificationUpdate(BaseModel):
    is_read: bool