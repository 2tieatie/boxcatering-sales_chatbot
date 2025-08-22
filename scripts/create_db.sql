-- Create database for Boxcatering Chatbot
-- Run this script as a PostgreSQL superuser (e.g., postgres)

-- Create database
CREATE DATABASE boxcatering_chatbot
    WITH 
    OWNER = postgres
    ENCODING = 'UTF8'
    LC_COLLATE = 'en_US.UTF-8'
    LC_CTYPE = 'en_US.UTF-8'
    TABLESPACE = pg_default
    CONNECTION LIMIT = -1;

-- Create user (optional - you can use existing postgres user)
-- CREATE USER boxcatering_user WITH PASSWORD 'your_password_here';
-- GRANT ALL PRIVILEGES ON DATABASE boxcatering_chatbot TO boxcatering_user;

-- Connect to the new database
\c boxcatering_chatbot;

-- Grant privileges (if you created a specific user)
-- GRANT ALL ON SCHEMA public TO boxcatering_user;

COMMENT ON DATABASE boxcatering_chatbot IS 'Database for Boxcatering Chatbot application';
