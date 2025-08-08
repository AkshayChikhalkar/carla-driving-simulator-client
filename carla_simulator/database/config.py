from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy.pool import QueuePool
import os
import yaml
from carla_simulator.utils.paths import get_config_path

# Schema name
SCHEMA_NAME = "carla_simulator"


def _load_database_url_from_yaml(default_url: str) -> str:
    """Try to read database.url from config/simulation.yaml; fall back to default."""
    try:
        cfg_path = get_config_path("simulation.yaml")
        if os.path.exists(cfg_path):
            with open(cfg_path, "r", encoding="utf-8") as f:
                cfg = yaml.safe_load(f) or {}
                db_cfg = cfg.get("database", {}) or {}
                if isinstance(db_cfg, dict) and db_cfg.get("url"):
                    return str(db_cfg["url"])
    except Exception:
        pass
    return default_url


# Database configuration: strictly from YAML, fallback to local default
DATABASE_URL = _load_database_url_from_yaml(
    "postgresql://postgres:postgres@localhost:5432/carla_simulator"
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
    """Database session generator"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
