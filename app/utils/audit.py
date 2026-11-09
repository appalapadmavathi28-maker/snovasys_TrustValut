from flask import request, has_request_context
from flask_login import current_user
from app.extensions import db
from app.models import AuditLog


def get_client_ip():
    if not has_request_context():
        return '127.0.0.1'
    if request.headers.get('X-Forwarded-For'):
        # In case of proxy, the first IP is the client IP
        return request.headers.get('X-Forwarded-For').split(',')[0].strip()
    return request.remote_addr or '127.0.0.1'


def get_user_agent():
    if not has_request_context():
        return 'System'
    ua = request.headers.get('User-Agent', 'Unknown')
    return ua[:255] if ua else 'Unknown'


def log_audit(action: str, status: str = 'success', user=None, user_id=None,
              document=None, document_id=None, details: str = None, commit: bool = True):
    """
    Append-only audit trail logger.
    Automatically captures client IP, user agent, timestamp, status, and related identifiers.
    """
    uid = None
    if user_id is not None:
        uid = user_id
    elif user is not None:
        uid = getattr(user, 'id', None)
    elif has_request_context() and current_user.is_authenticated:
        uid = current_user.id

    doc_id = None
    if document_id is not None:
        doc_id = document_id
    elif document is not None:
        doc_id = getattr(document, 'id', None)

    log_entry = AuditLog(
        user_id=uid,
        document_id=doc_id,
        action=action,
        ip_address=get_client_ip(),
        user_agent=get_user_agent(),
        status=status,
        details=details
    )

    db.session.add(log_entry)
    if commit:
        try:
            db.session.commit()
        except Exception:
            db.session.rollback()
            raise

    return log_entry
