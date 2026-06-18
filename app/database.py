import os
from dotenv import load_dotenv
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker, declarative_base

# Load .env (LOCAL ONLY)
load_dotenv()

# Get DATABASE_URL
DATABASE_URL = os.getenv("DATABASE_URL")

# Safety check (fail fast if missing)
if not DATABASE_URL:
    raise ValueError("DATABASE_URL is not set. Check environment variables or .env file.")

# Create async engine
engine = create_async_engine(
    DATABASE_URL,
    echo=False,
    pool_pre_ping=True  # helps avoid connection drop issues (IMPORTANT for cloud)
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