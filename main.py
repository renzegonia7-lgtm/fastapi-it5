"""Beginner Employee Management API built with FastAPI and SQLite."""

from contextlib import asynccontextmanager

from fastapi import FastAPI, Query
from fastapi.responses import JSONResponse

from app.database import initialize_database, database_connection
from app.models import (
    Department,
    DepartmentInput,
    DepartmentSummary,
    DepartmentTransfer,
    Employee,
    EmployeeInput,
    EmploymentStatus,
    SummaryReport,
    TransferInput,
)
from app.services import ConflictError, DepartmentService, EmployeeService, ResourceNotFound


department_service = DepartmentService(database_connection)
employee_service = EmployeeService(database_connection)


@asynccontextmanager
async def lifespan(_app: FastAPI):
    """Create database tables before serving requests."""
    initialize_database()
    yield


app = FastAPI(
    title="Beginner Employee API",
    version="1.0.0",
    description=(
        "An Employee Management API for maintaining departments and employee records, "
        "transferring employees between departments, and viewing a basic staffing report. "
        "Use the endpoints below to test the database workflow."
    ),
    lifespan=lifespan,
)


@app.exception_handler(ResourceNotFound)
async def not_found_handler(_request, exc: ResourceNotFound):
    return JSONResponse(status_code=404, content={"detail": str(exc)})


@app.exception_handler(ConflictError)
async def conflict_handler(_request, exc: ConflictError):
    return JSONResponse(status_code=409, content={"detail": str(exc)})


@app.get("/", tags=["default"])
def home():
    """Show the API welcome message."""
    return {
        "message": "Welcome to the Beginner Employee API.",
        "documentation": "/docs",
        "main_features": ["employee CRUD", "department CRUD", "department transfers", "staffing report"],
    }


# Department endpoints -------------------------------------------------------
@app.get("/departments", response_model=list[Department], tags=["departments"])
def get_departments():
    """List all departments."""
    return department_service.list_departments()


@app.get("/departments/{department_id}", response_model=Department, tags=["departments"])
def get_department(department_id: int):
    """Get one department by its ID."""
    return department_service.get_department(department_id)


@app.post("/department", response_model=Department, status_code=201, tags=["departments"])
def create_department(department: DepartmentInput):
    """Create a department. Names must be unique."""
    return department_service.create_department(department.model_dump())


@app.put("/department/{department_id}", response_model=Department, tags=["departments"])
def edit_department(department_id: int, department: DepartmentInput):
    """Replace the editable fields of an existing department."""
    return department_service.update_department(department_id, department.model_dump())


@app.delete("/department/{department_id}", status_code=204, tags=["departments"])
def delete_department(department_id: int):
    """Delete a department only when no employee or transfer refers to it."""
    department_service.delete_department(department_id)
    return None


# Employee endpoints. The singular POST/PUT/DELETE paths preserve the starter
# API's naming convention shown in the original Swagger screenshot.
@app.get("/employees", response_model=list[Employee], tags=["employees"])
def get_employees(
    search: str | None = Query(default=None, max_length=100, description="Search name or position"),
    department_id: int | None = Query(default=None, gt=0),
    employment_status: EmploymentStatus | None = Query(default=None),
):
    """List employees, optionally filtered by name/position, department, or status."""
    return employee_service.list_employees(search, department_id, employment_status)


@app.get("/employees/{employee_id}", response_model=Employee, tags=["employees"])
def get_employee(employee_id: int):
    """Get a single employee."""
    return employee_service.get_employee(employee_id)


@app.post("/employee", response_model=Employee, status_code=201, tags=["employees"])
def create_employee(employee: EmployeeInput):
    """Create an employee assigned to an existing department."""
    return employee_service.create_employee(employee.model_dump())


@app.put("/employee/{employee_id}", response_model=Employee, tags=["employees"])
def edit_employee(employee_id: int, employee: EmployeeInput):
    """Update employee details. Use the transfer workflow to change departments."""
    return employee_service.update_employee(employee_id, employee.model_dump())


@app.delete("/employee/{employee_id}", status_code=204, tags=["employees"])
def delete_employee(employee_id: int):
    """Delete an employee if no transfer history depends on the record."""
    employee_service.delete_employee(employee_id)
    return None


# Transactional workflow and reporting --------------------------------------
@app.post(
    "/employees/{employee_id}/transfer",
    response_model=DepartmentTransfer,
    status_code=201,
    tags=["workflows"],
)
def transfer_employee(employee_id: int, transfer: TransferInput):
    """Transfer an employee and save an audit record in one database transaction."""
    return employee_service.transfer_department(
        employee_id=employee_id,
        new_department_id=transfer.new_department_id,
        reason=transfer.reason,
    )


@app.get(
    "/employees/{employee_id}/transfers",
    response_model=list[DepartmentTransfer],
    tags=["workflows"],
)
def get_employee_transfers(employee_id: int):
    """List an employee's department-transfer history."""
    return employee_service.list_transfers(employee_id)


@app.get("/reports/summary", response_model=SummaryReport, tags=["reports"])
def get_summary_report():
    """Return employee totals and per-department headcount and average salary."""
    return employee_service.summary_report()
