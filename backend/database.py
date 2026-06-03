from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, DeclarativeBase

from config import settings


# Create the SQLAlchemy engine using the DATABASE_URL from .env
engine = create_engine(
    settings.DATABASE_URL,
    echo=settings.DEBUG,        # Logs all SQL statements when DEBUG=True
    pool_pre_ping=True,         # Checks connection health before use
)

# SessionLocal is the factory for database sessions
# autocommit=False — transactions must be committed explicitly
# autoflush=False  — changes are not flushed to DB until commit or explicit flush
SessionLocal = sessionmaker(
    bind=engine,
    autocommit=False,
    autoflush=False,
)


# Base class for all ORM models — models.py inherits from this
class Base(DeclarativeBase):
    pass


def get_db():
    """
    Dependency function that yields a database session per request.
    Used via FastAPI's dependency injection: db: Session = Depends(get_db)
    Guarantees the session is closed after each request, even on errors.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()