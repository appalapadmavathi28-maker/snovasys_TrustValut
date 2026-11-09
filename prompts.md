## prompt 1

You are a senior full-stack engineer. Build a complete, production-quality web application called "SecureDocs" (a secure document sharing platform) using Python Flask. Work autonomously: plan first, then create the project structure, write all code, install dependencies, run the app, test it, and fix any errors before finishing.

## PROJECT STATEMENT
A secure document sharing platform built with Flask that allows users to upload, share, and download documents with access permissions. Organizations can share documents securely, track every action performed on each document through an audit trail, detect unauthorized access, and revoke user access from an admin panel.

## TECH STACK
- Backend: Flask (Application Factory pattern + Blueprints)
- Database: SQLite via SQLAlchemy (Flask-SQLAlchemy) with Flask-Migrate
- Auth: Flask-Login, Werkzeug password hashing (or Flask-Bcrypt)
- Forms/CSRF: Flask-WTF
- Encryption: cryptography (Fernet) to encrypt files at rest
- Frontend: Jinja2 templates, Bootstrap 5, minimal vanilla JS. Clean, modern, responsive UI with a sidebar/navbar, cards, and tables
- Config via .env (python-dotenv)

## USER ROLES
1. Admin – manages all users, views all documents, views the full audit trail, revokes/restores access
2. User – uploads documents, shares them, downloads what's shared with them


## prompt 2

## CORE FEATURES

### 1. Authentication
- Register, login, logout
- Password hashing, password strength validation
- Session security (HttpOnly, SameSite cookies), CSRF protection on all forms
- Login rate limiting (Flask-Limiter) and account lockout after 5 failed attempts
- Seed a default admin account via a CLI command (flask create-admin)
- Blocked/revoked users cannot log in and see a clear "access revoked" message

### 2. Document Upload & Storage
- Upload documents (pdf, docx, xlsx, pptx, txt, png, jpg) with size limit (e.g., 16 MB)
- Validate extensions and MIME type, sanitize filenames (secure_filename), store with random UUID names
- Encrypt every file at rest with Fernet; decrypt only on authorized download/view
- Store metadata: title, description, original filename, size, type, owner, upload date

### 3. Sharing & Access Permissions
- Owner can share a document with specific users by email/username
- Permission levels: View-only, Download, Edit/Replace (owner can pick)
- Optional expiry date for each share
- Owner can revoke an individual share at any time
- Strict authorization check on every route (owner, shared user, or admin only). Return 403 otherwise
- "My Documents" and "Shared With Me" pages

### 4. Audit Trail (key feature)
- Log every action: login, failed login, logout, upload, view, download, share, permission change, revoke, delete, unauthorized access attempt
- Each log stores: user, document, action, IP address, user agent, timestamp, status (success/denied)
- Audit Trail page with filters (user, document, action type, date range, status), search, sorting, pagination
- Per-document audit page for owners showing who accessed their document
- Highlight unauthorized/denied attempts in red
- Export audit log as CSV
- Logs must be append-only (no edit/delete from the UI)

### 5. Admin Panel
- Dashboard with stats cards: total users, total documents, total shares, recent unauthorized attempts, plus a small chart (Chart.js) of activity over time
- Complete user list with: name, email, role, status, last login, document count, actions
- Revoke access / restore access / delete user buttons (with confirmation modal)
- Revoking a user immediately invalidates their sessions and removes all their active shares
- From the audit trail, an admin can click a user and jump straight to revoke their access
- View all documents and force-remove any share

### 6. Security Hardening
- CSRF tokens, secure headers (Flask-Talisman or manual CSP, X-Frame-Options, X-Content-Type-Options)
- Prevent path traversal and IDOR; use non-guessable IDs (UUID) for documents
- Parameterized queries only (SQLAlchemy ORM)
- Input validation and output escaping everywhere
- Secrets and encryption key loaded from environment, never hardcoded
- Custom error pages (403, 404, 413, 500)


## prompt 3


## PROJECT STRUCTURE

```text
securedocs/
├── app/
│   ├── __init__.py          # App factory
│   ├── models.py            # User, Document, Share, AuditLog
│   ├── extensions.py
│   ├── auth/                # Blueprint: routes, forms
│   ├── documents/           # Blueprint: upload, share, download, view
│   ├── admin/               # Blueprint: dashboard, users, audit
│   ├── utils/               # encryption.py, audit.py, decorators.py
│   ├── templates/           # base.html + per-feature folders
│   └── static/              # CSS, JS
├── uploads/                 # Encrypted files (gitignored)
├── migrations/
├── tests/                   # Pytest test cases
├── config.py
├── run.py
├── requirements.txt
├── .env.example
├── .gitignore
└── README.md
```


## prompt 4

## DATABASE MODELS
- User: id, name, email (unique), password_hash, role, is_active, failed_attempts, locked_until, last_login, created_at
- Document: id (UUID), title, description, original_filename, stored_filename, mime_type, size, owner_id, created_at
- Share: id, document_id, user_id, permission, expires_at, is_revoked, created_at
- AuditLog: id, user_id, document_id (nullable), action, ip_address, user_agent, status, details, timestamp

## UI PAGES
Login, Register, Dashboard, Upload, My Documents, Shared With Me, Document Detail (share form + per-document audit), Admin Dashboard, Admin Users, Admin Audit Trail, error pages. Use a consistent professional design (blue/dark theme), flash messages, and confirmation modals.


## prompt 5

## DELIVERABLES
1. Complete working code for everything above, no placeholders or TODOs
2. requirements.txt and .env.example
3. Seed script / CLI for the admin user and optional demo data
4. pytest tests covering: unauthorized access returns 403 and is logged, revoked user cannot log in, shared user permissions are enforced, audit logs are created for each action
5. README.md with setup steps, screenshots section, feature list, security notes, and the project statement
6. Run the app locally, verify every feature in the browser, and fix all bugs

## WORKING INSTRUCTIONS
- First write a short implementation plan, then execute it step by step
- Use the browser to test the full flow: register two users, upload, share, download, trigger an unauthorized access attempt, check the audit trail, and revoke the user as admin
- Keep code clean, commented, and modular
- At the end, summarize what was built, how to run it, and the default admin credentials
