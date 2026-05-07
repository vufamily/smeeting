"""
Routes: Meeting Routes
Handles meeting management (upload, process, result).
"""

from flask import render_template, request, jsonify, redirect, url_for, flash, send_from_directory
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename
import os
import uuid
import base64

from . import meeting_bp


ALLOWED_EXTENSIONS = {'mp3', 'wav', 'm4a', 'flac', 'webm', 'ogg', 'mp4'}


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


@meeting_bp.route('/')
def index():
    """Main dashboard page."""
    if current_user.is_authenticated and current_user.is_approved():
        return render_template('index.html', user=current_user)
    return render_template('login.html', username='', error='')


@meeting_bp.route('/dashboard')
@login_required
def dashboard():
    """Dashboard page."""
    return render_template('index.html', user=current_user)


@meeting_bp.route('/process/<meeting_id>')
@login_required
def process_page(meeting_id):
    return render_template('process.html', meeting_id=meeting_id, user=current_user)


@meeting_bp.route('/result/<meeting_id>')
@login_required
def result_page(meeting_id):
    return render_template('result.html', meeting_id=meeting_id, user=current_user)


@meeting_bp.route('/profile')
@login_required
def profile():
    """User profile page."""
    return render_template('profile.html')


# =============================================================================
# API ROUTES
# =============================================================================

@meeting_bp.route('/api/upload', methods=['POST'])
def upload_file():
    """Upload an audio file for processing."""
    if not current_user.is_authenticated or not current_user.is_approved():
        return jsonify({'error': 'Authentication required'}), 401

    if 'audio' not in request.files:
        return jsonify({'error': 'No file provided'}), 400

    file = request.files['audio']
    if file.filename == '':
        return jsonify({'error': 'No file selected'}), 400

    if file and allowed_file(file.filename):
        from app import meeting_service
        meeting_id = str(uuid.uuid4())
        filename = secure_filename(f"{meeting_id}_{file.filename}")
        upload_folder = app.config['UPLOAD_FOLDER']
        filepath = os.path.join(upload_folder, filename)
        os.makedirs(upload_folder, exist_ok=True)
        file.save(filepath)

        meeting = meeting_service.create_meeting(
            name=secure_filename(file.filename),
            audio_file=filepath,
            user_id=int(current_user.id)
        )

        return jsonify({
            'meeting_id': meeting['id'],
            'status': 'uploaded',
            'filename': filename
        })

    return jsonify({'error': 'Invalid file type'}), 400


@meeting_bp.route('/api/record', methods=['POST'])
def save_recorded_audio():
    """Save recorded audio from browser."""
    if not current_user.is_authenticated or not current_user.is_approved():
        return jsonify({'error': 'Authentication required'}), 401

    data = request.get_json()
    if not data or 'audio_data' not in data:
        return jsonify({'error': 'No audio data provided'}), 400

    from app import meeting_service
    meeting_id = str(uuid.uuid4())
    filename = f"{meeting_id}_recording.webm"
    upload_folder = app.config['UPLOAD_FOLDER']
    filepath = os.path.join(upload_folder, filename)
    os.makedirs(upload_folder, exist_ok=True)

    audio_bytes = base64.b64decode(data['audio_data'])
    with open(filepath, 'wb') as f:
        f.write(audio_bytes)

    from datetime import datetime
    meeting = meeting_service.create_meeting(
        name=f"Recording {datetime.now().strftime('%Y-%m-%d %H:%M')}",
        audio_file=filepath,
        user_id=int(current_user.id)
    )

    return jsonify({
        'meeting_id': meeting['id'],
        'status': 'saved'
    })


@meeting_bp.route('/api/process', methods=['POST'])
def start_processing():
    """Start processing a meeting."""
    if not current_user.is_authenticated or not current_user.is_approved():
        return jsonify({'error': 'Authentication required'}), 401

    data = request.get_json()
    if not data or 'meeting_id' not in data:
        return jsonify({'error': 'Missing meeting_id'}), 400

    from app import meeting_service
    meeting_id = data['meeting_id']
    meeting = meeting_service.get_meeting(meeting_id)

    if not meeting:
        return jsonify({'error': 'Meeting not found'}), 404

    job = meeting_service.create_processing_job(meeting_id)
    return jsonify({
        'job_id': job['job_id'],
        'status': 'processing',
        'meeting_name': meeting.get('name', ''),
        'audio_file': meeting.get('audio_file', '')
    })


@meeting_bp.route('/api/status/<job_id>')
def get_status(job_id):
    """Get processing job status."""
    if not current_user.is_authenticated or not current_user.is_approved():
        return jsonify({'error': 'Authentication required'}), 401

    from app import meeting_service
    job = meeting_service.get_job(job_id)
    if not job:
        return jsonify({'error': 'Job not found'}), 404
    return jsonify(job)


@meeting_bp.route('/api/result/<meeting_id>')
def get_result(meeting_id):
    """Get processing result."""
    if not current_user.is_authenticated or not current_user.is_approved():
        return jsonify({'error': 'Authentication required'}), 401

    from app import meeting_service
    meeting = meeting_service.get_meeting(meeting_id)
    if not meeting:
        return jsonify({'error': 'Meeting not found'}), 404

    return jsonify({
        'meeting_id': meeting_id,
        'meeting_name': meeting.get('name', ''),
        'created_at': meeting.get('created_at', ''),
        'audio_file': meeting.get('audio_file', ''),
        'transcription': meeting.get('transcription', []),
        'decisions': meeting.get('decisions', []),
        'tasks': meeting.get('tasks', []),
        'summary': meeting.get('summary', '')
    })


@meeting_bp.route('/api/meetings')
def get_meetings():
    """Get all meetings for current user."""
    if not current_user.is_authenticated or not current_user.is_approved():
        return jsonify({'error': 'Authentication required'}), 401

    from app import meeting_service
    meetings = meeting_service.get_all_meetings()
    return jsonify({'meetings': meetings})


@meeting_bp.route('/api/meeting/<meeting_id>', methods=['GET'])
def get_meeting(meeting_id):
    """Get meeting details."""
    if not current_user.is_authenticated or not current_user.is_approved():
        return jsonify({'error': 'Authentication required'}), 401

    from app import meeting_service
    meeting = meeting_service.get_meeting(meeting_id)
    if not meeting:
        return jsonify({'error': 'Meeting not found'}), 404

    return jsonify({
        'id': meeting['id'],
        'name': meeting.get('name', ''),
        'created_at': meeting.get('created_at', ''),
        'status': meeting.get('status', 'unknown'),
        'audio_file': meeting.get('audio_file', '')
    })


@meeting_bp.route('/api/meeting/<meeting_id>', methods=['DELETE'])
def delete_meeting(meeting_id):
    """Delete a meeting."""
    if not current_user.is_authenticated or not current_user.is_approved():
        return jsonify({'error': 'Authentication required'}), 401

    from app import meeting_service
    meeting = meeting_service.get_meeting(meeting_id)
    if meeting:
        audio_file = meeting.get('audio_file')
        if audio_file and os.path.exists(audio_file):
            os.remove(audio_file)

    success = meeting_service.delete_meeting(meeting_id)
    return jsonify({'status': 'deleted' if success else 'failed'})


@meeting_bp.route('/api/auth/me')
@login_required
def get_current_user():
    """Get current authenticated user info."""
    return jsonify({
        'id': current_user.id,
        'username': current_user.username,
        'email': current_user.email,
        'full_name': current_user.full_name,
        'role': str(current_user.role),
        'status': str(current_user.status)
    })


# Serve uploaded files
@meeting_bp.route('/uploads/<filename>')
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)