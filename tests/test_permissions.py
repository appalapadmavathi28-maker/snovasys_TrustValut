from datetime import timedelta
from app.models import Share, AuditLog, utc_now
from app.extensions import db


def test_unauthorized_access_returns_403_and_logs_audit(client, unauthorized_user_eve, sample_document):
    # Eve logs in and attempts to access Alice's document without permission
    client.post('/auth/login', data={'email': 'eve@test.local', 'password': 'EvePass123!'})

    response = client.get(f'/documents/{sample_document.id}')
    assert response.status_code == 403

    # Verify audit log was recorded
    audit_log = AuditLog.query.filter_by(
        user_id=unauthorized_user_eve.id,
        document_id=sample_document.id,
        action='UNAUTHORIZED_ACCESS',
        status='denied'
    ).first()
    assert audit_log is not None
    assert "Unauthorized" in audit_log.details


def test_view_only_permission_enforcement(client, regular_user_bob, sample_document):
    # Grant Bob View-Only access
    share = Share(
        document_id=sample_document.id,
        user_id=regular_user_bob.id,
        permission='view',
        is_revoked=False
    )
    db.session.add(share)
    db.session.commit()

    client.post('/auth/login', data={'email': 'bob@test.local', 'password': 'BobPass123!'})

    # Bob can view document details and inline view
    detail_res = client.get(f'/documents/{sample_document.id}')
    assert detail_res.status_code == 200

    view_res = client.get(f'/documents/{sample_document.id}/view')
    assert view_res.status_code == 200
    assert view_res.data == b"TOP SECRET FINANCIAL REPORT"

    # Bob cannot download (should return 403)
    download_res = client.get(f'/documents/{sample_document.id}/download')
    assert download_res.status_code == 403

    # Check that unauthorized download attempt was logged
    denied_download_log = AuditLog.query.filter_by(
        user_id=regular_user_bob.id,
        document_id=sample_document.id,
        action='UNAUTHORIZED_ACCESS',
        status='denied'
    ).first()
    assert denied_download_log is not None


def test_download_permission_enforcement(client, regular_user_bob, sample_document):
    # Grant Bob Download permission
    share = Share(
        document_id=sample_document.id,
        user_id=regular_user_bob.id,
        permission='download',
        is_revoked=False
    )
    db.session.add(share)
    db.session.commit()

    client.post('/auth/login', data={'email': 'bob@test.local', 'password': 'BobPass123!'})

    download_res = client.get(f'/documents/{sample_document.id}/download')
    assert download_res.status_code == 200
    assert download_res.data == b"TOP SECRET FINANCIAL REPORT"


def test_expired_share_returns_403(client, regular_user_bob, sample_document):
    # Share expired in the past
    past_time = (utc_now() - timedelta(days=2)).replace(tzinfo=None)
    share = Share(
        document_id=sample_document.id,
        user_id=regular_user_bob.id,
        permission='download',
        expires_at=past_time,
        is_revoked=False
    )
    db.session.add(share)
    db.session.commit()

    client.post('/auth/login', data={'email': 'bob@test.local', 'password': 'BobPass123!'})

    response = client.get(f'/documents/{sample_document.id}/download')
    assert response.status_code == 403


def test_revoked_share_returns_403(client, regular_user_bob, sample_document):
    share = Share(
        document_id=sample_document.id,
        user_id=regular_user_bob.id,
        permission='download',
        is_revoked=True
    )
    db.session.add(share)
    db.session.commit()

    client.post('/auth/login', data={'email': 'bob@test.local', 'password': 'BobPass123!'})

    response = client.get(f'/documents/{sample_document.id}/download')
    assert response.status_code == 403


def test_admin_has_override_access(client, admin_user, sample_document):
    # Admin is not the owner and has no share, but has system-wide override
    client.post('/auth/login', data={'email': 'admin@test.local', 'password': 'AdminPass123!'})

    response = client.get(f'/documents/{sample_document.id}')
    assert response.status_code == 200

    download_res = client.get(f'/documents/{sample_document.id}/download')
    assert download_res.status_code == 200
    assert download_res.data == b"TOP SECRET FINANCIAL REPORT"
