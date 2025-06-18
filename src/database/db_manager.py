import psycopg2
from psycopg2.extras import RealDictCursor
from contextlib import contextmanager
import logging
from typing import Optional, Dict, Any, List
import time

from .config import DATABASE_URL, SCHEMA_NAME

logger = logging.getLogger(__name__)


class DatabaseManager:
    def __init__(self, max_retries: int = 3, retry_delay: float = 1.0):
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self._connection = None

    @contextmanager
    def get_connection(self):
        """Get a database connection with retry logic"""
        for attempt in range(self.max_retries):
            try:
                if not self._connection or self._connection.closed:
                    self._connection = psycopg2.connect(
                        DATABASE_URL, cursor_factory=RealDictCursor
                    )
                    # Set schema
                    with self._connection.cursor() as cur:
                        cur.execute(f"SET search_path TO {SCHEMA_NAME}")
                yield self._connection
                return
            except Exception as e:
                logger.error(f"Database connection attempt {attempt + 1} failed: {e}")
                if attempt < self.max_retries - 1:
                    time.sleep(self.retry_delay)
                else:
                    raise

    def execute_query(
        self, query: str, params: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """Execute a query with retry logic"""
        for attempt in range(self.max_retries):
            try:
                with self.get_connection() as conn:
                    with conn.cursor() as cur:
                        cur.execute(query, params or {})
                        if cur.description:  # If query returns results
                            return cur.fetchall()
                        return []
            except Exception as e:
                logger.error(f"Query execution attempt {attempt + 1} failed: {e}")
                if attempt < self.max_retries - 1:
                    time.sleep(self.retry_delay)
                else:
                    raise

    def execute_transaction(self, queries: List[tuple]) -> None:
        """Execute multiple queries in a transaction"""
        for attempt in range(self.max_retries):
            try:
                with self.get_connection() as conn:
                    with conn.cursor() as cur:
                        for query, params in queries:
                            cur.execute(query, params or {})
                        conn.commit()
                    return
            except Exception as e:
                logger.error(f"Transaction attempt {attempt + 1} failed: {e}")
                if attempt < self.max_retries - 1:
                    time.sleep(self.retry_delay)
                else:
                    raise

    def verify_connection(self) -> bool:
        """Verify database connection and schema"""
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cur:
                    # Check if schema exists
                    cur.execute(
                        "SELECT 1 FROM information_schema.schemata WHERE schema_name = %s",
                        (SCHEMA_NAME,),
                    )
                    if not cur.fetchone():
                        logger.error(f"Schema {SCHEMA_NAME} does not exist")
                        return False

                    # Check if required tables exist
                    required_tables = [
                        "scenarios",
                        "vehicle_data",
                        "sensor_data",
                        "simulation_metrics",
                    ]
                    for table in required_tables:
                        cur.execute(
                            """
                            SELECT 1 
                            FROM information_schema.tables 
                            WHERE table_schema = %s AND table_name = %s
                        """,
                            (SCHEMA_NAME, table),
                        )
                        if not cur.fetchone():
                            logger.error(f"Table {table} does not exist")
                            return False

            return True
        except Exception as e:
            logger.error(f"Database verification failed: {e}")
            return False

    def close(self):
        """Close the database connection"""
        if self._connection and not self._connection.closed:
            self._connection.close()
            self._connection = None
