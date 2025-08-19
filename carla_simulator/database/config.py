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


def _build_url_from_env() -> str | None:
    """Construct DATABASE_URL from discrete env vars if available.

    Recognized envs: DATABASE_URL (direct), or DB_HOST/DB_HOSTIP, DB_PORT, DB_NAME, DB_USER, DB_PASSWORD
    and common Postgres variable names POSTGRES_DB, POSTGRES_USER, POSTGRES_PASSWORD.
    """
    # Direct url wins
    env_url = os.environ.get("DATABASE_URL")
    if env_url:
        return env_url

    host = os.environ.get("DB_HOST") or os.environ.get("DB_HOSTIP")
    name = os.environ.get("DB_NAME") or os.environ.get("POSTGRES_DB")
    user = os.environ.get("DB_USER") or os.environ.get("POSTGRES_USER")
    password = os.environ.get("DB_PASSWORD") or os.environ.get("POSTGRES_PASSWORD")
    port = os.environ.get("DB_PORT")

    if host or name or user or password or port:
        host = host or "localhost"
        name = name or "carla_simulator"
        user = user or "postgres"
        password = password or "postgres"
        port = port or "5432"
        return f"postgresql://{user}:{password}@{host}:{port}/{name}"

    return None


# Database configuration resolution order:
# 1) env DATABASE_URL
# 2) env parts (DB_HOST/DB_HOSTIP, DB_PORT, DB_NAME, DB_USER, DB_PASSWORD)
# 3) YAML database.url
# 4) local default
DATABASE_URL = (
    _build_url_from_env()
    or _load_database_url_from_yaml("postgresql://postgres:postgres@localhost:5432/carla_simulator")
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
