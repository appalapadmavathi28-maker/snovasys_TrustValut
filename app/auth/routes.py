from datetime import datetime, timezone
from urllib.parse import urlparse
from flask import render_template, redirect, url_for, flash, request
from flask_login import login_user, logout_user, login_required, current_user
from app.extensions import db, limiter
from app.auth import auth_bp
from app.auth.forms import LoginForm, RegisterForm
from app.models import User, utc_now
from app.utils.audit import log_audit


def is_safe_url(target):
    if not target:
        return False
    ref_url = urlparse(request.host_url)
    test_url = urlparse(target)
    return test_url.scheme in ('http', 'https') and ref_url.netloc == test_url.netloc


@auth_bp.route('/login', methods=['GET', 'POST'])
@limiter.limit("20 per minute")
def login():
    if current_user.is_authenticated:
        return redirect(url_for('documents.dashboard'))

    form = LoginForm()
    if form.validate_on_submit():
        email = form.email.data.strip().lower()
        password = form.password.data
        user = User.query.filter_by(email=email).first()

        if user:
            # Check lockout
            if user.is_locked():
                log_audit(
                    action='LOGIN_FAILED',
                    status='denied',
                    user_id=user.id,
                    details=f"Login attempt while account is locked until {user.locked_until}"
                )
                flash("Your account has been temporarily locked due to multiple failed login attempts. Please try again later or contact an administrator.", "danger")
                return render_template('auth/login.html', form=form)

            # Check if user is active / revoked
            if not user.is_active:
                log_audit(
                    action='LOGIN_FAILED',
                    status='denied',
                    user_id=user.id,
                    details="Access attempt by revoked user account"
                )
                flash("Your account access has been revoked. Please contact the system administrator.", "danger")
                return render_template('auth/login.html', form=form)

            # Check password
            if user.check_password(password):
                user.reset_failed_attempts()
                user.last_login = utc_now()
                db.session.commit()

                login_user(user, remember=form.remember_me.data)

                log_audit(
                    action='LOGIN_SUCCESS',
                    status='success',
                    user_id=user.id,
                    details=f"User {user.email} logged in successfully"
                )

                flash(f"Welcome back, {user.name}!", "success")
                next_page = request.args.get('next')
                if next_page and is_safe_url(next_page):
                    return redirect(next_page)
                return redirect(url_for('documents.dashboard'))
            else:
                user.record_failed_attempt(max_attempts=5, lockout_minutes=15)
                db.session.commit()

                if user.is_locked():
                    log_audit(
                        action='ACCOUNT_LOCKED',
                        status='denied',
                        user_id=user.id,
                        details="Account locked after 5 consecutive failed login attempts"
                    )
                    flash("Account locked after 5 consecutive failed login attempts. Please try again in 15 minutes.", "danger")
                else:
                    remaining = 5 - user.failed_attempts
                    log_audit(
                        action='LOGIN_FAILED',
                        status='denied',
                        user_id=user.id,
                        details=f"Invalid password. Failed attempt {user.failed_attempts}/5"
                    )
                    flash(f"Invalid email or password. {remaining} attempt(s) remaining before account lockout.", "danger")
        else:
            log_audit(
                action='LOGIN_FAILED',
                status='denied',
                details=f"Login attempt with unregistered email: {email}"
            )
            flash("Invalid email or password.", "danger")

    return render_template('auth/login.html', form=form)


@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('documents.dashboard'))

    form = RegisterForm()
    if form.validate_on_submit():
        user = User(
            name=form.name.data.strip(),
            email=form.email.data.strip().lower(),
            role='user',
            is_active=True
        )
        user.set_password(form.password.data)
        db.session.add(user)
        db.session.commit()

        log_audit(
            action='REGISTER',
            status='success',
            user_id=user.id,
            details=f"New user registered: {user.email}"
        )

        flash("Registration successful! You may now sign in.", "success")
        return redirect(url_for('auth.login'))

    return render_template('auth/register.html', form=form)


@auth_bp.route('/logout', methods=['GET', 'POST'])
@login_required
def logout():
    uid = current_user.id
    email = current_user.email
    logout_user()
    log_audit(
        action='LOGOUT',
        status='success',
        user_id=uid,
        details=f"User {email} logged out"
    )
    flash("You have been successfully signed out.", "info")
    return redirect(url_for('auth.login'))
