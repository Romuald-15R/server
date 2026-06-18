import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.database import engine, Base
from app.routers import (
    auth,
    users,
    categories,
    documents,
    logs,
    notifications,
    dashboard
)

# Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# Lifespan (startup/shutdown safe for Render)
@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("🚀 Starting DocArchive API...")

    try:
        # Create DB tables safely
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        logger.info("✅ Database tables ready")
    except Exception as e:
        logger.error(f"❌ Database init error: {e}")

    yield

    logger.info("🛑 Shutting down DocArchive API...")
    await engine.dispose()


# FastAPI app
app = FastAPI(
    title="DocArchive API",
    description="API de numérisation et archivage intelligent de documents administratifs",
    version="1.0.0",
    lifespan=lifespan
)

# CORS (OK for Flutter + mobile app)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # change in production if needed
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routers
app.include_router(auth.router)
app.include_router(users.router)
app.include_router(categories.router)
app.include_router(documents.router)
app.include_router(logs.router)
app.include_router(notifications.router)
app.include_router(dashboard.router)


# Root endpoint
@app.get("/")
async def root():
    return {
        "message": "DocArchive API running",
        "status": "ok"
    }


# Health check (VERY IMPORTANT for Render)
@app.get("/health")
async def health_check():
    return {"status": "healthy"}