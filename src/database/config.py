from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy.pool import QueuePool
import os

# Schema name
SCHEMA_NAME = "carla_simulator"

# Database configuration
DATABASE_URL = os.getenv(
    "DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/carla_simulator"
)

# Create SQLAlchemy engine with schema
engine = create_engine(
    DATABASE_URL, connect_args={"options": f"-csearch_path={SCHEMA_NAME}"}
)

# Create SessionLocal class
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Create declarative base using new SQLAlchemy 2.0 syntax
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
