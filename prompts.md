**prompt 1**

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
