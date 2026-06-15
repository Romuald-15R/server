from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.database import engine, Base
from app.routers import auth, users, categories, documents, logs, notifications, dashboard
import logging

# Configuration du logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Gère le cycle de vie de l'application.
    - Crée les tables au démarrage
    - Ferme la connexion à l'arrêt
    """
    logger.info("🚀 Démarrage de DocArchive API...")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        logger.info("✅ Tables vérifiées / créées avec succès")
    yield
    logger.info("🛑 Arrêt de DocArchive API...")
    await engine.dispose()

app = FastAPI(
    title="DocArchive API",
    description="API de numérisation et archivage intelligent de documents administratifs",
    version="1.0.0",
    lifespan=lifespan
)

# Configuration CORS (à restreindre en production)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # À remplacer par les domaines autorisés en production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Inclusion des routeurs
app.include_router(auth.router)
app.include_router(users.router)
app.include_router(categories.router)
app.include_router(documents.router)
app.include_router(logs.router)
app.include_router(notifications.router)
app.include_router(dashboard.router)

@app.get("/")
async def root():
    return {"message": "DocArchive API running", "status": "ok"}

@app.get("/health")
async def health_check():
    """Endpoint pour les sondes de santé (Kubernetes, etc.)"""
    return {"status": "healthy"}