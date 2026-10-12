"""SQLite database setup and transaction-safe connection management."""

from collections.abc import Iterator
from contextlib import contextmanager
import os
from pathlib import Path
import sqlite3

# An environment variable makes it easy to run isolated tests or move the DB.
DATABASE_FILE = Path(
    os.getenv("EMPLOYEE_DB_PATH", str(Path(__file__).resolve().parent.parent / "employees.db"))
)


@contextmanager
def database_connection() -> Iterator[sqlite3.Connection]:
    """Yield a SQLite connection; commit on success and roll back on errors."""
    DATABASE_FILE.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(DATABASE_FILE, timeout=10)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    try:
        yield connection
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()


def initialize_database() -> None:
    """Create the relational tables and indexes if they do not already exist."""
    with database_connection() as connection:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS departments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE COLLATE NOCASE
                    CHECK (length(trim(name)) BETWEEN 2 AND 80),
                description TEXT NOT NULL DEFAULT '',
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        connection.execute(
            """
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
            )
            """
        )
        connection.execute(
            """
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
            )
            """
        )
        connection.execute(
            "CREATE INDEX IF NOT EXISTS idx_employees_department ON employees(department_id)"
        )
        connection.execute(
            "CREATE INDEX IF NOT EXISTS idx_employees_name ON employees(full_name)"
        )
        connection.execute(
            "CREATE INDEX IF NOT EXISTS idx_transfers_employee ON department_transfers(employee_id)"
        )
