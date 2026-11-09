from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileRequired, FileAllowed
from wtforms import StringField, TextAreaField, SelectField, DateTimeLocalField, SubmitField
from wtforms.validators import DataRequired, Length, Optional

ALLOWED_EXTENSIONS = ['pdf', 'docx', 'xlsx', 'pptx', 'txt', 'png', 'jpg', 'jpeg']


class UploadDocumentForm(FlaskForm):
    title = StringField('Document Title', validators=[
        DataRequired(message="Title is required."),
        Length(max=150, message="Title must not exceed 150 characters.")
    ])
    description = TextAreaField('Description (Optional)', validators=[
        Length(max=500, message="Description must not exceed 500 characters.")
    ])
    document_file = FileField('Select Document', validators=[
        FileRequired(message="Please select a document to upload."),
        FileAllowed(ALLOWED_EXTENSIONS, f"Allowed file types: {', '.join(ALLOWED_EXTENSIONS)}")
    ])
    submit = SubmitField('Upload & Encrypt File')


class ReplaceDocumentForm(FlaskForm):
    document_file = FileField('Select Replacement Document', validators=[
        FileRequired(message="Please select a replacement file."),
        FileAllowed(ALLOWED_EXTENSIONS, f"Allowed file types: {', '.join(ALLOWED_EXTENSIONS)}")
    ])
    submit = SubmitField('Upload & Replace File')


class ShareDocumentForm(FlaskForm):
    recipient = StringField('Recipient Email or Name', validators=[
        DataRequired(message="Recipient identifier is required.")
    ])
    permission = SelectField('Access Permission', choices=[
        ('view', 'View Only (Read-only inline)'),
        ('download', 'View & Download'),
        ('edit', 'Full Access (View, Download, Replace)')
    ], default='view', validators=[DataRequired()])
    expires_at = DateTimeLocalField('Expiry Date & Time (Optional)', format='%Y-%m-%dT%H:%M', validators=[Optional()])
    submit = SubmitField('Share Access')
