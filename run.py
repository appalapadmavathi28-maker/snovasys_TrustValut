import os
from app import create_app, db
from app.models import User, Document, Share, AuditLog

app = create_app(os.environ.get('FLASK_CONFIG', 'default'))


@app.shell_context_processor
def make_shell_context():
    return {
        'db': db,
        'User': User,
        'Document': Document,
        'Share': Share,
        'AuditLog': AuditLog
    }


# Ensure tables exist when starting application
with app.app_context():
    db.create_all()

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    print(f" * SecureDocs server starting on http://localhost:{port} and http://127.0.0.1:{port}")
    app.run(host='0.0.0.0', port=port, debug=False)
