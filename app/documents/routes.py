import os
import io
import mimetypes
import uuid
from datetime import datetime, timezone
from werkzeug.utils import secure_filename
from flask import (
    render_template, redirect, url_for, flash, request, abort,
    send_file, current_app
)
from flask_login import login_required, current_user
from app.extensions import db
from app.documents import documents_bp
from app.documents.forms import UploadDocumentForm, ReplaceDocumentForm, ShareDocumentForm
from app.models import Document, Share, User, AuditLog, utc_now
from app.utils.encryption import save_encrypted_file, read_decrypted_file, delete_file
from app.utils.audit import log_audit
from app.utils.decorators import document_access_required


def get_safe_mimetype(filename, upload_mimetype=None):
    guessed_type, _ = mimetypes.guess_type(filename)
    if guessed_type:
        return guessed_type
    if upload_mimetype and upload_mimetype != 'application/octet-stream':
        return upload_mimetype
    return 'application/octet-stream'


@documents_bp.route('/')
@login_required
def dashboard():
    owned_count = Document.query.filter_by(owner_id=current_user.id).count()
    
    # Active shares received
    now_naive = utc_now().replace(tzinfo=None)
    shared_query = Share.query.filter(
        Share.user_id == current_user.id,
        Share.is_revoked == False
    )
    # Filter non-expired shares
    shared_list = [s for s in shared_query.all() if not s.is_expired()]
    shared_count = len(shared_list)

    # Recent activity for current user
    recent_logs = AuditLog.query.filter_by(user_id=current_user.id)\
        .order_by(AuditLog.timestamp.desc())\
        .limit(8).all()

    # Recent documents owned
    recent_docs = Document.query.filter_by(owner_id=current_user.id)\
        .order_by(Document.created_at.desc())\
        .limit(5).all()

    return render_template(
        'documents/dashboard.html',
        owned_count=owned_count,
        shared_count=shared_count,
        recent_logs=recent_logs,
        recent_docs=recent_docs
    )


@documents_bp.route('/documents/my-docs')
@login_required
def my_documents():
    search_query = request.args.get('q', '').strip()
    query = Document.query.filter_by(owner_id=current_user.id)

    if search_query:
        query = query.filter(
            (Document.title.ilike(f'%{search_query}%')) |
            (Document.description.ilike(f'%{search_query}%')) |
            (Document.original_filename.ilike(f'%{search_query}%'))
        )

    documents = query.order_by(Document.created_at.desc()).all()
    return render_template('documents/my_documents.html', documents=documents, search_query=search_query)


@documents_bp.route('/documents/shared-with-me')
@login_required
def shared_with_me():
    search_query = request.args.get('q', '').strip()
    shares_query = Share.query.filter_by(user_id=current_user.id, is_revoked=False)
    
    all_shares = shares_query.all()
    active_shares = [s for s in all_shares if not s.is_expired()]

    if search_query:
        active_shares = [
            s for s in active_shares
            if search_query.lower() in s.document.title.lower() or
               search_query.lower() in (s.document.description or '').lower() or
               search_query.lower() in s.document.owner.name.lower()
        ]

    return render_template('documents/shared_with_me.html', shares=active_shares, search_query=search_query)


@documents_bp.route('/documents/upload', methods=['GET', 'POST'])
@login_required
def upload():
    form = UploadDocumentForm()
    if form.validate_on_submit():
        file = form.document_file.data
        orig_filename = secure_filename(file.filename)
        if not orig_filename:
            orig_filename = f"document_{uuid.uuid4().hex[:8]}"

        doc_id = str(uuid.uuid4())
        stored_filename = f"{doc_id}.enc"
        target_path = os.path.join(current_app.config['UPLOAD_FOLDER'], stored_filename)

        # Detect MIME
        mime_type = get_safe_mimetype(orig_filename, file.content_type)

        # Encrypt file at rest
        file_size = save_encrypted_file(file, target_path)

        # Save document metadata in DB
        document = Document(
            id=doc_id,
            title=form.title.data.strip(),
            description=form.description.data.strip() if form.description.data else None,
            original_filename=orig_filename,
            stored_filename=stored_filename,
            mime_type=mime_type,
            size=file_size,
            owner_id=current_user.id
        )
        db.session.add(document)
        db.session.commit()

        log_audit(
            action='UPLOAD',
            status='success',
            user_id=current_user.id,
            document_id=doc_id,
            details=f"Uploaded document '{document.title}' ({document.original_filename}, {document.formatted_size})"
        )

        flash(f"Document '{document.title}' successfully encrypted and uploaded!", "success")
        return redirect(url_for('documents.document_detail', doc_id=doc_id))

    return render_template('documents/upload.html', form=form)


