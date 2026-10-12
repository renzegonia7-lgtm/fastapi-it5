# Beginner Employee API

A beginner-friendly Employee and Department Management API built with **Python, FastAPI, SQLite, Pydantic v2, and object-oriented service classes**. It extends the class boilerplate at <https://github.com/kayljiyan-addu/fastapi-it5> while keeping the recognizable `main.py` and `app/` module organization.

## Problem being addressed

Small offices may keep employee lists, department assignments, and staff transfers in separate spreadsheets or paper forms. This can result in outdated department assignments, duplicate department names, and no reliable transfer history. The API centralizes employee records, enforces foreign-key relationships, and records each department transfer.

## Features

- Full CRUD operations for departments and employee records.
- Three related SQLite tables: `departments`, `employees`, and `department_transfers`.
- Foreign-key and field constraints; department names are unique without case sensitivity.
- Employee search by name/position and filters by department and employment status.
- Transactional employee-transfer workflow: update the employee and insert an audit-history row in one transaction.
- Transfer-history protection: normal employee updates cannot silently change departments; use the transfer endpoint to record the reason and history.
- Summary report with total departments, total employees, active employees, headcount by department, and average salary.
- Consistent error responses for missing records, invalid data, and conflicting operations.
- Swagger UI at `http://127.0.0.1:8000/docs`.

## Project structure

```text
Employee_API_Final/
├── main.py                       # FastAPI endpoints and application setup
├── app/
│   ├── __init__.py
│   ├── database.py               # SQLite setup, schema, FK enforcement, transactions
│   ├── models.py                 # Pydantic request and response models
│   └── services.py                # OOP service classes and business rules
├── docs/
│   ├── er_diagram.png
│   ├── transfer_workflow.png
│   ├── schema.sql
│   ├── Employee_API_Project_Documentation.pdf
│   └── make_diagrams.py
├── tests/
│   └── test_api.py               # Integration tests
├── requirements.txt
├── pytest.ini
└── README.md
```

## Run on Windows (PowerShell)

Run these commands from inside the extracted `Employee_API_Final` folder:

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python -m uvicorn main:app --reload
```

If PowerShell blocks virtual-environment activation, run this in the same terminal and try activation again:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\.venv\Scripts\Activate.ps1
```

## Run on macOS/Linux

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python -m uvicorn main:app --reload
```

SQLite creates `employees.db` automatically when the app starts. A separate database server is not needed. Open `http://127.0.0.1:8000/docs` in your browser.

## Recommended first demo in Swagger UI

1. Use **POST `/department`** to create a department:

   ```json
   {
     "name": "Information Technology",
     "description": "IT support and infrastructure"
   }
   ```

2. Create a second department using **POST `/department`**, for example `Human Resources`.
3. Use **GET `/departments`** and note the IDs returned by the database.
4. Use **POST `/employee`** with an existing department ID:

   ```json
   {
     "full_name": "Alex Santos",
     "position": "IT Support Specialist",
     "salary": 25000,
     "department_id": 1,
     "employment_status": "Active"
   }
   ```

5. Use **GET `/employees`** to verify the record and its `department_name`.
6. Use **POST `/employees/{employee_id}/transfer`** with the employee ID and a different department ID:

   ```json
   {
     "new_department_id": 2,
     "reason": "Role reassignment"
   }
   ```

7. Verify the result using **GET `/employees/{employee_id}`**, check the audit entry using **GET `/employees/{employee_id}/transfers`**, and view the report at **GET `/reports/summary`**.

The IDs above are examples. Substitute the IDs returned by your running API.

## API endpoint list

### Departments

| Method | Path | Purpose |
|---|---|---|
| GET | `/departments` | List departments |
| GET | `/departments/{department_id}` | Retrieve one department |
| POST | `/department` | Create a department |
| PUT | `/department/{department_id}` | Update a department |
| DELETE | `/department/{department_id}` | Delete only if no employee or transfer refers to it |

### Employees

| Method | Path | Purpose |
|---|---|---|
| GET | `/employees` | List employees; optional `search`, `department_id`, `employment_status` filters |
| GET | `/employees/{employee_id}` | Retrieve one employee |
| POST | `/employee` | Hire/create an employee in an existing department |
| PUT | `/employee/{employee_id}` | Update details without changing departments |
| DELETE | `/employee/{employee_id}` | Delete only if the employee has no transfer history |

### Workflow and report

| Method | Path | Purpose |
|---|---|---|
| POST | `/employees/{employee_id}/transfer` | Change departments and record the reason atomically |
| GET | `/employees/{employee_id}/transfers` | View department-transfer history |
| GET | `/reports/summary` | Staffing totals, department headcount, active count, average salary |
| GET | `/` | Welcome message and documentation location |

## Database design

- `departments`: unique department name and optional description.
- `employees`: employee details and a foreign key to `departments.id`.
- `department_transfers`: audit history with foreign keys to an employee and both the old and new departments.

The relationship between departments and employees is one-to-many. A transfer record references exactly one employee, one previous department, and one destination department. The transfer table is append-only through the API so historical audit records cannot be accidentally changed or deleted. Department and employee deletion are restricted when they would break these relationships.

See `docs/er_diagram.png` for the ER diagram and `docs/schema.sql` for the SQL schema documented separately from the code that initializes it.

## Object-oriented design

- `APIModel`, `DepartmentInput`, `EmployeeInput`, and `TransferInput` organize input validation.
- `DepartmentService` contains department CRUD and integrity rules.
- `EmployeeService` contains employee CRUD, searching/filtering, transfer workflow, transfer-history retrieval, and reporting.
- `main.py` defines HTTP routes and calls service objects. This keeps endpoint handling separate from business/database rules.

## Tests

Run the automated integration suite from the project root:

```powershell
python -m pytest -q
```

The included suite covers application startup, department and employee CRUD, query filters, invalid data, missing records, duplicate names, transfer history, relationship restrictions, and rollback after a forced transfer-history write failure. The suite uses an isolated temporary SQLite database so normal `employees.db` data is not modified.

## Publish to your GitHub account

The starter repository is the foundation; submit your own completed repository instead of replacing the instructor's project. Create a new empty repository under your GitHub account, then run the following commands from this folder (replace the URL with your repository's actual URL):

```bash
git init
git add .
git commit -m "Complete Employee Management API"
git branch -M main
git remote add origin https://github.com/YOUR-USERNAME/Employee-API-Final.git
git push -u origin main
```

After the push succeeds, copy the actual repository URL into the submission. `http://127.0.0.1:8000/docs` is a local development URL and is not a public GitHub link.

## Limitations

This is an academic local prototype. It has no user login or permission roles and is not configured for production deployment, automated backups, or confidential HR data. Use sample employee data for class demonstrations and do not commit a real database file or private employee information to a public repository.
