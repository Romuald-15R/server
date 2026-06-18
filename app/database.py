import os
from dotenv import load_dotenv
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker, declarative_base

# Load .env (LOCAL ONLY)
load_dotenv()

# Get DATABASE_URL + manadio raha misy "DATABASE_URL=" eo aloha
DATABASE_URL = os.getenv("DATABASE_URL", "")

# Fix: strip prefix "DATABASE_URL=" raha misy
if DATABASE_URL.startswith("DATABASE_URL="):
    DATABASE_URL = DATABASE_URL[len("DATABASE_URL="):]

# Safety check
if not DATABASE_URL:
    raise ValueError("DATABASE_URL is not set. Check environment variables or .env file.")

# Create async engine
engine = create_async_engine(
    DATABASE_URL,
    echo=False,
    pool_pre_ping=True
)

# Session factory
AsyncSessionLocal = sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False
)

# Base for models
Base = declarative_base()

# FastAPI dependency
async def get_db():
    async with AsyncSessionLocal() as session:
        yield session