@documents_bp.route('/documents/<doc_id>')
@login_required
@document_access_required(permission='view')
def document_detail(doc_id):
    document = Document.query.get_or_404(doc_id)
    is_owner = (document.owner_id == current_user.id)
    is_admin = current_user.is_admin()
    can_manage = is_owner or is_admin

    # Check user's specific permission
    user_permission = 'edit' if can_manage else None
    user_share = None
    if not can_manage:
        user_share = Share.query.filter_by(document_id=doc_id, user_id=current_user.id).first()
        if user_share and user_share.is_valid():
            user_permission = user_share.permission

    # Forms for owner / admin
    share_form = ShareDocumentForm() if can_manage else None
    replace_form = ReplaceDocumentForm() if (can_manage or user_permission == 'edit') else None

    # Fetch shares & per-document audit trail if manager
    shares = []
    audit_logs = []
    if can_manage:
        shares = Share.query.filter_by(document_id=doc_id).order_by(Share.created_at.desc()).all()
        audit_logs = AuditLog.query.filter_by(document_id=doc_id).order_by(AuditLog.timestamp.desc()).limit(30).all()

    return render_template(
        'documents/detail.html',
        document=document,
        is_owner=is_owner,
        is_admin=is_admin,
        can_manage=can_manage,
        user_permission=user_permission,
        user_share=user_share,
        share_form=share_form,
        replace_form=replace_form,
        shares=shares,
        audit_logs=audit_logs
    )


@documents_bp.route('/documents/<doc_id>/view')
@login_required
@document_access_required(permission='view')
def view_document(doc_id):
    document = Document.query.get_or_404(doc_id)
    filepath = os.path.join(current_app.config['UPLOAD_FOLDER'], document.stored_filename)

    try:
        decrypted_data = read_decrypted_file(filepath)
    except FileNotFoundError:
        flash("Encrypted file not found on server storage.", "danger")
        return redirect(url_for('documents.document_detail', doc_id=doc_id))

    log_audit(
        action='VIEW',
        status='success',
        user_id=current_user.id,
        document_id=document.id,
        details=f"Viewed encrypted document '{document.title}' ({document.original_filename})"
    )

    return send_file(
        io.BytesIO(decrypted_data),
        mimetype=document.mime_type,
        as_attachment=False,
        download_name=document.original_filename
    )


@documents_bp.route('/documents/<doc_id>/download')
@login_required
@document_access_required(permission='download')
def download_document(doc_id):
    document = Document.query.get_or_404(doc_id)
    filepath = os.path.join(current_app.config['UPLOAD_FOLDER'], document.stored_filename)

    try:
        decrypted_data = read_decrypted_file(filepath)
    except FileNotFoundError:
        flash("Encrypted file not found on server storage.", "danger")
        return redirect(url_for('documents.document_detail', doc_id=doc_id))

    log_audit(
        action='DOWNLOAD',
        status='success',
        user_id=current_user.id,
        document_id=document.id,
        details=f"Downloaded decrypted document '{document.title}' ({document.original_filename})"
    )

    return send_file(
        io.BytesIO(decrypted_data),
        mimetype=document.mime_type,
        as_attachment=True,
        download_name=document.original_filename
    )


@documents_bp.route('/documents/<doc_id>/replace', methods=['POST'])
@login_required
@document_access_required(permission='edit')
def replace_document(doc_id):
    document = Document.query.get_or_404(doc_id)
    form = ReplaceDocumentForm()

    if form.validate_on_submit():
        file = form.document_file.data
        orig_filename = secure_filename(file.filename)
        if not orig_filename:
            orig_filename = f"replaced_{uuid.uuid4().hex[:8]}"

        target_path = os.path.join(current_app.config['UPLOAD_FOLDER'], document.stored_filename)
        
        # Save new encrypted version to disk
        new_size = save_encrypted_file(file, target_path)
        new_mime = get_safe_mimetype(orig_filename, file.content_type)

        document.original_filename = orig_filename
        document.mime_type = new_mime
        document.size = new_size
        document.updated_at = utc_now()
        db.session.commit()

        log_audit(
            action='EDIT_DOCUMENT',
            status='success',
            user_id=current_user.id,
            document_id=document.id,
            details=f"Replaced document contents with '{orig_filename}' ({document.formatted_size})"
        )

        flash("Document successfully updated and re-encrypted!", "success")
    else:
        for field, errors in form.errors.items():
            for err in errors:
                flash(f"Error updating file: {err}", "danger")

    return redirect(url_for('documents.document_detail', doc_id=doc_id))


