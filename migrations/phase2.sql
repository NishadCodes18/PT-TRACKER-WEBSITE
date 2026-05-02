-- Phase 2: Business Logic & Expense Tracking Migration
-- Run this to update existing database

-- 1. Add shift_type to trainers table
ALTER TABLE trainers ADD COLUMN shift_type TEXT DEFAULT '8-hour' CHECK (shift_type IN ('8-hour', '4-hour'));

-- 2. Add pt_tier and contact_number to clients table
ALTER TABLE clients ADD COLUMN pt_tier TEXT DEFAULT 'Silver' CHECK (pt_tier IN ('Silver', 'Gold', 'Platinum'));
ALTER TABLE clients ADD COLUMN contact_number TEXT;

-- 3. Add expected_amount to payments (for tier-based pricing)
ALTER TABLE payments ADD COLUMN expected_amount DECIMAL(10, 2);

-- 4. Create Expenses table (if not exists from original schema)
CREATE TABLE IF NOT EXISTS expenses (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    trainer_id INTEGER NOT NULL,
    expense_name TEXT NOT NULL,
    amount DECIMAL(10, 2) NOT NULL,
    expense_date DATE NOT NULL,
    category TEXT DEFAULT 'other',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (trainer_id) REFERENCES trainers(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_expenses_trainer ON expenses(trainer_id);
CREATE INDEX IF NOT EXISTS idx_expenses_date ON expenses(expense_date);
