# init_db.py
# Purpose: Python-based initializer for programmatic DB setup (using SQLAlchemy and psycopg2).
# This script creates the database, schema, and tables using Python code.
# If you want to use SQL scripts for manual or automated setup, see the SQL files in the 'init' folder.

import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
from .config import engine, DATABASE_URL
from .models import Base
import re

# Define the schema name
SCHEMA_NAME = "carla_simulator"


def get_db_name_from_url(url):
    """Extract database name from DATABASE_URL"""
    match = re.search(r"/([^/?]+)(?:\?|$)", url)
    return match.group(1) if match else "carla_simulator"


def get_connection_url_without_db(url):
    """Get connection URL without database name"""
    return re.sub(r"/[^/?]+(?:\?|$)", "/postgres", url)


def create_database_if_not_exists():
    """Create database if it doesn't exist"""
    db_name = get_db_name_from_url(DATABASE_URL)
    conn_url = get_connection_url_without_db(DATABASE_URL)

    try:
        # Connect to PostgreSQL server
        conn = psycopg2.connect(conn_url)
        conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
        cursor = conn.cursor()

        # Check if database exists
        cursor.execute("SELECT 1 FROM pg_database WHERE datname = %s", (db_name,))
        exists = cursor.fetchone()

        if not exists:
            print(f"Creating database '{db_name}'...")
            cursor.execute(f"CREATE DATABASE {db_name}")
            print(f"Database '{db_name}' created successfully!")
        else:
            print(f"Database '{db_name}' already exists.")

    except Exception as e:
        print(f"Error creating database: {e}")
        raise
    finally:
        if "cursor" in locals():
            cursor.close()
        if "conn" in locals():
            conn.close()


def create_schema_if_not_exists():
    """Create schema if it doesn't exist"""
    try:
        # Connect to our database
        conn = psycopg2.connect(DATABASE_URL)
        conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
        cursor = conn.cursor()

        # Check if schema exists
        cursor.execute(
            "SELECT 1 FROM information_schema.schemata WHERE schema_name = %s",
            (SCHEMA_NAME,),
        )
        exists = cursor.fetchone()

        if not exists:
            print(f"Creating schema '{SCHEMA_NAME}'...")
            cursor.execute(f"CREATE SCHEMA {SCHEMA_NAME}")
            print(f"Schema '{SCHEMA_NAME}' created successfully!")
        else:
            print(f"Schema '{SCHEMA_NAME}' already exists.")

    except Exception as e:
        print(f"Error creating schema: {e}")
        raise
    finally:
        if "cursor" in locals():
            cursor.close()
        if "conn" in locals():
            conn.close()


def init_db():
    """Initialize the database by creating all tables"""
    try:
        # First create database if it doesn't exist
        create_database_if_not_exists()

        # Then create schema if it doesn't exist
        create_schema_if_not_exists()

        # Update the engine to use our schema
        engine.execute(f"SET search_path TO {SCHEMA_NAME}")

        # Then create all tables
        print("Creating database tables...")
        Base.metadata.create_all(bind=engine)
        print("Database tables created successfully!")

    except Exception as e:
        print(f"Error initializing database: {e}")
        raise


if __name__ == "__main__":
    init_db()
