#!/bin/bash
set -e

# Variables
PGUSER=postgres
PGPASSWORD=postgres
DB=carla_simulator

# 1. Create user and database (run as superuser)
psql -U $PGUSER -f 01_create_user_and_db.sql

# 2. Create schema (run on the new DB)
psql -U $PGUSER -d $DB -f 02_create_schema.sql

# 3. Create tables (run on the new DB)
psql -U $PGUSER -d $DB -f 03_create_tables.sql

echo "Database setup complete!" 