-- Create user (if not exists)
DO
$$
BEGIN
   IF NOT EXISTS (
      SELECT FROM pg_catalog.pg_roles WHERE rolname = 'carla_user'
   ) THEN
      CREATE ROLE carla_user LOGIN PASSWORD 'carla_password';
   END IF;
END
$$;

-- Create database (if not exists)
DO
$$
BEGIN
   IF NOT EXISTS (
      SELECT FROM pg_database WHERE datname = 'carla_simulator'
   ) THEN
      CREATE DATABASE carla_simulator OWNER carla_user;
   END IF;
END
$$; 
