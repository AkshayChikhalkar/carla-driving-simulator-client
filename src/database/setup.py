import os
import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
import sys

# Database configuration
DB_USER = 'postgres'
DB_PASSWORD = 'postgres'
DB_HOST = 'localhost'
DB_PORT = '5432'
DB_NAME = 'carla_simulator'
SCHEMA_NAME = 'carla_simulator'

# Path to SQL files
INIT_DIR = os.path.join(os.path.dirname(__file__), 'init')
SQL_FILES = [
    '01_create_user_and_db.sql',
    '02_create_schema.sql',
    '03_create_tables.sql'
]

def execute_sql_file(conn, sql_file, db_name='postgres'):
    """Execute a SQL file"""
    print(f"Executing {sql_file}...")
    try:
        with open(os.path.join(INIT_DIR, sql_file), 'r') as f:
            sql = f.read()
            with conn.cursor() as cur:
                cur.execute(sql)
        print(f"Completed {sql_file}")
    except Exception as e:
        print(f"Error executing {sql_file}: {e}")
        raise

def setup_database():
    """Set up the database using SQL files"""
    try:
        # Connect to PostgreSQL server as superuser
        conn = psycopg2.connect(
            dbname='postgres',
            user=DB_USER,
            password=DB_PASSWORD,
            host=DB_HOST,
            port=DB_PORT
        )
        conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)

        # Execute first SQL file (create user and database)
        execute_sql_file(conn, SQL_FILES[0])

        # Close connection to postgres database
        conn.close()

        # Connect to our database
        conn = psycopg2.connect(
            dbname=DB_NAME,
            user=DB_USER,
            password=DB_PASSWORD,
            host=DB_HOST,
            port=DB_PORT
        )
        conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)

        # Execute remaining SQL files
        for sql_file in SQL_FILES[1:]:
            execute_sql_file(conn, sql_file, DB_NAME)

        print("\nDatabase setup completed successfully!")
        print(f"Database: {DB_NAME}")
        print(f"Schema: {SCHEMA_NAME}")
        print(f"User: {DB_USER}")
        print(f"Host: {DB_HOST}")
        print(f"Port: {DB_PORT}")

    except Exception as e:
        print(f"Error during database setup: {e}")
        sys.exit(1)
    finally:
        if 'conn' in locals():
            conn.close()

if __name__ == "__main__":
    setup_database() 