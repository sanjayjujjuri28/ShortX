from typing import Generator
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker, Session
from app.config import settings

# Normalize database URL (handle empty string, convert postgres:// or postgresql:// to postgresql+psycopg2://)
raw_url = (settings.DATABASE_URL or "").strip()
if not raw_url:
    db_url = "sqlite:///./shortx.db"
elif raw_url.startswith("postgres://"):
    db_url = raw_url.replace("postgres://", "postgresql+psycopg2://", 1)
elif raw_url.startswith("postgresql://") and not raw_url.startswith("postgresql+"):
    db_url = raw_url.replace("postgresql://", "postgresql+psycopg2://", 1)
else:
    db_url = raw_url

# Engine configuration
connect_args = {}
if db_url.startswith("sqlite"):
    connect_args = {"check_same_thread": False}

engine = create_engine(
    db_url,
    connect_args=connect_args,
    pool_pre_ping=True,
    echo=False
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def get_db() -> Generator[Session, None, None]:
    """Dependency that yields a database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """Initializes database tables."""
    # Import models so that they are registered on the metadata
    import app.models  # noqa: F401
    Base.metadata.create_all(bind=engine)
