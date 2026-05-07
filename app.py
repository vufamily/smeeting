"""
Meeting Assistant - Flask Server with Clean Architecture
Minimal app.py that registers route blueprints.
Business logic lives in core/services and infrastructure/.
"""

import os

from flask import Flask, redirect, url_for, flash, request, jsonify
from flask_login import LoginManager, login_required, current_user, UserMixin

from routes.auth_routes import auth_bp as auth_blueprint
from routes.admin_routes import admin_bp as admin_blueprint
from routes.meeting_routes import meeting_bp as meeting_blueprint

# =============================================================================
# FLASK APP SETUP
# =============================================================================

app = Flask(__name__,
            template_folder='templates',
            static_folder='static')

app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'meeting-assistant-secret-key-change-in-production')
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['MAX_CONTENT_LENGTH'] = 500 * 1024 * 1024  # 500MB max
app.config['DATABASE'] = 'data/meeting.db'

os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
os.makedirs('data', exist_ok=True)

# =============================================================================
# SERVICES (initialized here to avoid circular imports)
# =============================================================================

from infrastructure.database import SQLiteConnection, init_database, SQLiteUserRepository
from core.services.auth_service import AuthService
from core.services.meeting_service import InMemoryMeetingService

# Initialize database
db_conn = init_database(app.config['DATABASE'])

# Create services
user_repository = SQLiteUserRepository(db_conn)
auth_service = AuthService(user_repository=user_repository)
meeting_service = InMemoryMeetingService()  # In-memory for backward compat

# Create admin user if not exists
from core.entities.user import User, UserRole, UserStatus
admin = user_repository.get_by_username('admin')
if not admin:
    import bcrypt
    password_hash = bcrypt.hashpw('admin123'.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
    admin_user = User(
        username='admin',
        email='admin@meeting.local',
        password_hash=password_hash,
        full_name='System Administrator',
        role=UserRole.ADMIN,
        status=UserStatus.APPROVED
    )
    user_repository.create(admin_user)
    print("[AUTH] Default admin user created: admin / admin123")

# Make services available to routes via app
app.auth_service = auth_service
app.meeting_service = meeting_service

# =============================================================================
# FLASK-LOGIN SETUP
# =============================================================================

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'auth.login'
login_manager.login_message = 'Please log in to access this page.'


class FlaskUser(UserMixin):
    """Flask-Login User wrapper that bridges core User to Flask-Login."""

    def __init__(self, user):
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
        return self._user.role.value if hasattr(self._user.role, 'value') else self._user.role

    @property
    def status(self):
        return self._user.status.value if hasattr(self._user.status, 'value') else self._user.status

    def is_admin(self):
        return self._user.is_admin()

    def is_approved(self):
        return self._user.is_approved()

    def get_id(self):
        return str(self._user.id)


@login_manager.user_loader
def load_user(user_id):
    user = auth_service.get_user_by_id(int(user_id))
    if user:
        return FlaskUser(user)
    return None


# =============================================================================
# DECORATORS
# =============================================================================

def approved_required(f):
    """Require that the user is approved to access the route."""
    from functools import wraps
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            return login_manager.unauthorized()
        status_val = current_user.status
        if hasattr(status_val, 'value'):
            status_val = status_val.value
        if status_val != 'approved':
            if request.is_json:
                return jsonify({'error': 'Your account is not approved. Please contact administrator.'}), 403
            flash('Your account is not approved. Please contact administrator.', 'warning')
            return redirect(url_for('meeting.index')
                             if current_user.is_authenticated else url_for('auth.login'))
        return f(*args, **kwargs)
    return decorated_function


# =============================================================================
# REGISTER BLUEPRINTS
# =============================================================================

app.register_blueprint(auth_blueprint)
app.register_blueprint(admin_blueprint)
app.register_blueprint(meeting_blueprint)


# =============================================================================
# ROOT ROUTE (catch-all that delegates to meeting index)
# =============================================================================

@app.route('/')
def root():
    """Root route - delegates to meeting index."""
    return redirect(url_for('meeting.index'))


# =============================================================================
# APP STARTUP
# =============================================================================

if __name__ == '__main__':
    print("\n" + "=" * 50)
    print(" Meeting Assistant Web Server (Clean Architecture)")
    print("=" * 50)
    print("\nServer running at: http://localhost:5000")
    print("\nDefault admin credentials:")
    print("  Username: admin")
    print("  Password: admin123")
    print("\nPress Ctrl+C to stop\n")
    app.run(host='0.0.0.0', port=5000, debug=True)