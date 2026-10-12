"""Pydantic request/response models used by FastAPI for validation."""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

EmploymentStatus = Literal["Active", "On Leave", "Terminated"]


class APIModel(BaseModel):
    """Shared configuration for clean, validated string inputs."""

    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")


class DepartmentInput(APIModel):
    name: str = Field(min_length=2, max_length=80, description="Unique department name")
    description: str = Field(default="", max_length=300)

    @field_validator("name")
    @classmethod
    def department_name_not_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("Department name cannot be blank.")
        return value


class Department(DepartmentInput):
    id: int
    created_at: str


class EmployeeInput(APIModel):
    full_name: str = Field(min_length=2, max_length=100, description="Employee's full name")
    position: str = Field(min_length=2, max_length=80)
    salary: float = Field(gt=0, le=100_000_000, description="Monthly salary; must be positive")
    department_id: int = Field(gt=0, description="ID of an existing department")
    employment_status: EmploymentStatus = "Active"

    @field_validator("full_name", "position")
    @classmethod
    def text_not_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("This field cannot be blank.")
        return value


class Employee(EmployeeInput):
    id: int
    hire_date: str
    created_at: str
    updated_at: str
    department_name: str | None = None


class TransferInput(APIModel):
    new_department_id: int = Field(gt=0, description="Target department ID")
    reason: str = Field(min_length=5, max_length=300)

    @field_validator("reason")
    @classmethod
    def reason_not_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("Transfer reason cannot be blank.")
        return value


class DepartmentTransfer(BaseModel):
    id: int
    employee_id: int
    employee_name: str
    old_department_id: int
    old_department_name: str
    new_department_id: int
    new_department_name: str
    reason: str
    transfer_date: str


class DepartmentSummary(BaseModel):
    department_id: int
    department_name: str
    employee_count: int
    active_employee_count: int
    average_salary: float | None


class SummaryReport(BaseModel):
    total_departments: int
    total_employees: int
    active_employees: int
    departments: list[DepartmentSummary]
