import uuid
from datetime import datetime, timezone
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from app.extensions import db, login_manager


def utc_now():
    return datetime.now(timezone.utc)


class User(UserMixin, db.Model):
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(20), default='user', nullable=False)  # 'admin' or 'user'
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    failed_attempts = db.Column(db.Integer, default=0, nullable=False)
    locked_until = db.Column(db.DateTime, nullable=True)
    last_login = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, default=utc_now, nullable=False)

    # Relationships
    documents = db.relationship('Document', backref='owner', lazy='dynamic', cascade='all, delete-orphan')
    shares = db.relationship('Share', foreign_keys='Share.user_id', backref='recipient', lazy='dynamic', cascade='all, delete-orphan')
    audit_logs = db.relationship('AuditLog', foreign_keys='AuditLog.user_id', backref='user', lazy='dynamic')

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def is_locked(self):
        if self.locked_until is None:
            return False
        # Normalize comparison to timezone-naive UTC for SQLite compatibility
        locked_naive = self.locked_until.replace(tzinfo=None) if self.locked_until.tzinfo else self.locked_until
        now_naive = utc_now().replace(tzinfo=None)
        return locked_naive > now_naive

    def record_failed_attempt(self, max_attempts=5, lockout_minutes=15):
        from datetime import timedelta
        self.failed_attempts += 1
        if self.failed_attempts >= max_attempts:
            # Store timezone-naive UTC
            self.locked_until = (utc_now() + timedelta(minutes=lockout_minutes)).replace(tzinfo=None)

    def reset_failed_attempts(self):
        self.failed_attempts = 0
        self.locked_until = None

    def is_admin(self):
        return self.role == 'admin'

    def __repr__(self):
        return f'<User {self.email} ({self.role})>'


@login_manager.user_loader
def load_user(user_id):
    try:
        user = db.session.get(User, int(user_id))
        # If user account was revoked or deactivated, do not authenticate
        if user and not user.is_active:
            return None
        return user
    except Exception:
        return None


class Document(db.Model):
    __tablename__ = 'documents'

    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    title = db.Column(db.String(150), nullable=False)
    description = db.Column(db.Text, nullable=True)
    original_filename = db.Column(db.String(255), nullable=False)
    stored_filename = db.Column(db.String(255), nullable=False)  # Encrypted on-disk filename
    mime_type = db.Column(db.String(100), nullable=False)
    size = db.Column(db.Integer, nullable=False)  # in bytes
    owner_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    created_at = db.Column(db.DateTime, default=utc_now, nullable=False)
    updated_at = db.Column(db.DateTime, default=utc_now, onupdate=utc_now, nullable=False)

    # Relationships
    shares = db.relationship('Share', backref='document', lazy='dynamic', cascade='all, delete-orphan')
    audit_logs = db.relationship('AuditLog', backref='document', lazy='dynamic', cascade='all, delete-orphan')

    @property
    def formatted_size(self):
        bytes_val = self.size
        for unit in ['B', 'KB', 'MB', 'GB']:
            if bytes_val < 1024.0:
                return f"{bytes_val:.1f} {unit}"
            bytes_val /= 1024.0
        return f"{bytes_val:.1f} TB"

    @property
    def file_extension(self):
        if '.' in self.original_filename:
            return self.original_filename.rsplit('.', 1)[1].lower()
        return ''

    @property
    def is_previewable(self):
        mime = self.mime_type.lower()
        ext = self.file_extension
        return (
            mime.startswith('image/') or
            mime == 'application/pdf' or
            mime.startswith('text/') or
            ext in {'txt', 'png', 'jpg', 'jpeg', 'pdf'}
        )

    def __repr__(self):
        return f'<Document {self.title} ({self.id})>'


class Share(db.Model):
    __tablename__ = 'shares'

    id = db.Column(db.Integer, primary_key=True)
    document_id = db.Column(db.String(36), db.ForeignKey('documents.id', ondelete='CASCADE'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    created_by_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='SET NULL'), nullable=True)
    permission = db.Column(db.String(20), nullable=False, default='view')  # 'view', 'download', 'edit'
    expires_at = db.Column(db.DateTime, nullable=True)
    is_revoked = db.Column(db.Boolean, default=False, nullable=False)
    created_at = db.Column(db.DateTime, default=utc_now, nullable=False)

    # Creator relationship
    creator = db.relationship('User', foreign_keys=[created_by_id])

    def is_expired(self):
        if self.expires_at is None:
            return False
        expires_naive = self.expires_at.replace(tzinfo=None) if self.expires_at.tzinfo else self.expires_at
        now_naive = utc_now().replace(tzinfo=None)
        return expires_naive <= now_naive

    def is_valid(self):
        return (not self.is_revoked) and (not self.is_expired())

    def has_permission(self, required_permission):
        if not self.is_valid():
            return False
        hierarchy = {'view': 1, 'download': 2, 'edit': 3}
        share_level = hierarchy.get(self.permission, 0)
        required_level = hierarchy.get(required_permission, 1)
        return share_level >= required_level

    def __repr__(self):
        return f'<Share Doc:{self.document_id} User:{self.user_id} Perm:{self.permission}>'


class AuditLog(db.Model):
    __tablename__ = 'audit_logs'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='SET NULL'), nullable=True)
    document_id = db.Column(db.String(36), db.ForeignKey('documents.id', ondelete='SET NULL'), nullable=True)
    action = db.Column(db.String(50), nullable=False)
    ip_address = db.Column(db.String(45), nullable=True)
    user_agent = db.Column(db.String(255), nullable=True)
    status = db.Column(db.String(20), default='success', nullable=False)  # 'success' or 'denied'
    details = db.Column(db.Text, nullable=True)
    timestamp = db.Column(db.DateTime, default=utc_now, nullable=False, index=True)

    def __repr__(self):
        return f'<AuditLog {self.action} Status:{self.status} Time:{self.timestamp}>'
