import os
import click
from datetime import datetime, timezone
from flask import Flask, render_template, request
from config import config
from app.extensions import db, migrate, login_manager, csrf, limiter


def create_app(config_name=None):
    if config_name is None:
        config_name = os.environ.get('FLASK_CONFIG', 'default')

    app = Flask(__name__)
    app.config.from_object(config[config_name])

    # Ensure upload directory exists
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

    # Initialize extensions
    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)
    csrf.init_app(app)
    limiter.init_app(app)

    # Register Blueprints
    from app.auth import auth_bp
    from app.documents import documents_bp
    from app.admin import admin_bp

    app.register_blueprint(auth_bp, url_prefix='/auth')
    app.register_blueprint(documents_bp)
    app.register_blueprint(admin_bp, url_prefix='/admin')

    # Security Headers Hook
    @app.after_request
    def set_security_headers(response):
        response.headers['X-Content-Type-Options'] = 'nosniff'
        response.headers['X-Frame-Options'] = 'SAMEORIGIN'
        response.headers['X-XSS-Protection'] = '1; mode=block'
        response.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'
        # Modern Content-Security-Policy that permits Bootstrap, Bootstrap Icons, Chart.js CDNs
        response.headers['Content-Security-Policy'] = (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; "
            "style-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; "
            "font-src 'self' https://cdn.jsdelivr.net; "
            "img-src 'self' data:; "
            "frame-src 'self'; "
            "object-src 'none';"
        )
        return response

    # Template context processor
    @app.context_processor
    def inject_utilities():
        from app.models import utc_now
        return dict(
            current_time=utc_now(),
            now=datetime.now(timezone.utc)
        )

    # Error Handlers
    @app.errorhandler(403)
    def forbidden_error(error):
        return render_template('errors/403.html'), 403

    @app.errorhandler(404)
    def not_found_error(error):
        return render_template('errors/404.html'), 404

    @app.errorhandler(413)
    def request_entity_too_large(error):
        return render_template('errors/413.html'), 413

    @app.errorhandler(429)
    def ratelimit_handler(e):
        return render_template('errors/429.html', error=e), 429

    @app.errorhandler(500)
    def internal_error(error):
        db.session.rollback()
        return render_template('errors/500.html'), 500

    # Register CLI commands
    register_commands(app)

    return app


