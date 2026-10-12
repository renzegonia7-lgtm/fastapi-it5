"""Business rules and database operations, organized into service classes."""

import sqlite3
from collections.abc import Callable
from contextlib import AbstractContextManager
from typing import Any

from app.database import database_connection

ConnectionFactory = Callable[[], AbstractContextManager[sqlite3.Connection]]


class ResourceNotFound(Exception):
    """Raised when a requested record does not exist."""


class ConflictError(Exception):
    """Raised when an operation conflicts with a uniqueness or relationship rule."""


def _as_dict(row: sqlite3.Row | None) -> dict[str, Any] | None:
    return dict(row) if row is not None else None


class DepartmentService:
    """CRUD operations and rules for departments."""

    def __init__(self, connection_factory: ConnectionFactory = database_connection) -> None:
        self.connection_factory = connection_factory

    def list_departments(self) -> list[dict[str, Any]]:
        with self.connection_factory() as connection:
            rows = connection.execute(
                "SELECT id, name, description, created_at FROM departments ORDER BY name"
            ).fetchall()
        return [dict(row) for row in rows]

    def get_department(self, department_id: int) -> dict[str, Any]:
        with self.connection_factory() as connection:
            row = connection.execute(
                "SELECT id, name, description, created_at FROM departments WHERE id = ?",
                (department_id,),
            ).fetchone()
        result = _as_dict(row)
        if result is None:
            raise ResourceNotFound(f"Department {department_id} was not found.")
        return result

    def create_department(self, payload: dict[str, Any]) -> dict[str, Any]:
        try:
            with self.connection_factory() as connection:
                cursor = connection.execute(
                    "INSERT INTO departments (name, description) VALUES (?, ?)",
                    (payload["name"], payload.get("description", "")),
                )
                row = connection.execute(
                    "SELECT id, name, description, created_at FROM departments WHERE id = ?",
                    (cursor.lastrowid,),
                ).fetchone()
            return dict(row)
        except sqlite3.IntegrityError as exc:
            raise ConflictError("A department with that name already exists or the data is invalid.") from exc

    def update_department(self, department_id: int, payload: dict[str, Any]) -> dict[str, Any]:
        try:
            with self.connection_factory() as connection:
                cursor = connection.execute(
                    "UPDATE departments SET name = ?, description = ? WHERE id = ?",
                    (payload["name"], payload.get("description", ""), department_id),
                )
                if cursor.rowcount == 0:
                    raise ResourceNotFound(f"Department {department_id} was not found.")
                row = connection.execute(
                    "SELECT id, name, description, created_at FROM departments WHERE id = ?",
                    (department_id,),
                ).fetchone()
            return dict(row)
        except sqlite3.IntegrityError as exc:
            raise ConflictError("A department with that name already exists or the data is invalid.") from exc

    def delete_department(self, department_id: int) -> None:
        try:
            with self.connection_factory() as connection:
                cursor = connection.execute("DELETE FROM departments WHERE id = ?", (department_id,))
                if cursor.rowcount == 0:
                    raise ResourceNotFound(f"Department {department_id} was not found.")
        except sqlite3.IntegrityError as exc:
            raise ConflictError(
                "This department is referenced by an employee or transfer record. "
                "Move/delete the related records before deleting the department."
            ) from exc


