from app.models import User, Share, Document, AuditLog
from app.extensions import db


def test_non_admin_cannot_access_admin_panel(client, regular_user_alice):
    client.post('/auth/login', data={'email': 'alice@test.local', 'password': 'AlicePass123!'})

    response = client.get('/admin/dashboard')
    assert response.status_code == 403

    # Audit log recorded
    log = AuditLog.query.filter_by(
        user_id=regular_user_alice.id,
        action='UNAUTHORIZED_ACCESS',
        status='denied'
    ).first()
    assert log is not None


def test_admin_dashboard_metrics(client, admin_user, regular_user_alice, sample_document):
    client.post('/auth/login', data={'email': 'admin@test.local', 'password': 'AdminPass123!'})

    response = client.get('/admin/dashboard')
    assert response.status_code == 200
    assert b"Administrative Center" in response.data
    assert b"Registered Users" in response.data


def test_admin_revoke_user_invalidates_shares(client, admin_user, regular_user_bob, sample_document):
    # Grant Bob a share
    share = Share(
        document_id=sample_document.id,
        user_id=regular_user_bob.id,
        permission='download',
        is_revoked=False
    )
    db.session.add(share)
    db.session.commit()

    assert regular_user_bob.is_active is True
    assert share.is_revoked is False

    # Admin revokes Bob
    client.post('/auth/login', data={'email': 'admin@test.local', 'password': 'AdminPass123!'})
    response = client.post(f'/admin/users/{regular_user_bob.id}/revoke', follow_redirects=True)
    assert response.status_code == 200

    # Verify Bob is now inactive
    bob = db.session.get(User, regular_user_bob.id)
    assert bob.is_active is False

    # Verify Bob's share was invalidated
    share_check = db.session.get(Share, share.id)
    assert share_check.is_revoked is True


def test_admin_restore_user(client, admin_user, regular_user_bob):
    regular_user_bob.is_active = False
    db.session.commit()

    client.post('/auth/login', data={'email': 'admin@test.local', 'password': 'AdminPass123!'})
    response = client.post(f'/admin/users/{regular_user_bob.id}/restore', follow_redirects=True)
    assert response.status_code == 200

    bob = db.session.get(User, regular_user_bob.id)
    assert bob.is_active is True


def test_admin_cannot_revoke_self(client, admin_user):
    client.post('/auth/login', data={'email': 'admin@test.local', 'password': 'AdminPass123!'})
    response = client.post(f'/admin/users/{admin_user.id}/revoke', follow_redirects=True)
    assert response.status_code == 200
    assert b"cannot revoke your own administrator account" in response.data

    admin = db.session.get(User, admin_user.id)
    assert admin.is_active is True
