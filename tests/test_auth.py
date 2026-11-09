from app.models import User, AuditLog
from app.extensions import db


def test_user_registration_success(client, app_context):
    response = client.post('/auth/register', data={
        'name': 'Charlie Brown',
        'email': 'charlie@test.local',
        'password': 'StrongPassword123!',
        'password_confirm': 'StrongPassword123!'
    }, follow_redirects=True)

    assert response.status_code == 200
    assert b"Registration successful" in response.data

    user = User.query.filter_by(email='charlie@test.local').first()
    assert user is not None
    assert user.name == 'Charlie Brown'
    assert user.role == 'user'
    assert user.is_active is True
    assert user.check_password('StrongPassword123!')


def test_user_registration_weak_password(client, app_context):
    # Missing symbol and uppercase
    response = client.post('/auth/register', data={
        'name': 'Weak User',
        'email': 'weak@test.local',
        'password': 'weakpassword1',
        'password_confirm': 'weakpassword1'
    })
    assert b"Password must contain at least one uppercase letter" in response.data
    assert User.query.filter_by(email='weak@test.local').first() is None


def test_user_registration_duplicate_email(client, regular_user_alice):
    response = client.post('/auth/register', data={
        'name': 'Alice Copy',
        'email': 'alice@test.local',
        'password': 'StrongPassword123!',
        'password_confirm': 'StrongPassword123!'
    })
    assert b"This email address is already registered" in response.data


def test_user_login_success(client, regular_user_alice):
    response = client.post('/auth/login', data={
        'email': 'alice@test.local',
        'password': 'AlicePass123!'
    }, follow_redirects=True)

    assert response.status_code == 200
    assert b"Welcome back, Alice Vance!" in response.data


def test_user_login_invalid_password(client, regular_user_alice):
    response = client.post('/auth/login', data={
        'email': 'alice@test.local',
        'password': 'WrongPassword123!'
    }, follow_redirects=True)

    assert response.status_code == 200
    assert b"Invalid email or password" in response.data

    # Verify failed attempt recorded
    user = User.query.filter_by(email='alice@test.local').first()
    assert user.failed_attempts == 1


def test_account_lockout_after_five_failed_attempts(client, regular_user_alice):
    for i in range(5):
        client.post('/auth/login', data={
            'email': 'alice@test.local',
            'password': 'WrongPassword999!'
        })

    user = User.query.filter_by(email='alice@test.local').first()
    assert user.failed_attempts == 5
    assert user.is_locked() is True

    # 6th attempt should return lockout message
    response = client.post('/auth/login', data={
        'email': 'alice@test.local',
        'password': 'AlicePass123!'
    }, follow_redirects=True)

    assert b"account has been temporarily locked" in response.data


def test_revoked_user_cannot_login(client, regular_user_alice):
    # Deactivate / revoke Alice
    regular_user_alice.is_active = False
    db.session.commit()

    response = client.post('/auth/login', data={
        'email': 'alice@test.local',
        'password': 'AlicePass123!'
    }, follow_redirects=True)

    assert response.status_code == 200
    assert b"Your account access has been revoked" in response.data

    # Verify audit log recorded denied login
    denied_log = AuditLog.query.filter_by(user_id=regular_user_alice.id, action='LOGIN_FAILED', status='denied').first()
    assert denied_log is not None
    assert "revoked" in denied_log.details.lower()


def test_user_logout(client, regular_user_alice):
    client.post('/auth/login', data={
        'email': 'alice@test.local',
        'password': 'AlicePass123!'
    })

    response = client.get('/auth/logout', follow_redirects=True)
    assert response.status_code == 200
    assert b"You have been successfully signed out" in response.data
