import io
import csv
from datetime import datetime, timedelta, timezone
from flask import (
    render_template, redirect, url_for, flash, request, abort,
    Response, current_app
)
from flask_login import login_required, current_user
from sqlalchemy import func
from app.extensions import db
from app.admin import admin_bp
from app.models import User, Document, Share, AuditLog, utc_now
from app.utils.decorators import admin_required
from app.utils.audit import log_audit
from app.utils.encryption import delete_file


@admin_bp.before_request
@login_required
@admin_required
def require_admin_privileges():
    # Enforces admin check for all routes in this blueprint
    pass


@admin_bp.route('/dashboard')
def dashboard():
    total_users = User.query.count()
    total_documents = Document.query.count()
    total_shares = Share.query.filter_by(is_revoked=False).count()
    unauthorized_count = AuditLog.query.filter(
        (AuditLog.status == 'denied') | (AuditLog.action == 'UNAUTHORIZED_ACCESS')
    ).count()

    # Recent unauthorized attempts (last 10)
    recent_unauthorized = AuditLog.query.filter(
        (AuditLog.status == 'denied') | (AuditLog.action == 'UNAUTHORIZED_ACCESS')
    ).order_by(AuditLog.timestamp.desc()).limit(10).all()

    # Past 7 days activity trend for Chart.js
    labels = []
    success_counts = []
    denied_counts = []
    
    today = utc_now().date()
    for i in range(6, -1, -1):
        day = today - timedelta(days=i)
        day_str = day.strftime('%b %d')
        labels.append(day_str)
        
        day_start = datetime(day.year, day.month, day.day, 0, 0, 0)
        day_end = datetime(day.year, day.month, day.day, 23, 59, 59)
        
        success_c = AuditLog.query.filter(
            AuditLog.timestamp >= day_start,
            AuditLog.timestamp <= day_end,
            AuditLog.status == 'success'
        ).count()
        
        denied_c = AuditLog.query.filter(
            AuditLog.timestamp >= day_start,
            AuditLog.timestamp <= day_end,
            AuditLog.status == 'denied'
        ).count()
        
        success_counts.append(success_c)
        denied_counts.append(denied_c)

    return render_template(
        'admin/dashboard.html',
        total_users=total_users,
        total_documents=total_documents,
        total_shares=total_shares,
        unauthorized_count=unauthorized_count,
        recent_unauthorized=recent_unauthorized,
        chart_labels=labels,
        chart_success=success_counts,
        chart_denied=denied_counts
    )


@admin_bp.route('/users')
def users():
    search = request.args.get('q', '').strip()
    role_filter = request.args.get('role', '').strip()
    status_filter = request.args.get('status', '').strip()

    query = User.query
    if search:
        query = query.filter(
            (User.name.ilike(f'%{search}%')) |
            (User.email.ilike(f'%{search}%'))
        )
    if role_filter:
        query = query.filter_by(role=role_filter)
    if status_filter:
        if status_filter == 'active':
            query = query.filter_by(is_active=True)
        elif status_filter == 'revoked':
            query = query.filter_by(is_active=False)

    users_list = query.order_by(User.created_at.desc()).all()
    return render_template(
        'admin/users.html',
        users=users_list,
        search=search,
        role_filter=role_filter,
        status_filter=status_filter
    )


@admin_bp.route('/users/<int:user_id>/revoke', methods=['POST'])
def revoke_user(user_id):
    if user_id == current_user.id:
        flash("You cannot revoke your own administrator account.", "danger")
        return redirect(url_for('admin.users'))

    user = User.query.get_or_404(user_id)
    user.is_active = False
    
    # Revoke all active shares belonging to this user
    Share.query.filter_by(user_id=user.id).update({'is_revoked': True})
    db.session.commit()

    log_audit(
        action='USER_REVOKE',
        status='success',
        user_id=current_user.id,
        details=f"Admin revoked access and invalidates shares for user '{user.email}' (ID: {user.id})"
    )

    flash(f"Access revoked for {user.name} ({user.email}). All active shares have been revoked.", "warning")
    return redirect(request.referrer or url_for('admin.users'))


@admin_bp.route('/users/<int:user_id>/restore', methods=['POST'])
def restore_user(user_id):
    user = User.query.get_or_404(user_id)
    user.is_active = True
    user.reset_failed_attempts()
    db.session.commit()

    log_audit(
        action='USER_RESTORE',
        status='success',
        user_id=current_user.id,
        details=f"Admin restored access for user '{user.email}' (ID: {user.id})"
    )

    flash(f"Access restored for {user.name} ({user.email}).", "success")
    return redirect(request.referrer or url_for('admin.users'))


@admin_bp.route('/users/<int:user_id>/delete', methods=['POST'])
def delete_user(user_id):
    if user_id == current_user.id:
        flash("You cannot delete your own administrator account.", "danger")
        return redirect(url_for('admin.users'))

    user = User.query.get_or_404(user_id)
    user_email = user.email

    # Remove all encrypted documents owned by user from disk
    for doc in user.documents:
        filepath = os.path.join(current_app.config['UPLOAD_FOLDER'], doc.stored_filename)
        delete_file(filepath)

    db.session.delete(user)
    db.session.commit()

    log_audit(
        action='USER_DELETE',
        status='success',
        user_id=current_user.id,
        details=f"Admin deleted user '{user_email}' and all associated files."
    )

    flash(f"User {user_email} and all owned documents were permanently deleted.", "info")
    return redirect(url_for('admin.users'))


