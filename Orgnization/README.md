# Orgnization App (Organization & Permissions Module)

## Description
The Orgnization module manages corporate organizational structure, including departments, positions, and employee profiles. Additionally, this module enforces Role-Based Access Control (RBAC) and user authentication across the entire MES system.

## Models
* **Department**: Manages department code (unique), department name, and description.
* **Position**: Manages position code (unique), position title, and role description.
* **Employee**: Connected to Django `User` (OneToOne relationship), containing employee number (`emp_no`, unique and used as login identifier), name, department, position, and system role (`admin` / `manager` / `operator`).

## Key Features & Logic
* **Employee Number Authentication (EmployeeNoBackend)**:
  * System login **only accepts Employee Number (emp_no)** and does not use Django's default username login.
  * The authentication backend matches the employee number and verifies against the linked Django `User` password.
* **Role-Based Access Control (RBAC)**:
  * The module provides `RoleRequiredMixin` and `@role_required` decorators to enforce backend view-level authorization:
    * `admin`: Has full administrative permissions.
    * `manager`: Allowed to add and edit; deletion restricted in certain modules.
    * `operator`: Read-only view and browse permissions.
* **Automatic Image Cleanup**:
  * When an employee record is deleted (`post_delete`) or the photo is replaced (`pre_save`), previous photo files on disk are automatically deleted to prevent orphaned files.
* **create_employee Management Command**:
  * Provides `python manage.py create_employee` to quickly create an employee or bind an existing Django superuser to an employee account.

## Change Notice
* Optimized automatic cleanup mechanism for previous profile photos during employee image uploads.
