-- Beginner Employee API: relational schema
-- This file documents the schema created automatically by app/database.py.
-- Enable FK enforcement for each SQLite connection.
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS departments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE COLLATE NOCASE
        CHECK (length(trim(name)) BETWEEN 2 AND 80),
    description TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS employees (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    full_name TEXT NOT NULL CHECK (length(trim(full_name)) BETWEEN 2 AND 100),
    position TEXT NOT NULL CHECK (length(trim(position)) BETWEEN 2 AND 80),
    salary REAL NOT NULL CHECK (salary > 0),
    department_id INTEGER NOT NULL,
    employment_status TEXT NOT NULL DEFAULT 'Active'
        CHECK (employment_status IN ('Active', 'On Leave', 'Terminated')),
    hire_date TEXT NOT NULL DEFAULT (date('now')),
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (department_id) REFERENCES departments(id) ON DELETE RESTRICT
);

CREATE TABLE IF NOT EXISTS department_transfers (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    employee_id INTEGER NOT NULL,
    old_department_id INTEGER NOT NULL,
    new_department_id INTEGER NOT NULL,
    reason TEXT NOT NULL CHECK (length(trim(reason)) BETWEEN 5 AND 300),
    transfer_date TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (employee_id) REFERENCES employees(id) ON DELETE RESTRICT,
    FOREIGN KEY (old_department_id) REFERENCES departments(id) ON DELETE RESTRICT,
    FOREIGN KEY (new_department_id) REFERENCES departments(id) ON DELETE RESTRICT,
    CHECK (old_department_id <> new_department_id)
);

CREATE INDEX IF NOT EXISTS idx_employees_department ON employees(department_id);
CREATE INDEX IF NOT EXISTS idx_employees_name ON employees(full_name);
CREATE INDEX IF NOT EXISTS idx_transfers_employee ON department_transfers(employee_id);
