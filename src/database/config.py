from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import os

# Schema name
SCHEMA_NAME = 'carla_simulator'

# Database configuration
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://postgres:postgres@localhost:5432/carla_simulator"
)

# Create SQLAlchemy engine with schema
engine = create_engine(
    DATABASE_URL,
    connect_args={'options': f'-csearch_path={SCHEMA_NAME}'}
)

# Create SessionLocal class
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Create Base class
Base = declarative_base()

def get_db():
    """
    Database session generator
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close() 