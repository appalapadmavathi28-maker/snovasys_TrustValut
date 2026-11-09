# SecureDocs - Secure Document Sharing Platform

SecureDocs is a complete, production-quality web application built with Python Flask that allows organizations to securely store, share, and track confidential documents. Every uploaded file is encrypted at rest using Fernet (128-bit AES in CBC mode with HMAC SHA-256), and decrypted strictly in memory upon authorized request. Comprehensive role-based access control (RBAC), automatic brute-force lockout, rate limiting, and an immutable append-only audit trail provide enterprise-grade data protection and visibility.

---

## Key Highlights & Features

### 1. Robust Authentication & Account Governance
- **Registration & Login**: Secure password hashing via Werkzeug (`scrypt`/`pbkdf2`), password complexity enforcement (minimum 8 characters, uppercase, lowercase, numbers, and symbols).
- **Brute-Force Protection**: Automatic account lockout for 15 minutes after 5 consecutive failed login attempts.
- **Rate Limiting**: Built-in IP-based rate limiting via `Flask-Limiter`.
- **Session Hardening**: Strict session cookie policies (`HttpOnly`, `SameSite=Lax`, strict lifetime).
- **Access Revocation**: Administrators can revoke user accounts at any time. Revoking immediately invalidates the user's active shares and terminates their login privileges.

### 2. At-Rest Encryption & Document Lifecycle
- **Zero-Plaintext Storage**: All uploaded files are encrypted immediately on ingest via `cryptography.fernet.Fernet` and stored under non-guessable UUID filenames in `uploads/`. Plaintext files are never written to disk.
- **In-Memory Decryption**: Ciphertext is decrypted in memory only when an authorized user views or downloads the document.
- **Supported Formats**: PDF, DOCX, XLSX, PPTX, TXT, PNG, JPG, JPEG (enforced via extension validation, MIME type inspection, and a 16 MB upload cap).
- **Document Versioning / Replacement**: Owners and users with `edit` permissions can upload replacement versions that are re-encrypted on-the-fly.

### 3. Granular Access Control & Sharing
- **Permission Tiers**:
  - `View Only`: In-browser read-only preview; downloading and editing are blocked (returns HTTP 403).
  - `View & Download`: Inline preview plus full decrypted file download.
  - `Full Access (Edit)`: View, download, and replace/update the file contents.
- **Time-Bound Sharing**: Optional expiration dates and times on shares. Expired shares immediately return HTTP 403.
- **Immediate Share Revocation**: Owners and administrators can revoke individual shares at any time.

### 4. Immutable Append-Only Audit Trail
- **Comprehensive Event Logging**: Captures `LOGIN_SUCCESS`, `LOGIN_FAILED`, `LOGOUT`, `ACCOUNT_LOCKED`, `UPLOAD`, `VIEW`, `DOWNLOAD`, `EDIT_DOCUMENT`, `SHARE_CREATE`, `SHARE_UPDATE`, `SHARE_REVOKE`, `DELETE_DOCUMENT`, `USER_REVOKE`, `USER_RESTORE`, and `UNAUTHORIZED_ACCESS`.
- **Forensic Context**: Every entry permanently logs client IP address, User-Agent, user ID, document UUID, operation status (`success` or `denied`), timestamp (UTC), and details.
- **Per-Document Trail**: Document owners can inspect who viewed, downloaded, or attempted unauthorized access to their specific documents.
- **Admin Audit Center**: Search, filter by action, status, user, date range, pagination, red visual highlights for security incidents, and one-click **CSV Export**.

### 5. Administrative Dashboard
- **Telemetry Cards**: Total users, total documents, active shares, and unauthorized attempt counts.
- **Visual Analytics**: Interactive 7-day security telemetry chart powered by Chart.js.
- **Incident Response**: Admins can immediately revoke offending users straight from the unauthorized attempts list or audit trail.
- **Document Moderation**: Global oversight of all files with force-deletion capability.

---

## Tech Stack

| Layer | Technology |
|---|---|
| **Framework** | Python 3.13, Flask 3.1 (Application Factory pattern with Blueprints) |
| **Database & ORM** | SQLite via Flask-SQLAlchemy, migrations ready with Flask-Migrate |
| **Authentication** | Flask-Login, Werkzeug password security |
| **Forms & CSRF** | Flask-WTF with CSRF tokens on all POST requests |
| **Encryption at Rest** | `cryptography.fernet.Fernet` (128-bit AES in CBC mode with HMAC SHA-256) |
| **Rate Limiting** | Flask-Limiter |
| **Frontend UI** | Jinja2 templates, Bootstrap 5.3, Bootstrap Icons, Chart.js, Vanilla JS |
| **Testing** | Pytest (26 automated test cases covering auth, permissions, audit, encryption) |

---

## Project Structure

