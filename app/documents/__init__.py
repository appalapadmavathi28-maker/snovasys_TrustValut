from flask import Blueprint

documents_bp = Blueprint('documents', __name__, template_folder='../templates/documents')

from app.documents import routes
