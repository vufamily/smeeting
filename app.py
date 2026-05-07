"""
Meeting Assistant - Flask Server with Authentication
Full server with user auth, admin panel, and meeting management.
"""

import os
import uuid
import json
import base64
import sqlite3
from datetime import datetime
from functools import wraps

from flask import Flask, render_template, request, jsonify, send_from_directory, redirect, url_for, session, flash
from werkzeug.utils import secure_filename
from flask_login import LoginManager, login_user, logout_user, login_required, current_user, UserMixin
import bcrypt

app = Flask(__name__,
            template_folder='templates',
            static_folder='static')
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'meeting-assistant-secret-key-change-in-production')
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['MAX_CONTENT_LENGTH'] = 500 * 1024 * 1024  # 500MB max
app.config['DATABASE'] = 'data/meeting.db'

ALLOWED_EXTENSIONS = {'mp3', 'wav', 'm4a', 'flac', 'webm', 'ogg', 'mp4'}

# In-memory storage (for meetings - separate from auth)
meetings = {}
processing_jobs = {}

# =============================================================================
# DATABASE SETUP
# =============================================================================

def get_db():
    """Get SQLite database connection."""
    conn = sqlite3.connect(app.config['DATABASE'])
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    """Initialize the database with required tables."""
    os.makedirs('data', exist_ok=True)
    conn = get_db()
    cursor = conn.cursor()

    # Users table with approval workflow
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            email TEXT UNIQUE,
            password_hash TEXT NOT NULL,
            full_name TEXT,
            role TEXT DEFAULT 'user',
            status TEXT DEFAULT 'pending',
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # Meetings table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS meetings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            description TEXT,
            scheduled_at DATETIME,
            duration_minutes INTEGER,
            status TEXT DEFAULT 'pending',
            created_by INTEGER REFERENCES users(id),
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # Settings table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS settings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            key TEXT UNIQUE NOT NULL,
            value TEXT NOT NULL,
            description TEXT,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    conn.commit()

    # Create initial admin user if not exists
    cursor.execute('SELECT id FROM users WHERE username = ?', ('admin',))
    if cursor.fetchone() is None:
        password_hash = bcrypt.hashpw('admin123'.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
        cursor.execute('''
            INSERT INTO users (username, email, password_hash, full_name, role, status)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', ('admin', 'admin@meeting.local', password_hash, 'System Administrator', 'admin', 'approved'))
        conn.commit()
        print("[AUTH] Default admin user created: admin / admin123")

    conn.close()

# Initialize database on startup
init_db()

# =============================================================================
# FLASK-LOGIN SETUP
# =============================================================================

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'
login_manager.login_message = 'Please log in to access this page.'

class User(UserMixin):
    """User class for Flask-Login."""

    def __init__(self, user_id, username, email, full_name, role, status, created_at):
        self.id = user_id
        self.username = username
        self.email = email
        self.full_name = full_name
        self.role = role
        self.status = status
        self.created_at = created_at

    @staticmethod
    def get(user_id):
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM users WHERE id = ?', (user_id,))
        row = cursor.fetchone()
        conn.close()
        if row:
            return User(row['id'], row['username'], row['email'], row['full_name'],
                        row['role'], row['status'], row['created_at'])
        return None

    @staticmethod
    def get_by_username(username):
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM users WHERE username = ?', (username,))
        row = cursor.fetchone()
        conn.close()
        if row:
            return User(row['id'], row['username'], row['email'], row['full_name'],
                        row['role'], row['status'], row['created_at'])
        return None

    def is_admin(self):
        return self.role == 'admin' and self.status == 'approved'

    def is_approved(self):
        return self.status == 'approved'

@login_manager.user_loader
def load_user(user_id):
    return User.get(int(user_id))

# =============================================================================
# DECORATORS
# =============================================================================

def approved_required(f):
    """Require that the user is approved to access the route."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            return login_manager.unauthorized()
        if current_user.status != 'approved':
            if request.is_json:
                return jsonify({'error': 'Your account is not approved. Please contact administrator.'}), 403
            flash('Your account is not approved. Please contact administrator.', 'warning')
            return redirect(url_for('index'))
        return f(*args, **kwargs)
    return decorated_function

def admin_required(f):
    """Require that the user is an admin to access the route."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            return login_manager.unauthorized()
        if not current_user.is_admin():
            if request.is_json:
                return jsonify({'error': 'Admin access required.'}), 403
            flash('Admin access required.', 'danger')
            return redirect(url_for('index'))
        return f(*args, **kwargs)
    return decorated_function

# =============================================================================
# AUTH ROUTES
# =============================================================================

@app.route('/auth/register', methods=['GET', 'POST'])
def register():
    """User registration."""
    if current_user.is_authenticated:
        return redirect(url_for('index'))

    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        email = request.form.get('email', '').strip()
        password = request.form.get('password', '')
        full_name = request.form.get('full_name', '').strip()

        errors = {}

        if not username:
            errors['username'] = 'Username is required'
        elif len(username) < 3:
            errors['username'] = 'Username must be at least 3 characters'
        elif not username.replace('_', '').replace('-', '').isalnum():
            errors['username'] = 'Username can only contain letters, numbers, hyphens, and underscores'

        if not email:
            errors['email'] = 'Email is required'
        elif '@' not in email:
            errors['email'] = 'Invalid email address'

        if not password:
            errors['password'] = 'Password is required'
        elif len(password) < 6:
            errors['password'] = 'Password must be at least 6 characters'

        if errors:
            return render_template('register.html',
                                   username=username, email=email, full_name=full_name,
                                   errors=errors)

        conn = get_db()
        cursor = conn.cursor()

        # Check if username exists
        cursor.execute('SELECT id FROM users WHERE username = ?', (username,))
        if cursor.fetchone():
            conn.close()
            errors['username'] = 'Username already taken'
            return render_template('register.html',
                                   username=username, email=email, full_name=full_name,
                                   errors=errors)

        # Check if email exists
        cursor.execute('SELECT id FROM users WHERE email = ?', (email,))
        if cursor.fetchone():
            conn.close()
            errors['email'] = 'Email already registered'
            return render_template('register.html',
                                   username=username, email=email, full_name=full_name,
                                   errors=errors)

        # Create user with pending status
        password_hash = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
        cursor.execute('''
            INSERT INTO users (username, email, password_hash, full_name, role, status)
            VALUES (?, ?, ?, ?, 'user', 'pending')
        ''', (username, email, password_hash, full_name or username))
        conn.commit()
        conn.close()

        flash('Registration successful! Your account is pending approval by an administrator.', 'success')
        return redirect(url_for('login'))

    return render_template('register.html', username='', email='', full_name='', errors={})


@app.route('/auth/login', methods=['GET', 'POST'])
def login():
    """User login."""
    if current_user.is_authenticated:
        return redirect(url_for('index'))

    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')

        if not username or not password:
            return render_template('login.html', username=username,
                                   error='Please enter both username and password.')

        conn = get_db()
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM users WHERE username = ?', (username,))
        row = cursor.fetchone()
        conn.close()

        if row:
            stored_hash = row['password_hash'].encode('utf-8')
            if bcrypt.checkpw(password.encode('utf-8'), stored_hash):
                user = User(row['id'], row['username'], row['email'], row['full_name'],
                             row['role'], row['status'], row['created_at'])

                # Check status before allowing login
                if user.status == 'pending':
                    return render_template('login.html', username=username,
                                           error='Your account is pending approval. Please contact administrator.')

                if user.status == 'rejected':
                    return render_template('login.html', username=username,
                                           error='Your account has been rejected. Please contact administrator.')

                if user.status == 'disabled':
                    return render_template('login.html', username=username,
                                           error='Your account has been disabled. Please contact administrator.')

                login_user(user, remember=True)
                flash(f'Welcome back, {user.username}!', 'success')

                next_page = request.args.get('next')
                if next_page:
                    return redirect(next_page)
                return redirect(url_for('index'))

        return render_template('login.html', username=username,
                               error='Invalid username or password.')

    return render_template('login.html', username='', error='')


@app.route('/auth/logout')
@login_required
def logout():
    """User logout."""
    logout_user()
    flash('You have been logged out.', 'info')
    return redirect(url_for('login'))


# =============================================================================
# ADMIN ROUTES
# =============================================================================

@app.route('/admin/users')
@admin_required
def admin_users():
    """Admin user management panel."""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM users ORDER BY created_at DESC')
    users = cursor.fetchall()
    conn.close()
    return render_template('admin.html', users=users)


@app.route('/admin/users/create', methods=['POST'])
@admin_required
def admin_create_user():
    """Admin creates a new user directly (approved immediately)."""
    username = request.form.get('username', '').strip()
    email = request.form.get('email', '').strip()
    password = request.form.get('password', '')
    full_name = request.form.get('full_name', '').strip()
    role = request.form.get('role', 'user')

    errors = {}
    if not username:
        errors['username'] = 'Username is required'
    if not email:
        errors['email'] = 'Email is required'
    if not password:
        errors['password'] = 'Password is required'
    elif len(password) < 6:
        errors['password'] = 'Password must be at least 6 characters'

    if errors:
        flash('Please fix the errors below.', 'danger')
        return redirect(url_for('admin_users'))

    conn = get_db()
    cursor = conn.cursor()

    cursor.execute('SELECT id FROM users WHERE username = ?', (username,))
    if cursor.fetchone():
        conn.close()
        flash('Username already exists.', 'danger')
        return redirect(url_for('admin_users'))

    cursor.execute('SELECT id FROM users WHERE email = ?', (email,))
    if cursor.fetchone():
        conn.close()
        flash('Email already exists.', 'danger')
        return redirect(url_for('admin_users'))

    password_hash = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
    cursor.execute('''
        INSERT INTO users (username, email, password_hash, full_name, role, status)
        VALUES (?, ?, ?, ?, ?, 'approved')
    ''', (username, email, password_hash, full_name or username, role))
    conn.commit()
    conn.close()

    flash(f'User "{username}" created successfully.', 'success')
    return redirect(url_for('admin_users'))


@app.route('/admin/users/<int:user_id>/approve')
@admin_required
def admin_approve_user(user_id):
    """Approve a pending user."""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('UPDATE users SET status = ? WHERE id = ? AND status = ?',
                   ('approved', user_id, 'pending'))
    conn.commit()

    cursor.execute('SELECT username FROM users WHERE id = ?', (user_id,))
    row = cursor.fetchone()
    conn.close()

    if row:
        flash(f'User "{row["username"]}" has been approved.', 'success')
    return redirect(url_for('admin_users'))


@app.route('/admin/users/<int:user_id>/reject')
@admin_required
def admin_reject_user(user_id):
    """Reject a user."""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('UPDATE users SET status = ? WHERE id = ?',
                   ('rejected', user_id))
    conn.commit()

    cursor.execute('SELECT username FROM users WHERE id = ?', (user_id,))
    row = cursor.fetchone()
    conn.close()

    if row:
        flash(f'User "{row["username"]}" has been rejected.', 'warning')
    return redirect(url_for('admin_users'))


@app.route('/admin/users/<int:user_id>/disable')
@admin_required
def admin_disable_user(user_id):
    """Disable a user."""
    if current_user.id == user_id:
        flash('You cannot disable your own account.', 'danger')
        return redirect(url_for('admin_users'))

    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('UPDATE users SET status = ? WHERE id = ?',
                   ('disabled', user_id))
    conn.commit()

    cursor.execute('SELECT username FROM users WHERE id = ?', (user_id,))
    row = cursor.fetchone()
    conn.close()

    if row:
        flash(f'User "{row["username"]}" has been disabled.', 'warning')
    return redirect(url_for('admin_users'))


@app.route('/admin/users/<int:user_id>/enable')
@admin_required
def admin_enable_user(user_id):
    """Re-enable a disabled user."""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('UPDATE users SET status = ? WHERE id = ?',
                   ('approved', user_id))
    conn.commit()

    cursor.execute('SELECT username FROM users WHERE id = ?', (user_id,))
    row = cursor.fetchone()
    conn.close()

    if row:
        flash(f'User "{row["username"]}" has been enabled.', 'success')
    return redirect(url_for('admin_users'))


@app.route('/admin/users/<int:user_id>/delete')
@admin_required
def admin_delete_user(user_id):
    """Delete a user."""
    if current_user.id == user_id:
        flash('You cannot delete your own account.', 'danger')
        return redirect(url_for('admin_users'))

    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('SELECT username FROM users WHERE id = ?', (user_id,))
    row = cursor.fetchone()
    cursor.execute('DELETE FROM users WHERE id = ?', (user_id,))
    conn.commit()
    conn.close()

    if row:
        flash(f'User "{row["username"]}" has been deleted.', 'success')
    return redirect(url_for('admin_users'))


@app.route('/admin/users/<int:user_id>/update', methods=['POST'])
@admin_required
def admin_update_user(user_id):
    """Update user details (role, full_name)."""
    role = request.form.get('role', 'user')
    full_name = request.form.get('full_name', '').strip()

    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('UPDATE users SET role = ?, full_name = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?',
                   (role, full_name, user_id))
    conn.commit()
    conn.close()

    flash('User updated successfully.', 'success')
    return redirect(url_for('admin_users'))


@app.route('/admin/users/<int:user_id>/reset-password', methods=['POST'])
@admin_required
def admin_reset_password(user_id):
    """Admin resets a user's password."""
    new_password = request.form.get('new_password', '')
    if not new_password or len(new_password) < 6:
        flash('Password must be at least 6 characters.', 'danger')
        return redirect(url_for('admin_users'))

    password_hash = bcrypt.hashpw(new_password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('UPDATE users SET password_hash = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?',
                   (password_hash, user_id))
    conn.commit()

    cursor.execute('SELECT username FROM users WHERE id = ?', (user_id,))
    row = cursor.fetchone()
    conn.close()

    if row:
        flash(f'Password for "{row["username"]}" has been reset.', 'success')
    return redirect(url_for('admin_users'))


# =============================================================================
# PROFILE ROUTES
# =============================================================================

@app.route('/profile')
@login_required
def profile():
    """User profile page."""
    return render_template('profile.html')


@app.route('/profile/update', methods=['POST'])
@login_required
def profile_update():
    """Update user profile."""
    full_name = request.form.get('full_name', '').strip()
    email = request.form.get('email', '').strip()

    errors = {}
    if not email or '@' not in email:
        errors['email'] = 'Valid email is required'

    if errors:
        for err in errors.values():
            flash(err, 'danger')
        return redirect(url_for('profile'))

    # Check email uniqueness
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('SELECT id FROM users WHERE email = ? AND id != ?', (email, current_user.id))
    if cursor.fetchone():
        conn.close()
        flash('Email already in use by another account.', 'danger')
        return redirect(url_for('profile'))

    cursor.execute('UPDATE users SET email = ?, full_name = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?',
                   (email, full_name, current_user.id))
    conn.commit()
    conn.close()

    flash('Profile updated successfully.', 'success')
    return redirect(url_for('profile'))


@app.route('/profile/change-password', methods=['POST'])
@login_required
def profile_change_password():
    """Change own password."""
    current_password = request.form.get('current_password', '')
    new_password = request.form.get('new_password', '')
    confirm_password = request.form.get('confirm_password', '')

    if not new_password or len(new_password) < 6:
        flash('New password must be at least 6 characters.', 'danger')
        return redirect(url_for('profile'))

    if new_password != confirm_password:
        flash('New passwords do not match.', 'danger')
        return redirect(url_for('profile'))

    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('SELECT password_hash FROM users WHERE id = ?', (current_user.id,))
    row = cursor.fetchone()

    if not bcrypt.checkpw(current_password.encode('utf-8'), row['password_hash'].encode('utf-8')):
        conn.close()
        flash('Current password is incorrect.', 'danger')
        return redirect(url_for('profile'))

    new_hash = bcrypt.hashpw(new_password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
    cursor.execute('UPDATE users SET password_hash = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?',
                   (new_hash, current_user.id))
    conn.commit()
    conn.close()

    flash('Password changed successfully.', 'success')
    return redirect(url_for('profile'))


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def create_sample_transcription():
    """Generate sample transcription data for demo."""
    return [
        {"speaker": "Speaker A", "start": 0.0, "end": 5.2, "text": "Good morning everyone, let's start the sprint planning meeting."},
        {"speaker": "Speaker B", "start": 5.5, "end": 12.8, "text": "Thanks for joining. Today we need to plan the Q2 deliverables. First item: mobile app release."},
        {"speaker": "Speaker A", "start": 13.2, "end": 22.5, "text": "I've reviewed the mockups. The design team did great work. We can target March 15th for the beta release."},
        {"speaker": "Speaker C", "start": 23.0, "end": 35.6, "text": "I have concerns about the timeline. The backend API changes require at least 2 weeks of testing. Can we push to April 1st?"},
        {"speaker": "Speaker B", "start": 36.0, "end": 45.3, "text": "April 1st works for marketing. Sarah, can you prepare a revised schedule by Thursday?"},
        {"speaker": "Speaker A", "start": 46.0, "end": 52.1, "text": "Yes, I'll send the updated timeline. Next topic: budget allocation for the launch campaign."},
        {"speaker": "Speaker C", "start": 53.0, "end": 65.8, "text": "Marketing requested 50K for digital ads. I think we should allocate 35K to social media and 15K to email campaigns."},
        {"speaker": "Speaker B", "start": 66.5, "end": 78.2, "text": "Sounds reasonable. Let's approve the 50K budget. Also, we need to assign owners for each work stream."},
        {"speaker": "Speaker A", "start": 79.0, "end": 90.5, "text": "I'll own the mobile app development. David, can you handle the backend infrastructure?"},
        {"speaker": "Speaker C", "start": 91.0, "end": 98.5, "text": "Yes, I'll coordinate with the DevOps team for deployment. We should set up a staging environment by next Friday."},
        {"speaker": "Speaker B", "start": 99.0, "end": 108.3, "text": "Perfect. Last item: we need a contingency plan if we hit technical blockers. Any suggestions?"},
        {"speaker": "Speaker A", "start": 109.0, "end": 120.5, "text": "We can engage the external contractor for intensive debugging. I've already reached out for availability on April 1st week."},
        {"speaker": "Speaker C", "start": 121.0, "end": 128.7, "text": "Good thinking. I think we're aligned on the plan. Let's wrap up with action items."},
        {"speaker": "Speaker B", "start": 129.0, "end": 140.2, "text": "Great meeting everyone. Summary: beta launch April 1st, 50K marketing budget approved, each team lead owns their stream."}
    ]

def create_sample_decisions():
    """Generate sample decisions for demo."""
    return [
        {"id": str(uuid.uuid4()), "text": "Mobile app beta release target: April 1st", "speaker": "Speaker A", "timestamp": 22.5},
        {"id": str(uuid.uuid4()), "text": "Marketing budget: 50K (35K social media, 15K email)", "speaker": "Speaker B", "timestamp": 78.2},
        {"id": str(uuid.uuid4()), "text": "Staging environment setup by next Friday", "speaker": "Speaker C", "timestamp": 98.5},
        {"id": str(uuid.uuid4()), "text": "External contractor on standby for April 1st week", "speaker": "Speaker A", "timestamp": 120.5}
    ]

def create_sample_tasks():
    """Generate sample tasks for demo."""
    return [
        {"id": str(uuid.uuid4()), "text": "Prepare revised Q2 schedule", "assignee": "Sarah", "due_date": "2026-05-10", "completed": False},
        {"id": str(uuid.uuid4()), "text": "Coordinate staging environment setup", "assignee": "David", "due_date": "2026-05-14", "completed": False},
        {"id": str(uuid.uuid4()), "text": "Finalize marketing campaign materials", "assignee": "Marketing Team", "due_date": "2026-05-20", "completed": False},
        {"id": str(uuid.uuid4()), "text": "Set up external contractor engagement", "assignee": "Sarah", "due_date": "2026-05-08", "completed": False}
    ]

def create_sample_summary():
    """Generate sample summary for demo."""
    return """## Meeting Summary: Sprint Planning Q2

**Date:** May 7, 2026
**Duration:** ~2.5 minutes (demo)
**Participants:** Speaker A, Speaker B, Speaker C

### Key Outcomes

1. **Timeline Agreed:** Mobile app beta release scheduled for April 1st. Sarah to send revised schedule by Thursday.

2. **Budget Approved:** 50,000 marketing budget allocated for launch campaign:
   - 35,000 for social media advertising
   - 15,000 for email marketing campaigns

3. **Team Assignments:**
   - Speaker A: Mobile app development lead
   - Speaker C: Backend infrastructure & DevOps coordination

4. **Infrastructure:** Staging environment to be ready by next Friday (May 14).

5. **Risk Mitigation:** External contractor engaged for intensive debugging support during April 1st week if technical blockers arise.

### Next Steps

- Sarah to circulate updated Q2 timeline by May 8
- Infrastructure team to begin staging environment setup
- Marketing to begin campaign material development

---
*Meeting recorded and transcribed automatically*"""


# =============================================================================
# MAIN ROUTES
# =============================================================================

@app.route('/')
def index():
    """Main dashboard page."""
    if current_user.is_authenticated and current_user.is_approved():
        return render_template('index.html', user=current_user)
    return render_template('login.html', username='', error='')


@app.route('/dashboard')
@approved_required
def dashboard():
    """Dashboard page - same as index for now."""
    return render_template('index.html', user=current_user)


@app.route('/process/<meeting_id>')
@approved_required
def process_page(meeting_id):
    return render_template('process.html', meeting_id=meeting_id, user=current_user)


@app.route('/result/<meeting_id>')
@approved_required
def result_page(meeting_id):
    return render_template('result.html', meeting_id=meeting_id, user=current_user)


# =============================================================================
# API ROUTES
# =============================================================================

@app.route('/api/upload', methods=['POST'])
@approved_required
def upload_file():
    if 'audio' not in request.files:
        return jsonify({'error': 'No file provided'}), 400

    file = request.files['audio']
    if file.filename == '':
        return jsonify({'error': 'No file selected'}), 400

    if file and allowed_file(file.filename):
        meeting_id = str(uuid.uuid4())
        filename = secure_filename(f"{meeting_id}_{file.filename}")
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)

        os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
        file.save(filepath)

        meetings[meeting_id] = {
            'id': meeting_id,
            'name': secure_filename(file.filename),
            'created_at': datetime.now().isoformat(),
            'audio_file': filepath,
            'status': 'uploaded',
            'user_id': current_user.id
        }

        return jsonify({
            'meeting_id': meeting_id,
            'status': 'uploaded',
            'filename': filename
        })

    return jsonify({'error': 'Invalid file type'}), 400


@app.route('/api/record', methods=['POST'])
@approved_required
def save_recorded_audio():
    data = request.get_json()

    if not data or 'audio_data' not in data:
        return jsonify({'error': 'No audio data provided'}), 400

    meeting_id = str(uuid.uuid4())
    filename = f"{meeting_id}_recording.webm"
    filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)

    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

    audio_bytes = base64.b64decode(data['audio_data'])
    with open(filepath, 'wb') as f:
        f.write(audio_bytes)

    meetings[meeting_id] = {
        'id': meeting_id,
        'name': f"Recording {datetime.now().strftime('%Y-%m-%d %H:%M')}",
        'created_at': datetime.now().isoformat(),
        'audio_file': filepath,
        'status': 'uploaded',
        'user_id': current_user.id
    }

    return jsonify({
        'meeting_id': meeting_id,
        'status': 'saved'
    })


@app.route('/api/process', methods=['POST'])
@approved_required
def start_processing():
    data = request.get_json()

    if not data or 'meeting_id' not in data:
        return jsonify({'error': 'Missing meeting_id'}), 400

    meeting_id = data['meeting_id']

    if meeting_id not in meetings:
        return jsonify({'error': 'Meeting not found'}), 404

    job_id = str(uuid.uuid4())

    processing_jobs[job_id] = {
        'job_id': job_id,
        'meeting_id': meeting_id,
        'status': 'processing',
        'progress': 0,
        'step': 'upload',
        'steps': {
            'upload': {'status': 'complete', 'progress': 100},
            'validate': {'status': 'complete', 'progress': 100},
            'transcribe': {'status': 'processing', 'progress': 50},
            'speakers': {'status': 'pending', 'progress': 0},
            'decisions': {'status': 'pending', 'progress': 0},
            'tasks': {'status': 'pending', 'progress': 0},
            'summary': {'status': 'pending', 'progress': 0},
            'complete': {'status': 'pending', 'progress': 0}
        }
    }

    meetings[meeting_id]['status'] = 'processing'
    meetings[meeting_id]['job_id'] = job_id

    return jsonify({
        'job_id': job_id,
        'status': 'processing',
        'meeting_name': meetings[meeting_id]['name'],
        'audio_file': meetings[meeting_id].get('audio_file', '')
    })


@app.route('/api/status/<job_id>')
def get_status(job_id):
    if job_id not in processing_jobs:
        return jsonify({'error': 'Job not found'}), 404

    job = processing_jobs[job_id]

    step_order = ['upload', 'validate', 'transcribe', 'speakers', 'decisions', 'tasks', 'summary', 'complete']

    if job['status'] == 'processing':
        current_idx = step_order.index(job['step']) if job['step'] in step_order else 0

        if current_idx < len(step_order) - 1:
            import random
            if random.random() > 0.3:
                next_step = step_order[current_idx + 1]
                job['step'] = next_step
                job['progress'] = int((current_idx + 1) / (len(step_order) - 1) * 100)

                prev_step = step_order[current_idx]
                job['steps'][prev_step] = {'status': 'complete', 'progress': 100}

                job['steps'][next_step] = {'status': 'processing', 'progress': 50}

                if next_step == 'complete':
                    job['status'] = 'complete'
                    job['progress'] = 100
                    job['steps']['complete'] = {'status': 'complete', 'progress': 100}

    return jsonify(job)


@app.route('/api/result/<meeting_id>')
def get_result(meeting_id):
    if meeting_id not in meetings:
        return jsonify({'error': 'Meeting not found'}), 404

    meeting = meetings[meeting_id]

    if 'result' in meeting:
        return jsonify(meeting['result'])

    result = {
        'meeting_id': meeting_id,
        'meeting_name': meeting['name'],
        'created_at': meeting['created_at'],
        'audio_file': meeting.get('audio_file', ''),
        'transcription': create_sample_transcription(),
        'decisions': create_sample_decisions(),
        'tasks': create_sample_tasks(),
        'summary': create_sample_summary()
    }

    meeting['result'] = result
    meeting['status'] = 'complete'

    for job in processing_jobs.values():
        if job['meeting_id'] == meeting_id:
            job['status'] = 'complete'
            job['progress'] = 100
            job['step'] = 'complete'

    return jsonify(result)


@app.route('/api/meetings')
def get_meetings():
    meetings_list = []
    for m in meetings.values():
        meetings_list.append({
            'id': m['id'],
            'name': m['name'],
            'created_at': m['created_at'],
            'status': m.get('status', 'unknown')
        })

    meetings_list.sort(key=lambda x: x['created_at'], reverse=True)

    return jsonify({'meetings': meetings_list})


@app.route('/api/meeting/<meeting_id>', methods=['GET'])
def get_meeting(meeting_id):
    if meeting_id not in meetings:
        return jsonify({'error': 'Meeting not found'}), 404

    meeting = meetings[meeting_id]
    return jsonify({
        'id': meeting['id'],
        'name': meeting['name'],
        'created_at': meeting['created_at'],
        'status': meeting.get('status', 'unknown'),
        'audio_file': meeting.get('audio_file', '')
    })


@app.route('/api/meeting/<meeting_id>', methods=['DELETE'])
def delete_meeting(meeting_id):
    if meeting_id not in meetings:
        return jsonify({'error': 'Meeting not found'}), 404

    meeting = meetings[meeting_id]

    audio_file = meeting.get('audio_file')
    if audio_file and os.path.exists(audio_file):
        os.remove(audio_file)

    del meetings[meeting_id]

    for job_id, job in list(processing_jobs.items()):
        if job['meeting_id'] == meeting_id:
            del processing_jobs[job_id]

    return jsonify({'status': 'deleted'})


@app.route('/api/simulate-processing/<job_id>')
def simulate_processing_step(job_id):
    """Helper endpoint to manually advance processing (for demo)."""
    if job_id not in processing_jobs:
        return jsonify({'error': 'Job not found'}), 404

    job = processing_jobs[job_id]
    step_order = ['upload', 'validate', 'transcribe', 'speakers', 'decisions', 'tasks', 'summary', 'complete']

    current_idx = step_order.index(job['step']) if job['step'] in step_order else 0

    if current_idx < len(step_order) - 1:
        next_step = step_order[current_idx + 1]
        job['step'] = next_step
        job['progress'] = int((current_idx + 1) / (len(step_order) - 1) * 100)

        prev_step = step_order[current_idx]
        job['steps'][prev_step] = {'status': 'complete', 'progress': 100}
        job['steps'][next_step] = {'status': 'processing', 'progress': 50}

        if next_step == 'complete':
            job['status'] = 'complete'
            job['steps']['complete'] = {'status': 'complete', 'progress': 100}

    return jsonify(job)


# Serve uploaded files
@app.route('/uploads/<filename>')
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)


# =============================================================================
# APP STARTUP
# =============================================================================

if __name__ == '__main__':
    os.makedirs('uploads', exist_ok=True)
    os.makedirs('data', exist_ok=True)
    print("\n" + "=" * 50)
    print("🎙️  Meeting Assistant Web Server (with Auth)")
    print("=" * 50)
    print("\nServer running at: http://localhost:5000")
    print("\nDefault admin credentials:")
    print("  Username: admin")
    print("  Password: admin123")
    print("\nPress Ctrl+C to stop\n")
    app.run(host='0.0.0.0', port=5000, debug=True)
