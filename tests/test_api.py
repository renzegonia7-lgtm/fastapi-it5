"""Integration tests for employee CRUD, department relationships, and transfers."""

import os
from pathlib import Path
import tempfile

# Select an isolated test database before importing the app.
_TEST_DB = Path(tempfile.gettempdir()) / f"employee_api_test_{os.getpid()}.db"
if _TEST_DB.exists():
    _TEST_DB.unlink()
os.environ["EMPLOYEE_DB_PATH"] = str(_TEST_DB)

from fastapi.testclient import TestClient  # noqa: E402
from main import app  # noqa: E402



def setup_function():
    if _TEST_DB.exists():
        _TEST_DB.unlink()


def client_context():
    return TestClient(app)


def make_department(client: TestClient, name: str = "Information Technology") -> dict:
    response = client.post("/department", json={"name": name, "description": "Test department"})
    assert response.status_code == 201, response.text
    return response.json()


def make_employee(client: TestClient, department_id: int, name: str = "Alex Santos") -> dict:
    response = client.post(
        "/employee",
        json={
            "full_name": name,
            "position": "IT Support Specialist",
            "salary": 25000,
            "department_id": department_id,
            "employment_status": "Active",
        },
    )
    assert response.status_code == 201, response.text
    return response.json()


def test_home_and_empty_lists():
    with client_context() as client:
        assert client.get("/").status_code == 200
        assert client.get("/employees").json() == []
        assert client.get("/departments").json() == []


def test_department_and_employee_crud():
    with client_context() as client:
        department = make_department(client)
        employee = make_employee(client, department["id"])
        employee_id = employee["id"]

        assert employee["department_name"] == "Information Technology"
        assert client.get(f"/employees/{employee_id}").json()["full_name"] == "Alex Santos"
        assert len(client.get("/employees", params={"search": "Alex"}).json()) == 1

        updated = client.put(
            f"/employee/{employee_id}",
            json={
                "full_name": "Alex R. Santos", "position": "Senior IT Support",
                "salary": 30000, "department_id": department["id"],
                "employment_status": "Active",
            },
        )
        assert updated.status_code == 200
        assert updated.json()["salary"] == 30000

        assert client.delete(f"/employee/{employee_id}").status_code == 204
        assert client.delete(f"/department/{department['id']}").status_code == 204


def test_reject_invalid_salary_missing_department_and_duplicate_department():
    with client_context() as client:
        department = make_department(client)
        duplicate = client.post("/department", json={"name": "information technology"})
        assert duplicate.status_code == 409

        invalid_salary = client.post(
            "/employee",
            json={"full_name": "Taylor Cruz", "position": "Clerk", "salary": 0,
                  "department_id": department["id"]},
        )
        assert invalid_salary.status_code == 422

        missing_department = client.post(
            "/employee",
            json={"full_name": "Taylor Cruz", "position": "Clerk", "salary": 15000,
                  "department_id": 9999},
        )
        assert missing_department.status_code == 404


def test_department_transfer_is_recorded_and_updates_employee():
    with client_context() as client:
        hr = make_department(client, "Human Resources")
        finance = make_department(client, "Finance")
        employee = make_employee(client, hr["id"], "Jamie Rivera")

        response = client.post(
            f"/employees/{employee['id']}/transfer",
            json={"new_department_id": finance["id"], "reason": "Role reassignment"},
        )
        assert response.status_code == 201, response.text
        assert response.json()["old_department_name"] == "Human Resources"
        assert response.json()["new_department_name"] == "Finance"

        updated_employee = client.get(f"/employees/{employee['id']}").json()
        assert updated_employee["department_id"] == finance["id"]
        history = client.get(f"/employees/{employee['id']}/transfers").json()
        assert len(history) == 1
        assert history[0]["reason"] == "Role reassignment"

        report = client.get("/reports/summary").json()
        assert report["total_departments"] == 2
        assert report["total_employees"] == 1
        assert report["active_employees"] == 1


def test_transfer_to_same_department_and_delete_restrictions():
    with client_context() as client:
        first = make_department(client, "Operations")
        second = make_department(client, "Customer Service")
        employee = make_employee(client, first["id"], "Morgan Lee")

        same_department = client.post(
            f"/employees/{employee['id']}/transfer",
            json={"new_department_id": first["id"], "reason": "Attempted transfer"},
        )
        assert same_department.status_code == 409

        blocked_delete = client.delete(f"/department/{first['id']}")
        assert blocked_delete.status_code == 409

        transfer = client.post(
            f"/employees/{employee['id']}/transfer",
            json={"new_department_id": second["id"], "reason": "Team restructuring"},
        )
        assert transfer.status_code == 201
        assert client.delete(f"/employee/{employee['id']}").status_code == 409


