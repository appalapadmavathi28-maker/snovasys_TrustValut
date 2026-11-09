from functools import wraps
from flask import abort, request, flash, redirect, url_for
from flask_login import current_user
from app.extensions import db
from app.models import Document, Share
from app.utils.audit import log_audit


def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            return redirect(url_for('auth.login', next=request.url))
        if current_user.role != 'admin':
            log_audit(
                action='UNAUTHORIZED_ACCESS',
                status='denied',
                user_id=current_user.id,
                details=f"User attempted unauthorized access to admin endpoint: {request.path}"
            )
            abort(403)
        return f(*args, **kwargs)
    return decorated_function


def document_access_required(permission='view'):
    """
    Decorator to verify that the current user has the required permission
    ('view', 'download', or 'edit') on the requested document.
    Owners and Admins always have full permissions.
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not current_user.is_authenticated:
                return redirect(url_for('auth.login', next=request.url))

            # Retrieve document ID from kwargs (matches route parameter <doc_id>)
            doc_id = kwargs.get('doc_id') or kwargs.get('document_id')
            if not doc_id:
                abort(404)

            document = db.session.get(Document, doc_id)
            if not document:
                abort(404)

            # Admins have full access
            if current_user.is_admin():
                return f(*args, **kwargs)

            # Owner has full access
            if document.owner_id == current_user.id:
                return f(*args, **kwargs)

            # Check shared access
            share = Share.query.filter_by(
                document_id=document.id,
                user_id=current_user.id
            ).first()

            if share and share.has_permission(permission):
                return f(*args, **kwargs)

            # Access Denied: Log audit and abort 403
            log_audit(
                action='UNAUTHORIZED_ACCESS',
                status='denied',
                user_id=current_user.id,
                document_id=document.id,
                details=f"Unauthorized '{permission}' attempt on document '{document.title}' (ID: {document.id})"
            )
            abort(403)

        return decorated_function
    return decorator
