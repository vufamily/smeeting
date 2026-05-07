"""
Infrastructure Auth: Flask-Auth Integration
Wraps Flask-Login with core User entity.
"""

from flask_login import LoginManager, login_user, logout_user, login_required, current_user, UserMixin
from functools import wraps
from typing import Optional

from core.entities.user import User


class FlaskUser(UserMixin):
    """Flask-Login User wrapper for core User entity."""

    def __init__(self, user: User):
        self._user = user

    @property
    def id(self):
        return str(self._user.id) if self._user.id else None

    @property
    def username(self):
        return self._user.username

    @property
    def email(self):
        return self._user.email

    @property
    def full_name(self):
        return self._user.full_name

    @property
    def role(self):
        return self._user.role

    @property
    def status(self):
        return self._user.status

    @property
    def created_at(self):
        return self._user.created_at

    def is_admin(self):
        return self._user.is_admin()

    def is_approved(self):
        return self._user.is_approved()

    def is_active(self):
        return self._user.is_active()

    def get_id(self):
        return str(self._user.id)

    @staticmethod
    def from_user(user: User):
        return FlaskUser(user)


def init_flask_login(app, user_loader_fn):
    """Initialize Flask-Login with the app."""
    login_manager = LoginManager()
    login_manager.init_app(app)
    login_manager.login_view = 'login'
    login_manager.login_message = 'Please log in to access this page.'

    @login_manager.user_loader
    def load_user(user_id):
        return user_loader_fn(int(user_id))

    return login_manager


def approved_required(f):
    """Decorator requiring user to be approved."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        from flask import redirect, url_for, flash, request, jsonify
        from flask_login import current_user

        if not current_user.is_authenticated:
            from flask_login import current_user
            from flask_login import LoginManager
            lm = LoginManager()
            # Will be set by app context
            return lm.unauthorized()

        if current_user.status != 'approved':
            if request.is_json:
                return jsonify({'error': 'Your account is not approved. Please contact administrator.'}), 403
            flash('Your account is not approved. Please contact administrator.', 'warning')
            return redirect(url_for('index'))
        return f(*args, **kwargs)
    return decorated_function


def admin_required(f):
    """Decorator requiring user to be admin."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        from flask import redirect, url_for, flash, request, jsonify
        from flask_login import current_user

        if not current_user.is_authenticated:
            from flask_login import LoginManager
            return LoginManager().unauthorized()

        if not current_user.is_admin():
            if request.is_json:
                return jsonify({'error': 'Admin access required.'}), 403
            flash('Admin access required.', 'danger')
            return redirect(url_for('index'))
        return f(*args, **kwargs)
    return decorated_function
