import re
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, BooleanField, SubmitField
from wtforms.validators import DataRequired, Length, EqualTo, ValidationError, Regexp
from app.models import User

EMAIL_REGEX = r'^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$'
EMAIL_MESSAGE = "Please enter a valid email address."


class LoginForm(FlaskForm):
    email = StringField('Email Address', validators=[
        DataRequired(message="Email is required."),
        Regexp(EMAIL_REGEX, message=EMAIL_MESSAGE)
    ])
    password = PasswordField('Password', validators=[
        DataRequired(message="Password is required.")
    ])
    remember_me = BooleanField('Remember Me')
    submit = SubmitField('Sign In')


class RegisterForm(FlaskForm):
    name = StringField('Full Name', validators=[
        DataRequired(message="Full name is required."),
        Length(min=2, max=100, message="Name must be between 2 and 100 characters.")
    ])
    email = StringField('Email Address', validators=[
        DataRequired(message="Email is required."),
        Regexp(EMAIL_REGEX, message=EMAIL_MESSAGE),
        Length(max=120)
    ])
    password = PasswordField('Password', validators=[
        DataRequired(message="Password is required."),
        Length(min=8, message="Password must be at least 8 characters long.")
    ])
    password_confirm = PasswordField('Confirm Password', validators=[
        DataRequired(message="Please confirm your password."),
        EqualTo('password', message="Passwords must match.")
    ])
    submit = SubmitField('Create Account')

    def validate_email(self, field):
        user = User.query.filter_by(email=field.data.strip().lower()).first()
        if user:
            raise ValidationError("This email address is already registered.")

    def validate_password(self, field):
        pwd = field.data
        if not re.search(r'[A-Z]', pwd):
            raise ValidationError("Password must contain at least one uppercase letter (A-Z).")
        if not re.search(r'[a-z]', pwd):
            raise ValidationError("Password must contain at least one lowercase letter (a-z).")
        if not re.search(r'[0-9]', pwd):
            raise ValidationError("Password must contain at least one number (0-9).")
        if not re.search(r'[^A-Za-z0-9]', pwd):
            raise ValidationError("Password must contain at least one special character (!@#$%^&* etc.).")

