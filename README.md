# Antigravity_MES

A Django-based Manufacturing Execution System (MES) featuring 9 core modules: Organization, Equipment, Material, Product, Supplier, Customer, Production, Documents, and File Library. Includes role-based access control (admin / manager / operator), SQLite database, CI testing, and uWSGI/Nginx deployment configurations.

## Quick Start

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python manage.py makemigrations Customer Dashboard Documents Equipment FileLibrary Material Orgnization Product Production Supplier 
python manage.py migrate
python manage.py runserver 127.0.0.1:9090
```

- Dashboard Home: http://127.0.0.1:9090/
- Admin: http://127.0.0.1:9090/admin/

## Login Account (Important)

System login **only accepts Employee Number (`emp_no`)**; username login is not supported.
Accounts created via `createsuperuser` do not have an associated employee profile and will fail to log in directly. They must first be bound:

```bash
# 1. Create superuser
python manage.py createsuperuser

# 2. Bind superuser to an employee profile (automatically creates department/position)
python manage.py create_employee --username <your_superuser_account> --emp-no EMP-001 --role admin
```

Subsequent logins:
- **Account**: `EMP-001` (Employee Number)
- **Password**: Superuser password

### `create_employee` Parameters

| Parameter | Default | Description |
|---|---|---|
| `--username` | Required | Account created via `createsuperuser` |
| `--emp-no` | `EMP-001` | Employee number used for login (must be unique) |
| `--role` | `admin` | `admin` / `manager` / `operator` |
| `--name` | username | Employee name |
| `--dept` / `--dept-name` | `D001` / `Management` | Department code/name (auto-created if non-existent) |
| `--position` / `--position-name` | `P001` / `Managerial` | Position code/name (auto-created if non-existent) |

> Role Permissions: `admin` has full permissions; `manager` can create/edit; `operator` is read-only. Button visibility is controlled at the template level via `is_manager` / `is_admin` context variables, with backend views doubly guarded using `RoleRequiredMixin` / `@role_required`.

## Tech Stack

| Tool | Version / Notes |
|---|---|
| Python / Django | 3.12 / 5.2 |
| Database | SQLite (development), can be migrated to PostgreSQL |
| CSS / Forms | Bootstrap 5 (Linear Light Design) + django-crispy-forms + crispy-bootstrap5 |
| Image / Video | Pillow 12.2.0 / ffmpeg (H.264 transcoding) |
| QR Code | qrcode 8.2 (Pillow generates PNG) |
| WSGI | uWSGI (see `uwsgi.ini`) |
| Proxy | Nginx (see `Nginx.md`) |
| CI | GitHub Actions (`.github/workflows/django.yml`) |

## App Architecture

```
miniMES/
├── settings.py / urls.py / wsgi.py
│
├── Dashboard/            # Home + Dashboard
├── Orgnization/          # Organization: Departments / Positions / Employees (with RBAC)
├── Equipment/            # Equipment: Categories / Equipment / Maintenance Records
├── Material/             # Material: Categories / Materials / Stock Transactions
├── Product/              # Product: Categories / Products
├── Supplier/             # Supplier: Categories / Suppliers
├── Customer/             # Customer: Customer profiles (Code, Contact, Tax ID, etc.)
├── Production/           # Production: Work Orders (with Process Routing) / BOM
├── Documents/            # Documents: Categories / Documents / Multi-image / Audit Logs (Approval Workflow)
├── FileLibrary/          # File Library: Categories / Files (Chunked Upload / Video Transcoding)
│
├── templates/            # Site-wide base templates
│   └── registration/
│       └── login.html    # Django auth login page
│
└── statics/              # Static assets (CSS / JS)
```

## Module Design Overview

### 1. Dashboard
- `LandingPageView` (public home page before login), `DashboardView` (dashboard after login)
- **Switchable Dashboard Templates**: Classic (Linear Light) and Industrial (Data-Dense, `ui-ux-pro-max` design system: Blue `#1E40AF` / Amber `#F59E0B`, KPI cards, data tables, Fira Code font falling back to Inter) — Switchable via top-right button, preferences saved in session; can also be selected via query string `?template=classic|industrial`.

### 2. Orgnization (Organization Management)
| Model | Responsibility |
|---|---|
| `Department` | Department code (unique), name, description |
| `Position` | Position code (unique), name, description |
| `Employee` | Employee number `emp_no` (unique), name, department FK, position FK, role (admin/manager/operator), photo, etc. |

- Login links to `Employee.user` (OneToOne) using custom `EmployeeNoBackend` authentication backend.
- Photo uploads automatically clean up old files via `post_delete` / `pre_save` signals.
- `create_employee` management command: Quickly binds a superuser to an employee profile.

### 3. Equipment (Equipment Management)
| Model | Responsibility |
|---|---|
| `EquipmentCategory` | Equipment category (unique), description |
| `Equipment` | Equipment code (unique), name, category FK, status (active/maintenance/broken/retired) |
| `MaintenanceRecord` | Maintenance and service logs |

