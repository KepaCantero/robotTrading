-- Database Initialization Script for AlgoTrading
-- TASK-2: Dockerización completa

-- Create database if it doesn't exist
CREATE DATABASE IF NOT EXISTS algotrading_dev;

-- Use the database
\c algotrading_dev;

-- Create extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";

-- Create schemas
CREATE SCHEMA IF NOT EXISTS trading;
CREATE SCHEMA IF NOT EXISTS analytics;
CREATE SCHEMA IF NOT EXISTS monitoring;

-- Set search path
SET search_path TO trading, analytics, monitoring, public;
