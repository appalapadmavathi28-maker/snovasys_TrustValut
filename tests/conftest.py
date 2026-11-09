import os
import shutil
import pytest
from app import create_app, db
from app.models import User, Document, Share, AuditLog
from app.utils.encryption import encrypt_data


@pytest.fixture(scope='session')
def test_app():
    test_upload_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'test_uploads'))
    os.makedirs(test_upload_dir, exist_ok=True)

    app = create_app('testing')
    app.config['UPLOAD_FOLDER'] = test_upload_dir
    app.config['WTF_CSRF_ENABLED'] = False

    yield app

    # Cleanup test uploads directory
    if os.path.exists(test_upload_dir):
        shutil.rmtree(test_upload_dir, ignore_errors=True)


@pytest.fixture(scope='function')
def app_context(test_app):
    with test_app.app_context():
        db.create_all()
        yield test_app
        db.session.remove()
        db.drop_all()


@pytest.fixture(scope='function')
def client(app_context):
    return app_context.test_client()


@pytest.fixture(scope='function')
def admin_user(app_context):
    admin = User(name="Admin User", email="admin@test.local", role="admin", is_active=True)
    admin.set_password("AdminPass123!")
    db.session.add(admin)
    db.session.commit()
    return admin


@pytest.fixture(scope='function')
def regular_user_alice(app_context):
    alice = User(name="Alice Vance", email="alice@test.local", role="user", is_active=True)
    alice.set_password("AlicePass123!")
    db.session.add(alice)
    db.session.commit()
    return alice


@pytest.fixture(scope='function')
def regular_user_bob(app_context):
    bob = User(name="Bob Smith", email="bob@test.local", role="user", is_active=True)
    bob.set_password("BobPass123!")
    db.session.add(bob)
    db.session.commit()
    return bob


@pytest.fixture(scope='function')
def unauthorized_user_eve(app_context):
    eve = User(name="Eve Hacker", email="eve@test.local", role="user", is_active=True)
    eve.set_password("EvePass123!")
    db.session.add(eve)
    db.session.commit()
    return eve


@pytest.fixture(scope='function')
def sample_document(app_context, regular_user_alice, test_app):
    doc_id = "test-doc-uuid-999"
    filename = f"{doc_id}.enc"
    filepath = os.path.join(test_app.config['UPLOAD_FOLDER'], filename)
    raw_content = b"TOP SECRET FINANCIAL REPORT"

    with open(filepath, 'wb') as f:
        f.write(encrypt_data(raw_content))

    doc = Document(
        id=doc_id,
        title="Q4 Financials",
        description="Confidential quarterly earnings",
        original_filename="Q4_Financials.txt",
        stored_filename=filename,
        mime_type="text/plain",
        size=len(raw_content),
        owner_id=regular_user_alice.id
    )
    db.session.add(doc)
    db.session.commit()
    return doc
