import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
import os
import sys
import subprocess
import platform
from .config import DATABASE_URL, SCHEMA_NAME
from .models import Base
from sqlalchemy import create_engine
import re

# Database configuration
DB_NAME = 'carla_simulator'
DB_USER = 'postgres'
DB_PASSWORD = 'postgres'
DB_HOST = 'localhost'
DB_PORT = '5432'

def check_postgres_installation():
    """Check if PostgreSQL is installed and running"""
    try:
        # Try to connect to PostgreSQL server
        conn = psycopg2.connect(
            dbname='postgres',
            user=DB_USER,
            password=DB_PASSWORD,
            host=DB_HOST,
            port=DB_PORT
        )
        conn.close()
        print("PostgreSQL server is running.")
        return True
    except psycopg2.OperationalError as e:
        print("Error: PostgreSQL server is not running or not properly configured.")
        print("Please ensure PostgreSQL is installed and running.")
        print(f"Error details: {e}")
        return False
    except Exception as e:
        print(f"Unexpected error: {e}")
        return False

def create_user_if_not_exists():
    """Create database user if it doesn't exist"""
    try:
        # Connect to PostgreSQL server
        conn = psycopg2.connect(
            dbname='postgres',
            user=DB_USER,
            password=DB_PASSWORD,
            host=DB_HOST,
            port=DB_PORT
        )
        conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
        cursor = conn.cursor()

        # Check if user exists
        cursor.execute("SELECT 1 FROM pg_roles WHERE rolname = %s", (DB_USER,))
        if not cursor.fetchone():
            print(f"Creating user '{DB_USER}'...")
            cursor.execute(f"CREATE USER {DB_USER} WITH PASSWORD '{DB_PASSWORD}'")
            cursor.execute(f"ALTER USER {DB_USER} WITH SUPERUSER")
            print(f"User '{DB_USER}' created successfully!")
        else:
            print(f"User '{DB_USER}' already exists.")

    except Exception as e:
        print(f"Error creating user: {e}")
        raise
    finally:
        if 'cursor' in locals():
            cursor.close()
        if 'conn' in locals():
            conn.close()

def create_database_if_not_exists():
    """Create database if it doesn't exist"""
    try:
        # Connect to PostgreSQL server
        conn = psycopg2.connect(
            dbname='postgres',
            user=DB_USER,
            password=DB_PASSWORD,
            host=DB_HOST,
            port=DB_PORT
        )
        conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
        cursor = conn.cursor()

        # Check if database exists
        cursor.execute("SELECT 1 FROM pg_database WHERE datname = %s", (DB_NAME,))
        if not cursor.fetchone():
            print(f"Creating database '{DB_NAME}'...")
            cursor.execute(f'CREATE DATABASE {DB_NAME}')
            print(f"Database '{DB_NAME}' created successfully!")
        else:
            print(f"Database '{DB_NAME}' already exists.")

    except Exception as e:
        print(f"Error creating database: {e}")
        raise
    finally:
        if 'cursor' in locals():
            cursor.close()
        if 'conn' in locals():
            conn.close()

def create_schema_if_not_exists():
    """Create schema if it doesn't exist"""
    try:
        # Connect to our database
        conn = psycopg2.connect(
            dbname=DB_NAME,
            user=DB_USER,
            password=DB_PASSWORD,
            host=DB_HOST,
            port=DB_PORT
        )
        conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
        cursor = conn.cursor()

        # Check if schema exists
        cursor.execute("SELECT 1 FROM information_schema.schemata WHERE schema_name = %s", (SCHEMA_NAME,))
        if not cursor.fetchone():
            print(f"Creating schema '{SCHEMA_NAME}'...")
            cursor.execute(f'CREATE SCHEMA {SCHEMA_NAME}')
            print(f"Schema '{SCHEMA_NAME}' created successfully!")
        else:
            print(f"Schema '{SCHEMA_NAME}' already exists.")

    except Exception as e:
        print(f"Error creating schema: {e}")
        raise
    finally:
        if 'cursor' in locals():
            cursor.close()
        if 'conn' in locals():
            conn.close()

def setup_database():
    """Main function to set up the database"""
    try:
        # Check PostgreSQL installation
        if not check_postgres_installation():
            sys.exit(1)

        # Create user if not exists
        create_user_if_not_exists()

        # Create database if not exists
        create_database_if_not_exists()

        # Create schema if not exists
        create_schema_if_not_exists()

        # Create tables
        print("Creating database tables...")
        engine = create_engine(DATABASE_URL)
        Base.metadata.create_all(bind=engine)
        print("Database tables created successfully!")

        print("\nDatabase setup completed successfully!")
        print(f"Database: {DB_NAME}")
        print(f"Schema: {SCHEMA_NAME}")
        print(f"User: {DB_USER}")
        print(f"Host: {DB_HOST}")
        print(f"Port: {DB_PORT}")

    except Exception as e:
        print(f"Error during database setup: {e}")
        sys.exit(1)

if __name__ == "__main__":
    setup_database() 