from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, Boolean, BigInteger
from sqlalchemy.orm import relationship
from datetime import datetime
from app.database import Base

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    nom = Column(String, nullable=False)
    email = Column(String, unique=True, nullable=False, index=True)
    password_hash = Column(String, nullable=False)
    role = Column(String, default="employee")  # admin, employee
    photo_profil = Column(String, nullable=True)
    telephone = Column(String, nullable=True)
    statut = Column(String, default="actif")  # actif, bloque
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    documents = relationship("Document", back_populates="user", cascade="all, delete-orphan")
    logs = relationship("Log", back_populates="user", cascade="all, delete-orphan")
    notifications = relationship("Notification", back_populates="user", cascade="all, delete-orphan")

class Category(Base):
    __tablename__ = "categories"
    id = Column(Integer, primary_key=True, index=True)
    nom = Column(String, unique=True, nullable=False)
    description = Column(Text, nullable=True)
    couleur = Column(String, default="#3498db")
    created_at = Column(DateTime, default=datetime.utcnow)
    
    documents = relationship("Document", back_populates="category")

class Document(Base):
    __tablename__ = "documents"
    id = Column(Integer, primary_key=True, index=True)
    titre = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    file_path = Column(String, nullable=False)
    file_type = Column(String)  # pdf, image
    numero_archive = Column(String, unique=True, nullable=False)
    ocr_text = Column(Text, nullable=True)
    taille_fichier = Column(BigInteger)
    date_scan = Column(DateTime, default=datetime.utcnow)
    date_archivage = Column(DateTime, default=datetime.utcnow)
    statut = Column(String, default="actif")  # actif, supprime, archive
    user_id = Column(Integer, ForeignKey("users.id"))
    categorie_id = Column(Integer, ForeignKey("categories.id"))
    
    user = relationship("User", back_populates="documents")
    category = relationship("Category", back_populates="documents")
    logs = relationship("Log", back_populates="document", cascade="all, delete-orphan")

class Log(Base):
    __tablename__ = "logs"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    document_id = Column(Integer, ForeignKey("documents.id"), nullable=True)
    action = Column(String, nullable=False)
    description_action = Column(Text, nullable=True)
    ip_address = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    user = relationship("User", back_populates="logs")
    document = relationship("Document", back_populates="logs")

class Notification(Base):
    __tablename__ = "notifications"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    titre = Column(String, nullable=False)
    message = Column(Text, nullable=False)
    type = Column(String, default="info")  # info, warning, success
    is_read = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    user = relationship("User", back_populates="notifications")