@documents_bp.route('/documents/<doc_id>/delete', methods=['POST'])
@login_required
def delete_document(doc_id):
    document = Document.query.get_or_404(doc_id)
    if not (document.owner_id == current_user.id or current_user.is_admin()):
        log_audit(
            action='UNAUTHORIZED_ACCESS',
            status='denied',
            user_id=current_user.id,
            document_id=document.id,
            details=f"Unauthorized attempt to delete document '{document.title}'"
        )
        abort(403)

    filepath = os.path.join(current_app.config['UPLOAD_FOLDER'], document.stored_filename)
    delete_file(filepath)

    doc_title = document.title
    db.session.delete(document)
    db.session.commit()

    log_audit(
        action='DELETE_DOCUMENT',
        status='success',
        user_id=current_user.id,
        details=f"Deleted document '{doc_title}' (UUID: {doc_id})"
    )

    flash(f"Document '{doc_title}' has been permanently deleted.", "info")
    return redirect(url_for('documents.my_documents'))


@documents_bp.route('/documents/<doc_id>/share', methods=['POST'])
@login_required
def share_document(doc_id):
    document = Document.query.get_or_404(doc_id)
    if not (document.owner_id == current_user.id or current_user.is_admin()):
        abort(403)

    form = ShareDocumentForm()
    if form.validate_on_submit():
        recipient_identifier = form.recipient.data.strip()
        recipient = User.query.filter(
            (User.email.ilike(recipient_identifier)) |
            (User.name.ilike(recipient_identifier))
        ).first()

        if not recipient:
            flash(f"No user found with identifier '{recipient_identifier}'.", "danger")
            return redirect(url_for('documents.document_detail', doc_id=doc_id))

        if recipient.id == document.owner_id:
            flash("You cannot share a document with its owner.", "warning")
            return redirect(url_for('documents.document_detail', doc_id=doc_id))

        # Check existing share
        existing_share = Share.query.filter_by(
            document_id=doc_id,
            user_id=recipient.id
        ).first()

        expires = form.expires_at.data
        if expires and expires.tzinfo:
            expires = expires.astimezone(timezone.utc).replace(tzinfo=None)

        if existing_share:
            existing_share.permission = form.permission.data
            existing_share.expires_at = expires
            existing_share.is_revoked = False
            action_name = 'SHARE_UPDATE'
            msg = f"Updated share permissions for {recipient.email} ({form.permission.data})."
        else:
            new_share = Share(
                document_id=doc_id,
                user_id=recipient.id,
                created_by_id=current_user.id,
                permission=form.permission.data,
                expires_at=expires,
                is_revoked=False
            )
            db.session.add(new_share)
            action_name = 'SHARE_CREATE'
            msg = f"Document successfully shared with {recipient.email} ({form.permission.data})."

        db.session.commit()

        log_audit(
            action=action_name,
            status='success',
            user_id=current_user.id,
            document_id=doc_id,
            details=f"{action_name} for recipient {recipient.email} with permission '{form.permission.data}'"
        )

        flash(msg, "success")
    else:
        for field, errors in form.errors.items():
            for err in errors:
                flash(f"Share error: {err}", "danger")

    return redirect(url_for('documents.document_detail', doc_id=doc_id))


@documents_bp.route('/shares/<int:share_id>/revoke', methods=['POST'])
@login_required
def revoke_share(share_id):
    share = Share.query.get_or_404(share_id)
    document = share.document

    if not (document.owner_id == current_user.id or current_user.is_admin()):
        abort(403)

    share.is_revoked = True
    db.session.commit()

    recipient_email = share.recipient.email if share.recipient else f"User #{share.user_id}"
    log_audit(
        action='SHARE_REVOKE',
        status='success',
        user_id=current_user.id,
        document_id=document.id,
        details=f"Revoked share access for {recipient_email} on document '{document.title}'"
    )

    flash(f"Access revoked for {recipient_email}.", "info")
    return redirect(url_for('documents.document_detail', doc_id=document.id))