### 4. Material (Material Management)
| Model | Responsibility |
|---|---|
| `MaterialCategory` | Material category (unique), description |
| `Material` | Material code (unique), name, category FK, unit, current stock, safety stock, supplier, location |
| `StockTransaction` | Inventory transactions (INBOUND/OUTBOUND/ADJUST), tracks `balance_after` |

- `is_low_stock`: Low stock warning when `stock_quantity <= min_stock`.

### 5. Product (Product Management)
| Model | Responsibility |
|---|---|
| `ProductCategory` | Product category |
| `Product` | Product code (unique), name, category FK, specifications |

### 6. Supplier (Supplier Management)
| Model | Responsibility |
|---|---|
| `SupplierCategory` | Supplier category |
| `Supplier` | Supplier code (unique), name, category FK, contact info |

### 7. Customer (Customer Management)
| Model | Responsibility |
|---|---|
| `Customer` | Customer code (unique), name, contact person, phone, email, address, tax ID, active status |

- Customer ID format validation (alphanumeric/underscores/hyphens) and real-time uniqueness checking (`check_customer_id` AJAX endpoint).

### 8. Production (Production Management)
| Model | Responsibility |
|---|---|
| `WorkOrder` | Work order number (unique), product FK, target quantity, status, planned/actual start and end times |
| `BOM` / `BOMItem` | Finished product BOM composition and usage quantity (`unique_together = (bom, component)`) |
| `ProcessStep` | Process routing definitions (step name, sequence, responsible position) |
| `WorkOrderStep` | Work order routing step instances (status derived automatically; includes Track In / Track Out tracking: operator, equipment, timestamps, remarks; `is_picking_step` flags the material picking step) |
| `MaterialPickingItem` | Material picking checklist (required quantity per BOM, confirmed quantity/operator/timestamp, remarks) |

- Work order statuses: `PENDING` / `IN_PROGRESS` / `COMPLETED` / `CANCELLED` / `ABNORMAL`.
- **Material Picking Station (Step 0)**: When a work order is created and the product has an active BOM, a "Material Picking" step (step 0) is automatically created along with a **material checklist** (BOM usage × work order quantity). Operators check required vs. current stock, submit confirmed quantities and remarks. **Upon confirmation, stock is immediately deducted** (OUTBOUND transaction with duplicate deduction prevention) before the picking station completes. **Operators cannot track into the next station until confirmed** (strict serial enforcement). No duplicate stock deduction occurs upon final order completion.
- **Track In / Track Out**: Steps execute via Track In / Track Out workflows:
  - **Track In**: Operators enter **inbound quantity and remarks/status** (validates strict serial order, employee position, equipment status, and BOM readiness; records operator, actual equipment, and timestamp).
  - **Track Out**: Enforces reporting of good, defective, and lost quantities (which must balance) along with **outbound remarks/status**, recording outbound operator and timestamp.
  - The routing card displays quantity transitions and station status, and **automatically rolls over good + defective quantities to the next station** (Inbound Qty = Good + Defective; lost units do not roll over; skipped/cancelled steps are bypassed).
- **Completion Stock Deduction**: When completing a work order, BOM component inventory is validated; if insufficient, completion is blocked. If sufficient, atomic stock deduction is performed and logged in `StockTransaction` (OUTBOUND).
- **Work Order QR Code**: The top of the work order detail page renders a dynamically generated QR Code PNG (`qrcode`) encoding the work order number, ready to download and print for shop floor tagging.

### 9. Documents (Document Management)
| Model | Responsibility |
|---|---|
| `DocumentCategory` | Document category |
| `Document` | Title, code (unique), category FK, content, version, approval status, submitter/approver |
| `DocumentImage` | Multiple document attachments/images |
| `DocumentAuditLog` | Audit trail history (create / submit / approve / reject / recall / toggle active status) |

- Approval workflow: `draft → pending → approved / rejected`; resubmitting after rejection auto-increments version.
- Permissions: Submitter can recall pending documents; drafts/rejected documents can be edited or deleted; approved documents can only be modified by manager/admin.

### 10. FileLibrary (File Library)
| Model | Responsibility |
|---|---|
| `FileCategory` | File category |
| `LibraryFile` | File attachment, category FK, description, uploader, `video_status` / `video_standard` / `video_error` (video transcoding) |

- **Chunked Upload**: Files >5MB are automatically split into 5MB chunks with progress bar, resumable uploads, and a single-file limit of 100MB.
- **Video Transcoding**: Uploaded videos are converted asynchronously to 720p / **H.264** / MP4 (compatible across all modern browsers) for instant in-browser playback.
- Permissions: Admin has full upload/edit/delete/category management; manager can upload; operator can view and download.

## Role-Based Access Control (RBAC) Matrix

