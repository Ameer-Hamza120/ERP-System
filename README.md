# ERP System

A professional, modular Enterprise Resource Planning (ERP) system built with **Python Django**, **Django REST Framework**, **PostgreSQL**, and vanilla **HTML/CSS/JavaScript**.

## System Architecture

```
Presentation Layer  →  HTML5 + CSS3 + JS (templates/static)
        ↓
Business Logic     →  Python Django (apps/)
        ↓
Data Access        →  Django ORM
        ↓
Database           →  PostgreSQL
```

## Phase 1 — Foundation & Administration

### Features Implemented

| Module | Key Features |
|--------|-------------|
| **Authentication** | Login/Logout, password change, session-based auth, brute-force protection (configurable max attempts + lockout) |
| **Dashboard** | Permission-aware widgets: user/items/warehouses/stock counts, low-stock alerts, pending approvals, recent activity, document numbering status |
| **Users** | CRUD, role assignment, activate/deactivate, password reset, audit trail |
| **Roles** | CRUD, permission assignment via checkboxes, granular permissions per model |
| **Permissions** | View, Add, Change, Delete, plus custom (`can_manage_stock`, `can_view_auditlog`) |
| **Company Settings** | Company name, logo, address, city, country, phone, email, website, tax/VAT ID, base currency, fiscal year, date format, timezone, default warehouse, default payment terms, invoice terms |
| **Document Numbering** | Configurable per document type (SO, PO, INV, GR, ST, ITM), year prefix, configurable padding, atomic sequential numbering (no duplicates) |
| **Audit Log** | Automatic recording of Login/Logout (via signals), Create/Update/Delete for Users, Roles, Items, Item Groups, Warehouses, Stock Movements, Stock Transfers, Company Settings. Viewable list with filters + detail page with old/new values. Read-only in admin. |
| **API** | REST endpoints for auth, users, roles, permissions, company settings, document sequences, items, warehouses, stock, stock movements, transfers (DRF) |

### Security

- Password hashing (Django default PBKDF2)
- CSRF protection
- Input validation (server-side)
- SQL injection protection (Django ORM)
- XSS protection (template auto-escaping)
- Secure session cookies (configurable)
- Login brute-force protection (cache-based, configurable attempts/lockout)
- API rate limiting (DRF throttling)
- Granular permission checks on every view
- Permission-aware sidebar (users see only what they can access)
- Environment variables for secrets
- `.env.example` template provided

### Default Roles

1. **Super Admin** — All permissions
2. **Manager** — View users, full inventory management
3. **Employee** — Read-only inventory views
4. **Inventory Manager** — Full inventory management
5. **Inventory Employee** — View inventory + create transfers

Roles are stored in the database. Administrators can create/edit/delete roles via the web interface.

## Phase 3 — Inventory (Implemented)

| Module | Key Features |
|--------|-------------|
| **Item Groups** | CRUD, active/inactive, search |
| **Items** | Code, name, SKU, barcode, group, description, UOM, purchase/selling price, tax %, min/max stock, reorder level, opening stock by warehouse, active/inactive |
| **Warehouses** | Code, name, location, address, city, country, manager, description, active/inactive |
| **Stock** | Per-item-per-warehouse quantity, Stock In/Out with validation, full movement history |
| **Stock Movements** | Immutable audit trail: Opening Stock, Stock In, Stock Out, Adjustment, Transfer Out/In, Purchase Receipt, Sales Delivery, Return |
| **Stock Transfers** | Source → Destination, Pending → Complete (validates stock) / Cancel, approval tracking, notes, document numbering (ST-YYYY-NNNNNN) |

## Technology Stack

| Layer | Technology |
|-------|-----------|
| Backend | Python 3.14+, Django 6.x |
| API | Django REST Framework 3.x |
| Database | PostgreSQL |
| Frontend | HTML5, CSS3, Vanilla JavaScript |
| Auth | Django auth + session/token |
| ORM | Django ORM |

## Project Structure

```
erp_system/
├── manage.py
├── requirements.txt
├── .env.example
├── .gitignore
├── config/
│   ├── settings.py          # Django settings (DB, apps, templates, DRF, security)
│   ├── urls.py              # Root URL configuration
│   ├── asgi.py
│   └── wsgi.py
├── accounts/
│   ├── models.py            # CompanySettings, DocumentSequence
│   ├── forms.py             # User, Role, CompanySettings, DocumentSequence forms
│   ├── views.py             # Dashboard, User, Role, CompanySettings, DocumentSequence
│   ├── views_api.py         # DRF API views (auth, users, groups, permissions, settings)
│   ├── serializers.py       # DRF serializers
│   ├── urls.py              # Web URLs
│   ├── api_urls.py          # API URLs
│   ├── context_processors.py # Global template context (pending approvals, company)
│   ├── tests.py             # 18 tests
│   └── management/commands/
│       ├── setup_roles.py   # Seed roles, permissions, document sequences
│       └── create_super_admin.py  # Create first super admin interactively
├── inventory/
│   ├── models.py            # ItemGroup, Item, Warehouse, Stock, StockMovement, StockTransfer
│   ├── forms.py             # All inventory forms
│   ├── views.py             # CRUD + stock operations + audit logging
│   ├── views_api.py         # JSON API endpoints
│   ├── urls.py              # Web URLs
│   ├── api_urls.py          # API URLs
│   └── tests.py             # 20 tests
├── reports/
│   ├── views.py             # Inventory report, low stock, transfer report, CSV export
│   └── urls.py
├── audit/
│   ├── models.py            # AuditLog model
│   ├── log.py              # log_activity() helper + login/logout signals
│   ├── signals.py           # Signal imports
│   ├── views.py             # Audit log list + detail
│   ├── urls.py
│   ├── admin.py             # Read-only admin
│   └── tests.py             # 6 tests
├── templates/
│   ├── base.html            # Permission-aware sidebar, topbar search, notifications
│   ├── includes/pagination.html
│   ├── accounts/            # Login, dashboard, user/role/company/document sequence templates
│   ├── inventory/           # Item, warehouse, stock, transfer templates
│   ├── reports/             # Report templates
│   └── audit/               # Audit log list + detail
├── static/
│   ├── css/style.css        # Full responsive stylesheet
│   └── js/main.js           # Alert auto-hide, delete confirm, sidebar toggle
└── media/                   # Uploaded logos, item images
```