def teardown_module():
    try:
        _TEST_DB.unlink(missing_ok=True)
        Path(str(_TEST_DB) + "-journal").unlink(missing_ok=True)
    except OSError:
        pass


def test_department_change_must_use_transfer_workflow():
    with client_context() as client:
        hr = make_department(client, "Human Resources")
        finance = make_department(client, "Finance")
        employee = make_employee(client, hr["id"], "Casey Dela Cruz")

        direct_change = client.put(
            f"/employee/{employee['id']}",
            json={
                "full_name": employee["full_name"],
                "position": employee["position"],
                "salary": employee["salary"],
                "department_id": finance["id"],
                "employment_status": employee["employment_status"],
            },
        )
        assert direct_change.status_code == 409
        assert "transfer" in direct_change.json()["detail"].lower()
        assert client.get(f"/employees/{employee['id']}").json()["department_id"] == hr["id"]
        assert client.get(f"/employees/{employee['id']}/transfers").json() == []


def test_failed_transfer_keeps_employee_in_original_department():
    import sqlite3

    with client_context() as client:
        hr = make_department(client, "Human Resources")
        finance = make_department(client, "Finance")
        employee = make_employee(client, hr["id"], "Jordan Reyes")

        # Force the transfer-history insert to fail after the employee update runs.
        # The database transaction should roll back both operations.
        with sqlite3.connect(_TEST_DB) as connection:
            connection.execute(
                """CREATE TRIGGER reject_transfer_insert
                   BEFORE INSERT ON department_transfers
                   BEGIN SELECT RAISE(ABORT, 'forced test failure'); END"""
            )

        response = client.post(
            f"/employees/{employee['id']}/transfer",
            json={"new_department_id": finance["id"], "reason": "Test transaction rollback"},
        )
        assert response.status_code == 409
        current_employee = client.get(f"/employees/{employee['id']}").json()
        assert current_employee["department_id"] == hr["id"]
        assert client.get(f"/employees/{employee['id']}/transfers").json() == []


def test_employee_filters_by_department_and_employment_status():
    with client_context() as client:
        it = make_department(client, "Information Technology")
        hr = make_department(client, "Human Resources")
        active = make_employee(client, it["id"], "Avery Santos")
        on_leave = client.post(
            "/employee",
            json={
                "full_name": "Bailey Cruz",
                "position": "HR Assistant",
                "salary": 22000,
                "department_id": hr["id"],
                "employment_status": "On Leave",
            },
        )
        assert on_leave.status_code == 201, on_leave.text

        assert [e["id"] for e in client.get("/employees", params={"department_id": it["id"]}).json()] == [active["id"]]
        assert [e["full_name"] for e in client.get("/employees", params={"employment_status": "On Leave"}).json()] == ["Bailey Cruz"]
        assert client.get("/employees", params={"search": "assistant"}).json()[0]["full_name"] == "Bailey Cruz"


def test_missing_records_return_404():
    with client_context() as client:
        payload = {"name": "Operations", "description": "Operations team"}
        employee_payload = {
            "full_name": "Taylor Cruz",
            "position": "Office Clerk",
            "salary": 18000,
            "department_id": 1,
            "employment_status": "Active",
        }
        assert client.get("/departments/999").status_code == 404
        assert client.put("/department/999", json=payload).status_code == 404
        assert client.delete("/department/999").status_code == 404
        assert client.get("/employees/999").status_code == 404
        assert client.put("/employee/999", json=employee_payload).status_code == 404
        assert client.delete("/employee/999").status_code == 404
        assert client.get("/employees/999/transfers").status_code == 404


def test_transfer_validation_and_unknown_target_department():
    with client_context() as client:
        department = make_department(client, "Customer Service")
        employee = make_employee(client, department["id"], "Robin Dela Cruz")

        too_short = client.post(
            f"/employees/{employee['id']}/transfer",
            json={"new_department_id": department["id"], "reason": "No"},
        )
        assert too_short.status_code == 422

        missing_target = client.post(
            f"/employees/{employee['id']}/transfer",
            json={"new_department_id": 9999, "reason": "Department reassignment"},
        )
        assert missing_target.status_code == 404
        assert client.get(f"/employees/{employee['id']}").json()["department_id"] == department["id"]
        assert client.get(f"/employees/{employee['id']}/transfers").json() == []