```
snovasys/
├── app/
│   ├── __init__.py          # App factory, error handlers, CSP security headers, CLI commands
│   ├── models.py            # User, Document, Share, AuditLog models
│   ├── extensions.py        # db, migrate, login_manager, csrf, limiter
│   ├── auth/                # Blueprint: login, register, logout, forms
│   │   ├── __init__.py
│   │   ├── forms.py
│   │   └── routes.py
│   ├── documents/           # Blueprint: upload, preview, download, share, revoke, per-doc audit
│   │   ├── __init__.py
│   │   ├── forms.py
│   │   └── routes.py
│   ├── admin/               # Blueprint: dashboard, user management, audit trail & CSV export
│   │   ├── __init__.py
│   │   └── routes.py
│   ├── utils/
│   │   ├── encryption.py    # Fernet cipher read/write/decrypt helpers
│   │   ├── audit.py         # Append-only audit logger capturing IP & UA
│   │   └── decorators.py    # @admin_required, @document_access_required
│   ├── templates/
│   │   ├── base.html        # Responsive Bootstrap 5 layout with dark/blue corporate theme
│   │   ├── auth/            # login.html, register.html
│   │   ├── documents/       # dashboard.html, my_documents.html, shared_with_me.html, upload.html, detail.html
│   │   ├── admin/           # dashboard.html, users.html, documents.html, audit.html
│   │   └── errors/          # 403.html, 404.html, 413.html, 429.html, 500.html
│   └── static/
│       ├── css/custom.css   # Custom styling and audit highlights
│       └── js/main.js       # Dynamic confirmation modals, password strength meter
├── uploads/                 # Storage for encrypted files (*.enc)
├── tests/
│   ├── conftest.py          # Pytest fixtures, test client, isolated test uploads
│   ├── test_auth.py         # Registration, password complexity, login, lockout, revoked checks
│   ├── test_documents.py    # Encrypted upload, in-memory decrypt, view, replace, delete
│   ├── test_permissions.py  # 403 enforcement, view-only, download, expiry, revocation
│   ├── test_audit.py        # Audit trail logging, IP/UA capture, CSV export
│   └── test_admin.py        # Admin panel, user revocation, share invalidation
├── config.py                # Development, Testing, Production configurations
├── run.py                   # Application entrypoint
├── requirements.txt         # Pinned production dependencies
├── .env.example             # Environment variable template
├── .gitignore               # Ignored DB, test uploads, pycache, .env
└── README.md
```

---

## Getting Started

### 1. Prerequisites
- Python 3.11+ (Tested and verified on Python 3.13)
- `pip`

### 2. Installation
Clone the repository and install the dependencies:
```bash
pip install -r requirements.txt
```

### 3. Environment Configuration
Copy `.env.example` to `.env` or use the pre-configured `.env`:
```bash
cp .env.example .env
```
To generate a fresh Fernet encryption key at any time:
```bash
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```
Paste this into `ENCRYPTION_KEY` in your `.env`.

### 4. Seed Database & Demo Data
Run the built-in demo seeder CLI command:
```bash
flask seed-demo
```
This automatically initializes the database, creates standard documents, sets up shares, and generates sample audit records with the following accounts:

| Role | Email | Password |
|---|---|---|
| **Administrator** | `admin@securedocs.local` | `AdminSecure123!` |
| **Regular User 1** | `alice@securedocs.local` | `AlicePass123!` |
| **Regular User 2** | `bob@securedocs.local` | `BobPass123!` |

You can also create a custom administrator account at any time using:
```bash
flask create-admin --name "Security Officer" --email "secops@securedocs.local" --password "SecOpsMaster2026!"
```

### 5. Running the Application
Launch the Flask server:
```bash
python run.py
```
Open your browser and navigate to:
```
http://127.0.0.1:5000
```

---

## Automated Test Suite

Run the full automated test suite with `pytest`:
```bash
python -m pytest -v
```
All **26 tests** will execute and verify:
- Registration, validation, and password strength rules
- Brute-force lockout after 5 consecutive failed logins
- Revoked users blocked from logging in with a clear explanation
- Zero-plaintext encrypted storage on disk and decryption in memory
- Permission enforcement: View-only users receive HTTP 403 on download attempts
- Expired and revoked shares return HTTP 403
- Append-only audit logging of all security and file operations with IP address & User-Agent
- CSV export of audit trails
- Admin user revocation invalidating sessions and active shares immediately

---

## Security Hardening Details

1. **Defense-in-Depth Cryptography**:
   - Files are encrypted before reaching disk storage with Fernet AES-128-CBC + HMAC SHA-256.
   - Keys are kept strictly in server-side configuration/environment variables.
2. **IDOR & Path Traversal Prevention**:
   - Files are stored using random UUIDv4 names (e.g. `b024797e-2672-4dad-8991-1296b4f3d5fd.enc`).
   - Original filenames are sanitized using `werkzeug.utils.secure_filename` before being recorded in metadata.
3. **HTTP Security Headers**:
   - `Content-Security-Policy`: Restricts scripts, styles, objects, and framing to trusted CDNs and `'self'`.
   - `X-Content-Type-Options: nosniff`: Prevents MIME-type sniffing.
   - `X-Frame-Options: SAMEORIGIN`: Prevents clickjacking.
   - `Referrer-Policy: strict-origin-when-cross-origin`: Minimizes referrer leakage.
4. **Session Protection**:
   - `HttpOnly`: Prevents JavaScript access to authentication cookies.
   - `SameSite=Lax`: Mitigates Cross-Site Request Forgery.
   - CSRF tokens validated on every form submission.
5. **SQL Injection Prevention**:
   - All database queries are parameterized through the SQLAlchemy 2.0 ORM.
