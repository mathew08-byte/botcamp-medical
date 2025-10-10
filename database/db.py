from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
import os
from .models import Base

# Database URL - prefer env var, default SQLite
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./botcamp_medical.db")

# Normalize async URL for SQLite when needed
def _to_async_url(url: str) -> str:
    if url.startswith("sqlite+aiosqlite:"):
        return url
    if url.startswith("sqlite:"):
        return url.replace("sqlite:", "sqlite+aiosqlite:", 1)
    # For other drivers, caller must provide a proper async URL
    return url

# Create sync engine/session
engine = create_engine(DATABASE_URL, echo=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Create async engine/session
ASYNC_DATABASE_URL = _to_async_url(DATABASE_URL)
async_engine = create_async_engine(ASYNC_DATABASE_URL, echo=False, future=True)
AsyncSessionLocal = sessionmaker(bind=async_engine, class_=AsyncSession, expire_on_commit=False, autoflush=False, autocommit=False)

def get_db():
    """Yield a synchronous DB session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

async def get_async_db():
    """Async generator yielding an AsyncSession."""
    async with AsyncSessionLocal() as session:
        yield session

def create_tables():
    """Create all database tables (synchronous)."""
    Base.metadata.create_all(bind=engine)

# Backwards-compatible alias expected by other modules
create_tables_sync = create_tables
