import io
import os
from app.models import Document, AuditLog
from app.extensions import db
from app.utils.encryption import read_decrypted_file


def test_document_upload_and_encryption_at_rest(client, regular_user_alice, test_app):
    # Log in as Alice
    client.post('/auth/login', data={'email': 'alice@test.local', 'password': 'AlicePass123!'})

    file_content = b"Confidential client agreement 2026."
    data = {
        'title': 'Client Agreement',
        'description': 'Master service agreement',
        'document_file': (io.BytesIO(file_content), 'agreement.txt')
    }

    response = client.post('/documents/upload', data=data, content_type='multipart/form-data', follow_redirects=True)
    assert response.status_code == 200
    assert b"successfully encrypted and uploaded" in response.data

    doc = Document.query.filter_by(title='Client Agreement').first()
    assert doc is not None
    assert doc.owner_id == regular_user_alice.id
    assert doc.size == len(file_content)

    # Verify on-disk file is ciphertext (not equal to file_content)
    filepath = os.path.join(test_app.config['UPLOAD_FOLDER'], doc.stored_filename)
    assert os.path.exists(filepath)
    with open(filepath, 'rb') as f:
        disk_bytes = f.read()
    assert disk_bytes != file_content
    assert disk_bytes.startswith(b'gAAAAA')  # Standard Fernet token prefix

    # Verify decryption utility recovers original content
    decrypted = read_decrypted_file(filepath)
    assert decrypted == file_content


def test_document_download_decryption(client, regular_user_alice, sample_document):
    # Log in as Alice
    client.post('/auth/login', data={'email': 'alice@test.local', 'password': 'AlicePass123!'})

    response = client.get(f'/documents/{sample_document.id}/download')
    assert response.status_code == 200
    assert response.data == b"TOP SECRET FINANCIAL REPORT"
    assert "attachment" in response.headers.get("Content-Disposition", "")


def test_document_view_inline(client, regular_user_alice, sample_document):
    # Log in as Alice
    client.post('/auth/login', data={'email': 'alice@test.local', 'password': 'AlicePass123!'})

    response = client.get(f'/documents/{sample_document.id}/view')
    assert response.status_code == 200
    assert response.data == b"TOP SECRET FINANCIAL REPORT"
    assert "inline" in response.headers.get("Content-Disposition", "") or response.headers.get("Content-Disposition") is None


def test_document_replacement(client, regular_user_alice, sample_document, test_app):
    client.post('/auth/login', data={'email': 'alice@test.local', 'password': 'AlicePass123!'})

    new_content = b"REVISED FINANCIAL STATEMENTS - VERSION 2"
    response = client.post(
        f'/documents/{sample_document.id}/replace',
        data={'document_file': (io.BytesIO(new_content), 'Revised_Q4.txt')},
        content_type='multipart/form-data',
        follow_redirects=True
    )
    assert response.status_code == 200
    assert b"successfully updated and re-encrypted" in response.data

    filepath = os.path.join(test_app.config['UPLOAD_FOLDER'], sample_document.stored_filename)
    decrypted = read_decrypted_file(filepath)
    assert decrypted == new_content


def test_document_deletion(client, regular_user_alice, sample_document, test_app):
    client.post('/auth/login', data={'email': 'alice@test.local', 'password': 'AlicePass123!'})

    filepath = os.path.join(test_app.config['UPLOAD_FOLDER'], sample_document.stored_filename)
    assert os.path.exists(filepath)

    response = client.post(f'/documents/{sample_document.id}/delete', follow_redirects=True)
    assert response.status_code == 200
    assert b"has been permanently deleted" in response.data

    # File must be deleted from storage
    assert not os.path.exists(filepath)
    assert db.session.get(Document, sample_document.id) is None