def register_commands(app):
    @app.cli.command("create-admin")
    @click.option("--name", default="System Administrator", help="Admin's full name")
    @click.option("--email", prompt="Admin Email", help="Admin's email address")
    @click.option("--password", prompt=True, hide_input=True, confirmation_prompt=True, help="Admin password")
    def create_admin(name, email, password):
        """Create a default or new Administrator account."""
        from app.models import User
        from app.utils.audit import log_audit

        with app.app_context():
            db.create_all()
            existing_user = User.query.filter_by(email=email.strip().lower()).first()
            if existing_user:
                click.secho(f"User with email '{email}' already exists. Updating role to 'admin'...", fg="yellow")
                existing_user.role = 'admin'
                existing_user.is_active = True
                existing_user.set_password(password)
                existing_user.reset_failed_attempts()
                db.session.commit()
                click.secho(f"User '{email}' updated to Administrator successfully!", fg="green")
            else:
                admin_user = User(
                    name=name.strip(),
                    email=email.strip().lower(),
                    role='admin',
                    is_active=True
                )
                admin_user.set_password(password)
                db.session.add(admin_user)
                db.session.commit()
                log_audit(
                    action='USER_CREATE',
                    status='success',
                    user_id=admin_user.id,
                    details=f"Admin account created via CLI: {admin_user.email}"
                )
                click.secho(f"Administrator account '{email}' created successfully!", fg="green")

    @app.cli.command("seed-demo")
    def seed_demo():
        """Seed sample demo data (Admin, Users, Documents, Shares, Audit Logs)."""
        from app.models import User, Document, Share, AuditLog, utc_now
        from app.utils.encryption import encrypt_data

        with app.app_context():
            db.create_all()

            # 1. Admin
            admin = User.query.filter_by(email='admin@securedocs.local').first()
            if not admin:
                admin = User(name='Admin Officer', email='admin@securedocs.local', role='admin', is_active=True)
                admin.set_password('AdminSecure123!')
                db.session.add(admin)

            # 2. Regular User 1 (Alice)
            alice = User.query.filter_by(email='alice@securedocs.local').first()
            if not alice:
                alice = User(name='Alice Vance', email='alice@securedocs.local', role='user', is_active=True)
                alice.set_password('AlicePass123!')
                db.session.add(alice)

            # 3. Regular User 2 (Bob)
            bob = User.query.filter_by(email='bob@securedocs.local').first()
            if not bob:
                bob = User(name='Bob Smith', email='bob@securedocs.local', role='user', is_active=True)
                bob.set_password('BobPass123!')
                db.session.add(bob)

            db.session.commit()

            # 4. Create sample encrypted documents for Alice
            doc1_id = "demo-policy-uuid-101"
            doc1_filename = f"{doc1_id}.enc"
            doc1_path = os.path.join(app.config['UPLOAD_FOLDER'], doc1_filename)
            doc1_content = b"CONFIDENTIAL CORPORATE SECURITY POLICY\nVersion 2.4\nAll documents must be encrypted at rest.\nStrict role-based access control applies."
            
            with open(doc1_path, 'wb') as f:
                f.write(encrypt_data(doc1_content))

            doc1 = Document.query.get(doc1_id)
            if not doc1:
                doc1 = Document(
                    id=doc1_id,
                    title="Company Security Policy 2026",
                    description="Standard enterprise cryptographic and sharing compliance guidelines.",
                    original_filename="Company_Security_Policy_2026.txt",
                    stored_filename=doc1_filename,
                    mime_type="text/plain",
                    size=len(doc1_content),
                    owner_id=alice.id
                )
                db.session.add(doc1)
                db.session.commit()

            # 5. Share with Bob (Download permission)
            share1 = Share.query.filter_by(document_id=doc1_id, user_id=bob.id).first()
            if not share1:
                share1 = Share(
                    document_id=doc1_id,
                    user_id=bob.id,
                    created_by_id=alice.id,
                    permission='download',
                    is_revoked=False
                )
                db.session.add(share1)

            # 6. Sample Audit logs
            audit_records = [
                AuditLog(user_id=alice.id, document_id=doc1_id, action='UPLOAD', status='success', ip_address='127.0.0.1', user_agent='Mozilla/5.0 Demo Browser', details='Alice uploaded Security Policy'),
                AuditLog(user_id=alice.id, document_id=doc1_id, action='SHARE_CREATE', status='success', ip_address='127.0.0.1', user_agent='Mozilla/5.0 Demo Browser', details='Alice shared policy with Bob (permission: download)'),
                AuditLog(user_id=bob.id, document_id=doc1_id, action='VIEW', status='success', ip_address='127.0.0.1', user_agent='Mozilla/5.0 Demo Browser', details='Bob viewed encrypted document'),
                AuditLog(user_id=bob.id, document_id=doc1_id, action='DOWNLOAD', status='success', ip_address='127.0.0.1', user_agent='Mozilla/5.0 Demo Browser', details='Bob downloaded decrypted document'),
            ]
            for r in audit_records:
                db.session.add(r)

            db.session.commit()
            click.secho("Demo seed data created successfully!", fg="green")
            click.secho("Accounts:", fg="cyan")
            click.secho("  - Admin: admin@securedocs.local / AdminSecure123!", fg="cyan")
            click.secho("  - User 1: alice@securedocs.local / AlicePass123!", fg="cyan")
            click.secho("  - User 2: bob@securedocs.local / BobPass123!", fg="cyan")