class EmployeeService:
    """Employee CRUD plus the atomic department-transfer workflow."""

    EMPLOYEE_SELECT = """
        SELECT e.id, e.full_name, e.position, e.salary, e.department_id,
               e.employment_status, e.hire_date, e.created_at, e.updated_at,
               d.name AS department_name
        FROM employees e
        JOIN departments d ON d.id = e.department_id
    """

    def __init__(self, connection_factory: ConnectionFactory = database_connection) -> None:
        self.connection_factory = connection_factory

    def list_employees(
        self, search: str | None = None, department_id: int | None = None,
        employment_status: str | None = None,
    ) -> list[dict[str, Any]]:
        query = self.EMPLOYEE_SELECT
        clauses: list[str] = []
        params: list[Any] = []
        if search:
            clauses.append("(e.full_name LIKE ? OR e.position LIKE ?)")
            term = f"%{search.strip()}%"
            params.extend([term, term])
        if department_id is not None:
            clauses.append("e.department_id = ?")
            params.append(department_id)
        if employment_status:
            clauses.append("e.employment_status = ?")
            params.append(employment_status)
        if clauses:
            query += " WHERE " + " AND ".join(clauses)
        query += " ORDER BY e.full_name COLLATE NOCASE, e.id"
        with self.connection_factory() as connection:
            rows = connection.execute(query, params).fetchall()
        return [dict(row) for row in rows]

    def get_employee(self, employee_id: int) -> dict[str, Any]:
        with self.connection_factory() as connection:
            row = connection.execute(
                self.EMPLOYEE_SELECT + " WHERE e.id = ?", (employee_id,)
            ).fetchone()
        result = _as_dict(row)
        if result is None:
            raise ResourceNotFound(f"Employee {employee_id} was not found.")
        return result

    def create_employee(self, payload: dict[str, Any]) -> dict[str, Any]:
        try:
            with self.connection_factory() as connection:
                department = connection.execute(
                    "SELECT id FROM departments WHERE id = ?", (payload["department_id"],)
                ).fetchone()
                if department is None:
                    raise ResourceNotFound(
                        f"Department {payload['department_id']} was not found. Create the department first."
                    )
                cursor = connection.execute(
                    """INSERT INTO employees
                       (full_name, position, salary, department_id, employment_status)
                       VALUES (?, ?, ?, ?, ?)""",
                    (payload["full_name"], payload["position"], payload["salary"],
                     payload["department_id"], payload.get("employment_status", "Active")),
                )
                row = connection.execute(
                    self.EMPLOYEE_SELECT + " WHERE e.id = ?", (cursor.lastrowid,)
                ).fetchone()
            return dict(row)
        except sqlite3.IntegrityError as exc:
            raise ConflictError("The employee data violates a database constraint.") from exc

    def update_employee(self, employee_id: int, payload: dict[str, Any]) -> dict[str, Any]:
        try:
            with self.connection_factory() as connection:
                exists = connection.execute(
                    "SELECT id, department_id FROM employees WHERE id = ?", (employee_id,)
                ).fetchone()
                if exists is None:
                    raise ResourceNotFound(f"Employee {employee_id} was not found.")
                department = connection.execute(
                    "SELECT id FROM departments WHERE id = ?", (payload["department_id"],)
                ).fetchone()
                if department is None:
                    raise ResourceNotFound(
                        f"Department {payload['department_id']} was not found. Create the department first."
                    )
                if exists["department_id"] != payload["department_id"]:
                    raise ConflictError(
                        "Use POST /employees/{employee_id}/transfer to change departments so that "
                        "the transfer is recorded in the audit history."
                    )
                connection.execute(
                    """UPDATE employees
                       SET full_name = ?, position = ?, salary = ?,
                           employment_status = ?, updated_at = CURRENT_TIMESTAMP
                       WHERE id = ?""",
                    (payload["full_name"], payload["position"], payload["salary"],
                     payload.get("employment_status", "Active"), employee_id),
                )
                row = connection.execute(
                    self.EMPLOYEE_SELECT + " WHERE e.id = ?", (employee_id,)
                ).fetchone()
            return dict(row)
        except sqlite3.IntegrityError as exc:
            raise ConflictError("The employee data violates a database constraint.") from exc

    def delete_employee(self, employee_id: int) -> None:
        try:
            with self.connection_factory() as connection:
                cursor = connection.execute("DELETE FROM employees WHERE id = ?", (employee_id,))
                if cursor.rowcount == 0:
                    raise ResourceNotFound(f"Employee {employee_id} was not found.")
        except sqlite3.IntegrityError as exc:
            raise ConflictError(
                "This employee has department-transfer history and cannot be deleted. "
                "The history is retained for audit purposes."
            ) from exc

    def transfer_department(
        self, employee_id: int, new_department_id: int, reason: str
    ) -> dict[str, Any]:
        """Change the employee's department and create its audit record atomically."""
        try:
            # Both writes happen inside the same connection/transaction. If either
            # write fails, database_connection() rolls the whole transaction back.
            with self.connection_factory() as connection:
                employee = connection.execute(
                    "SELECT id, full_name, department_id FROM employees WHERE id = ?",
                    (employee_id,),
                ).fetchone()
                if employee is None:
                    raise ResourceNotFound(f"Employee {employee_id} was not found.")
                target = connection.execute(
                    "SELECT id FROM departments WHERE id = ?", (new_department_id,)
                ).fetchone()
                if target is None:
                    raise ResourceNotFound(f"Department {new_department_id} was not found.")
                old_department_id = employee["department_id"]
                if old_department_id == new_department_id:
                    raise ConflictError("The employee already belongs to that department.")

                connection.execute(
                    "UPDATE employees SET department_id = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
                    (new_department_id, employee_id),
                )
                cursor = connection.execute(
                    """INSERT INTO department_transfers
                       (employee_id, old_department_id, new_department_id, reason)
                       VALUES (?, ?, ?, ?)""",
                    (employee_id, old_department_id, new_department_id, reason),
                )
                transfer = connection.execute(
                    """SELECT t.id, t.employee_id, e.full_name AS employee_name,
                              t.old_department_id, old_d.name AS old_department_name,
                              t.new_department_id, new_d.name AS new_department_name,
                              t.reason, t.transfer_date
                       FROM department_transfers t
                       JOIN employees e ON e.id = t.employee_id
                       JOIN departments old_d ON old_d.id = t.old_department_id
                       JOIN departments new_d ON new_d.id = t.new_department_id
                       WHERE t.id = ?""",
                    (cursor.lastrowid,),
                ).fetchone()
            return dict(transfer)
        except sqlite3.IntegrityError as exc:
            raise ConflictError("The transfer could not be saved because it violates a database rule.") from exc

    def list_transfers(self, employee_id: int) -> list[dict[str, Any]]:
        # A missing employee should not be mistaken for an employee with no transfers.
        self.get_employee(employee_id)
        with self.connection_factory() as connection:
            rows = connection.execute(
                """SELECT t.id, t.employee_id, e.full_name AS employee_name,
                          t.old_department_id, old_d.name AS old_department_name,
                          t.new_department_id, new_d.name AS new_department_name,
                          t.reason, t.transfer_date
                   FROM department_transfers t
                   JOIN employees e ON e.id = t.employee_id
                   JOIN departments old_d ON old_d.id = t.old_department_id
                   JOIN departments new_d ON new_d.id = t.new_department_id
                   WHERE t.employee_id = ? ORDER BY t.transfer_date DESC, t.id DESC""",
                (employee_id,),
            ).fetchall()
        return [dict(row) for row in rows]

    def summary_report(self) -> dict[str, Any]:
        with self.connection_factory() as connection:
            totals = connection.execute(
                """SELECT
                       (SELECT COUNT(*) FROM departments) AS total_departments,
                       (SELECT COUNT(*) FROM employees) AS total_employees,
                       (SELECT COUNT(*) FROM employees WHERE employment_status = 'Active') AS active_employees"""
            ).fetchone()
            rows = connection.execute(
                """SELECT d.id AS department_id, d.name AS department_name,
                          COUNT(e.id) AS employee_count,
                          SUM(CASE WHEN e.employment_status = 'Active' THEN 1 ELSE 0 END)
                              AS active_employee_count,
                          AVG(e.salary) AS average_salary
                   FROM departments d
                   LEFT JOIN employees e ON e.department_id = d.id
                   GROUP BY d.id, d.name ORDER BY d.name"""
            ).fetchall()
        return {
            **dict(totals),
            "departments": [dict(row) for row in rows],
        }