| Feature | admin | manager | operator |
|---|:---:|:---:|:---:|
| View / Download | ✅ | ✅ | ✅ |
| Create (All Modules) | ✅ | ✅ | ❌ |
| Edit / Delete | ✅ | Partial | ❌ |
| Document Submit / Recall | ✅ | ✅ | ✅ (Own only) |
| Document Approval | ✅ | ✅ | ❌ |
| File Library Upload | ✅ | ✅ | ❌ |
| File Library Delete / Category Management | ✅ | ❌ | ❌ |

## Database Relationship Diagram (Text Version)

```
Department 1 ────< Employee >──── 1 Position
MaterialCategory 1 ────< Material
Material 1 ────< StockTransaction
ProductCategory 1 ────< Product
Product 1 ────< WorkOrder >──── Customer
Product 1 ────< BOM 1 ────< BOMItem >──── Material (Component)
ProcessStep 1 ────< WorkOrderStep >──── WorkOrder
DocumentCategory 1 ────< Document >───── auth.User
Document 1 ────< DocumentImage / DocumentAuditLog
FileCategory 1 ────< LibraryFile >───── auth.User
```

## URL Routing (`miniMES/urls.py`)

| Prefix | App | Description |
|---|---|---|
| `/admin/` | Django Admin | Superuser administration portal |
| `/accounts/` | django.contrib.auth | Login / Logout / Password reset |
| `/` | Dashboard | Home page / Dashboard |
| `/org/` | Orgnization | Department, position, and employee management |
| `/equipment/` | Equipment | Equipment management |
| `/material/` | Material | Material management |
| `/product/` | Product | Product management |
| `/supplier/` | Supplier | Supplier management |
| `/customer/` | Customer | Customer management |
| `/production/` | Production | Work orders, BOM, and process routing |
| `/documents/` | Documents | Document management |
| `/files/` | FileLibrary | File library |

## CI (GitHub Actions)

- File: `.github/workflows/django.yml`
- Triggers: push / PR to `main`
- Actions: checkout → Python 3.12 setup → `pip install -r requirements.txt` → `python manage.py test`

## Deployment

### uWSGI + Nginx

Key Files:
- `uwsgi.ini`: uWSGI startup configuration (includes `post-buffering=8192` for large file upload buffering)
- `nginx.conf`: Nginx configuration
- `uwsgi_params`: Nginx-to-uWSGI parameter forwarding
- `Nginx.md`: Operation commands and troubleshooting guide

Recommended Steps:
1. `python -m venv .venv && source .venv/bin/activate`
2. `pip install -r requirements.txt`
3. `python manage.py migrate`
4. `python manage.py collectstatic` (when static files are updated)
5. Update `alias` paths for `/static` and `/media` in `nginx.conf`
6. Update `chdir`, `wsgi-file`, and `virtualenv` paths in `uwsgi.ini`
7. `uwsgi --ini uwsgi.ini`
8. `sudo nginx -c /path/to/nginx.conf`

### Deployment Notes

- Deployments should **sync code only**; do not overwrite `db.sqlite3`, `media/`, `uwsgi.ini`, `nginx.conf`, or `nginx.pid` in production.
- The `virtualenv` path in `uwsgi.ini` must point to the actual virtual environment.
- Video transcoding requires `ffmpeg` (with `libx264`) installed on the server.
- If new features modify models, run `python manage.py makemigrations <app> && python manage.py migrate` on the server (migrations are not committed to git and should be generated per environment).

### Environment Variables (Security Configuration)

`miniMES/settings.py` supports overriding security settings via environment variables (falls back to development defaults when unset, without affecting local dev):

| Variable | Default | Description |
|---|---|---|
| `DJANGO_SECRET_KEY` | Development key (not recommended for production) | Must be set in production, e.g. via `openssl rand -hex 32` |
| `DJANGO_DEBUG` | `true` | Set to `false` in production |
| `DJANGO_ALLOWED_HOSTS` | `*` | Comma-separated list of hostnames, e.g., `example.com,www.example.com` |
| `DJANGO_SECURE_SSL_REDIRECT` | Disabled | Set to `true` to enforce HTTPS redirects (behind Nginx) |
| `DJANGO_SECURE_COOKIES` | Disabled | Set to `true` to ensure Session/CSRF cookies are transmitted via HTTPS only |

Example:

```bash
export DJANGO_SECRET_KEY="$(openssl rand -hex 32)"
export DJANGO_DEBUG=false
export DJANGO_ALLOWED_HOSTS=mes.example.com
uwsgi --ini uwsgi.ini
```

### FAQs / Troubleshooting

- Nginx upload permissions: `sudo chmod -R 775 /run/nginx/client_body_temp`
- Video has audio but no picture: Verify transcoding codec is H.264 (`libx264`); H.265 is not supported on desktop Chrome.
- Out of memory during large file uploads: Ensure `uwsgi.ini` contains `post-buffering = 8192`.

## Developers

- GitHub: [miniCloudMES/Antigravity_MES](https://github.com/miniCloudMES/Antigravity_MES)