## API Endpoints

### Authentication & Accounts
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/auth/login/` | Login (returns user data) |
| POST | `/api/auth/logout/` | Logout |
| GET | `/api/auth/me/` | Current user profile + permissions |
| GET/POST | `/api/users/` | List / Create users |
| GET/PUT/DELETE | `/api/users/{id}/` | Retrieve / Update / Delete user |
| GET/POST | `/api/groups/` | List / Create roles |
| GET/PUT/DELETE | `/api/groups/{id}/` | Retrieve / Update / Delete role |
| GET | `/api/permissions/` | List all permissions (filterable by `?app=`) |
| GET/PUT | `/api/company-settings/` | Get / Update company settings |
| GET/PUT | `/api/document-sequences/` | List / Update document sequences |

### Inventory
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET/POST | `/api/items/` | List / Create items |
| GET/PUT/DELETE | `/api/items/{id}/` | Retrieve / Update / Delete item |
| GET | `/api/warehouses/` | List warehouses |
| GET | `/api/stock/` | List stock records |
| GET | `/api/stock-movements/` | List stock movements (filter by `?item=` & `?warehouse=`) |
| GET/POST | `/api/transfers/` | List / Create stock transfers |

## Installation

### Prerequisites

- Python 3.10+
- PostgreSQL installed and running
- pip

### Setup

1. **Clone the project** and open the terminal in the project directory.

2. **Create and activate a virtual environment:**
   ```bash
   python -m venv venv
   source venv/bin/activate      # Linux/macOS
   venv\Scripts\activate         # Windows
   ```

3. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure PostgreSQL database:**
   ```sql
   CREATE DATABASE erp;
   \c erp
   GRANT ALL ON SCHEMA public TO postgres;
   ```
   The defaults in `.env`/`settings.py` expect the `postgres` user with password `123`. Adjust `DB_USER`/`DB_PASSWORD` in `.env` to match your PostgreSQL installation.

5. **Configure environment (optional):**
   Copy `.env.example` to `.env` and adjust values. Defaults work with the setup above.

6. **Run migrations:**
   ```bash
   python manage.py migrate
   ```

7. **Seed roles, permissions, and document sequences:**
   ```bash
   python manage.py setup_roles
   ```

8. **Create super admin:**
   ```bash
   python manage.py create_super_admin
   ```

9. **Start the development server:**
   ```bash
   python manage.py runserver
   ```

10. **Open** [http://127.0.0.1:8000](http://127.0.0.1:8000) and log in with the super admin credentials.

## Running Tests

```bash
python manage.py test accounts inventory audit reports
```

All 41 tests should pass.

## Audit Log

The system automatically records important actions:
- **Login/Logout** — via Django signals
- **User Management** — Create, Update, Delete, Password Reset
- **Role Management** — Create, Update, Delete
- **Company Settings** — Updates (with old/new values)
- **Inventory** — Item/Group/Warehouse CRUD, Stock In/Out, Stock Transfer lifecycle
- **API** — Item CRUD and Transfer creation via API

Audit log entries are viewable from the Administration sidebar and are read-only.

## Document Numbering

Every important ERP document receives a unique number. The system uses an atomic counter (`select_for_update`) to guarantee no duplicates even under concurrent requests.

Default sequences created by `setup_roles`:
- SO → `SO-2026-000001`
- PO → `PO-2026-000001`
- INV → `INV-2026-000001`
- GR → `GR-2026-000001`
- ST → `ST-2026-000001`
- ITM → `ITM-0001` (no year)

Configure from Administration → Document Numbering.

## Business Rules

- **Stock** cannot go negative (Stock Out validates quantity).
- **Stock Transfer** source and destination warehouse must be different.
- **Stock Transfer** only moves stock when Completed (Pending → validated → Completed).
- **Audit Log** is immutable (no add/change/delete through admin).
- **Prices** cannot be negative.
- **Document numbers** are unique per type (atomic sequence).
- **Login** locks after configurable number of failed attempts (default: 5, 15-min lockout).

## Known Limitations

- No email/SMS notifications for pending approvals.
- No multi-company support (single company model).
- No multi-currency support (single base currency).
- No file/attachment management beyond logos and item images.
- Login throttling uses Django cache (LocMemCache by default; Redis recommended for production).

## Recommended Next Phase

**Phase 4 — Sales** (Customers, Sales Quotations, Sales Orders, Deliveries, Returns, Invoices) with integration to the Inventory stock system.