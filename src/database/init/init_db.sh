#!/bin/bash
set -e

# Variables
PGUSER=postgres
PGPASSWORD=postgres
DB=carla_simulator
SCHEMA=carla_simulator

echo "Starting database setup..."

# 1. Create user and database (run as superuser)
echo "Creating user and database..."
psql -U $PGUSER -f 01_create_user_and_db.sql

# 2. Create schema (run on the new DB)
echo "Creating schema..."
psql -U $PGUSER -d $DB -f 02_create_schema.sql

# 3. Create tables (run on the new DB)
echo "Creating tables..."
psql -U $PGUSER -d $DB -f 03_create_tables.sql

# 4. Create auth tables (run on the new DB)
echo "Creating auth tables..."
psql -U $PGUSER -d $DB -f 04_create_auth_tables.sql

echo "Database setup complete!"
echo "Database: $DB"
echo "Schema: $SCHEMA"
echo "User: $PGUSER" 