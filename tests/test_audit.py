import csv
import io
from app.models import AuditLog
from app.utils.audit import log_audit


def test_audit_logs_created_for_document_actions(client, regular_user_alice, sample_document):
    client.post('/auth/login', data={'email': 'alice@test.local', 'password': 'AlicePass123!'})

    # View
    client.get(f'/documents/{sample_document.id}/view')
    view_log = AuditLog.query.filter_by(
        user_id=regular_user_alice.id,
        document_id=sample_document.id,
        action='VIEW',
        status='success'
    ).first()
    assert view_log is not None
    assert view_log.ip_address is not None

    # Download
    client.get(f'/documents/{sample_document.id}/download')
    download_log = AuditLog.query.filter_by(
        user_id=regular_user_alice.id,
        document_id=sample_document.id,
        action='DOWNLOAD',
        status='success'
    ).first()
    assert download_log is not None


def test_audit_trail_export_csv(client, admin_user, regular_user_alice, sample_document):
    # Log an action
    log_audit('TEST_ACTION', status='success', user=regular_user_alice, document=sample_document, details="Test Export Details")

    # Log in as admin
    client.post('/auth/login', data={'email': 'admin@test.local', 'password': 'AdminPass123!'})

    response = client.get('/admin/audit/export')
    assert response.status_code == 200
    assert response.content_type == 'text/csv; charset=utf-8'

    csv_data = response.data.decode('utf-8')
    reader = csv.reader(io.StringIO(csv_data))
    rows = list(reader)

    # Check headers
    headers = rows[0]
    assert 'Timestamp (UTC)' in headers
    assert 'User Email' in headers
    assert 'Action' in headers
    assert 'Status' in headers
    assert 'IP Address' in headers

    # Verify our action is present
    action_found = any('TEST_ACTION' in row for row in rows)
    assert action_found is True