@admin_bp.route('/documents')
def documents():
    search = request.args.get('q', '').strip()
    query = Document.query

    if search:
        query = query.join(User, Document.owner_id == User.id).filter(
            (Document.title.ilike(f'%{search}%')) |
            (Document.original_filename.ilike(f'%{search}%')) |
            (User.email.ilike(f'%{search}%')) |
            (User.name.ilike(f'%{search}%'))
        )

    all_docs = query.order_by(Document.created_at.desc()).all()
    return render_template('admin/documents.html', documents=all_docs, search=search)


@admin_bp.route('/documents/<doc_id>/delete', methods=['POST'])
def delete_document(doc_id):
    doc = Document.query.get_or_404(doc_id)
    filepath = os.path.join(current_app.config['UPLOAD_FOLDER'], doc.stored_filename)
    delete_file(filepath)

    title = doc.title
    db.session.delete(doc)
    db.session.commit()

    log_audit(
        action='DELETE_DOCUMENT',
        status='success',
        user_id=current_user.id,
        details=f"Admin deleted document '{title}' (UUID: {doc_id})"
    )

    flash(f"Document '{title}' deleted by administrator.", "info")
    return redirect(url_for('admin.documents'))


@admin_bp.route('/audit')
def audit_trail():
    page = request.args.get('page', 1, type=int)
    per_page = 25

    action_filter = request.args.get('action', '').strip()
    status_filter = request.args.get('status', '').strip()
    user_id_filter = request.args.get('user_id', type=int)
    search_query = request.args.get('q', '').strip()
    date_from = request.args.get('date_from', '').strip()
    date_to = request.args.get('date_to', '').strip()

    query = AuditLog.query

    if action_filter:
        query = query.filter_by(action=action_filter)
    if status_filter:
        query = query.filter_by(status=status_filter)
    if user_id_filter:
        query = query.filter_by(user_id=user_id_filter)
    if search_query:
        query = query.outerjoin(User, AuditLog.user_id == User.id).filter(
            (AuditLog.details.ilike(f'%{search_query}%')) |
            (AuditLog.ip_address.ilike(f'%{search_query}%')) |
            (AuditLog.action.ilike(f'%{search_query}%')) |
            (User.email.ilike(f'%{search_query}%')) |
            (User.name.ilike(f'%{search_query}%'))
        )
    if date_from:
        try:
            df = datetime.strptime(date_from, '%Y-%m-%d')
            query = query.filter(AuditLog.timestamp >= df)
        except ValueError:
            pass
    if date_to:
        try:
            dt = datetime.strptime(date_to, '%Y-%m-%d') + timedelta(days=1)
            query = query.filter(AuditLog.timestamp < dt)
        except ValueError:
            pass

    pagination = query.order_by(AuditLog.timestamp.desc()).paginate(page=page, per_page=per_page, error_out=False)

    # Distinct action types for filter dropdown
    distinct_actions = [
        r[0] for r in db.session.query(AuditLog.action).distinct().order_by(AuditLog.action).all()
    ]

    return render_template(
        'admin/audit.html',
        pagination=pagination,
        logs=pagination.items,
        distinct_actions=distinct_actions,
        action_filter=action_filter,
        status_filter=status_filter,
        user_id_filter=user_id_filter,
        search_query=search_query,
        date_from=date_from,
        date_to=date_to
    )


@admin_bp.route('/audit/export')
def export_audit_csv():
    action_filter = request.args.get('action', '').strip()
    status_filter = request.args.get('status', '').strip()
    user_id_filter = request.args.get('user_id', type=int)
    search_query = request.args.get('q', '').strip()
    date_from = request.args.get('date_from', '').strip()
    date_to = request.args.get('date_to', '').strip()

    query = AuditLog.query

    if action_filter:
        query = query.filter_by(action=action_filter)
    if status_filter:
        query = query.filter_by(status=status_filter)
    if user_id_filter:
        query = query.filter_by(user_id=user_id_filter)
    if search_query:
        query = query.outerjoin(User, AuditLog.user_id == User.id).filter(
            (AuditLog.details.ilike(f'%{search_query}%')) |
            (AuditLog.ip_address.ilike(f'%{search_query}%')) |
            (AuditLog.action.ilike(f'%{search_query}%')) |
            (User.email.ilike(f'%{search_query}%'))
        )
    if date_from:
        try:
            df = datetime.strptime(date_from, '%Y-%m-%d')
            query = query.filter(AuditLog.timestamp >= df)
        except ValueError:
            pass
    if date_to:
        try:
            dt = datetime.strptime(date_to, '%Y-%m-%d') + timedelta(days=1)
            query = query.filter(AuditLog.timestamp < dt)
        except ValueError:
            pass

    logs = query.order_by(AuditLog.timestamp.desc()).all()

    # Create CSV in memory
    si = io.StringIO()
    writer = csv.writer(si)
    writer.writerow([
        'ID',
        'Timestamp (UTC)',
        'User Email',
        'User Name',
        'Document Title',
        'Document ID',
        'Action',
        'Status',
        'IP Address',
        'User Agent',
        'Details'
    ])

    for log in logs:
        user_email = log.user.email if log.user else 'Anonymous/Unauthenticated'
        user_name = log.user.name if log.user else 'N/A'
        doc_title = log.document.title if log.document else 'N/A'
        writer.writerow([
            log.id,
            log.timestamp.strftime('%Y-%m-%d %H:%M:%S UTC'),
            user_email,
            user_name,
            doc_title,
            log.document_id or 'N/A',
            log.action,
            log.status,
            log.ip_address or 'N/A',
            log.user_agent or 'N/A',
            log.details or ''
        ])

    output = si.getvalue()
    filename = f"securedocs_audit_log_{utc_now().strftime('%Y%m%d_%H%M%S')}.csv"

    return Response(
        output,
        mimetype="text/csv",
        headers={"Content-Disposition": f"attachment;filename={filename}"}
    )
