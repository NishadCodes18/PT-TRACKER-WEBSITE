"""
PostgreSQL Migration Script for License Keys Table
Run this on your Render PostgreSQL database to create the license_keys table.

Usage:
1. Go to Render Dashboard → Your PostgreSQL database
2. Click "Connect" → Get connection string
3. Run this SQL in your PostgreSQL client or Render's Shell

OR run via command line:
psql "postgresql://user:pass@host/db" < create_license_table.sql
"""

-- Create license_keys table
CREATE TABLE IF NOT EXISTS license_keys (
    id SERIAL PRIMARY KEY,
    license_key VARCHAR(100) UNIQUE NOT NULL,
    is_used BOOLEAN DEFAULT FALSE NOT NULL,
    used_by_trainer_id INTEGER,
    used_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
    notes VARCHAR(200),
    FOREIGN KEY (used_by_trainer_id) REFERENCES trainers(id) ON DELETE SET NULL
);

-- Create index for faster lookups
CREATE INDEX IF NOT EXISTS idx_license_keys_license_key ON license_keys(license_key);
CREATE INDEX IF NOT EXISTS idx_license_keys_is_used ON license_keys(is_used);

-- Verify table was created
SELECT
    'license_keys table created successfully!' as status,
    COUNT(*) as total_keys
FROM license_keys;
