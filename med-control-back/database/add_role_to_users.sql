-- Migration: add role column to users table for RBAC
-- Run once: psql $DATABASE_URL -f database/add_role_to_users.sql

ALTER TABLE users
  ADD COLUMN IF NOT EXISTS role VARCHAR(20) NOT NULL DEFAULT 'USER';

UPDATE users SET role = 'USER' WHERE role IS NULL;

CREATE INDEX IF NOT EXISTS idx_users_role ON users(role);

COMMENT ON COLUMN users.role IS 'RBAC role: USER (full access) | CAREGIVER (read-only)';
