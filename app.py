"""
Meeting Assistant - Simple Flask Server for Web UI Testing
Standalone server for development and testing of the web interface.
For production, use main.py with the full backend pipeline.
"""

import os
import uuid
import json
import base64
from datetime import datetime
from flask import Flask, render_template, request, jsonify, send_from_directory
from werkzeug.utils import secure_filename

app = Flask(__name__, 
            template_folder='templates',
            static_folder='static')
app.config['SECRET_KEY'] = 'meeting-assistant-secret-key'
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['MAX_CONTENT_LENGTH'] = 500 * 1024 * 1024  # 500MB max

ALLOWED_EXTENSIONS = {'mp3', 'wav', 'm4a', 'flac', 'webm', 'ogg', 'mp4'}

# In-memory storage
meetings = {}
processing_jobs = {}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def create_sample_transcription():
    """Generate sample transcription data for demo"""
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
    """Generate sample decisions for demo"""
    return [
        {"id": str(uuid.uuid4()), "text": "Mobile app beta release target: April 1st", "speaker": "Speaker A", "timestamp": 22.5},
        {"id": str(uuid.uuid4()), "text": "Marketing budget: 50K (35K social media, 15K email)", "speaker": "Speaker B", "timestamp": 78.2},
        {"id": str(uuid.uuid4()), "text": "Staging environment setup by next Friday", "speaker": "Speaker C", "timestamp": 98.5},
        {"id": str(uuid.uuid4()), "text": "External contractor on standby for April 1st week", "speaker": "Speaker A", "timestamp": 120.5}
    ]

def create_sample_tasks():
    """Generate sample tasks for demo"""
    return [
        {"id": str(uuid.uuid4()), "text": "Prepare revised Q2 schedule", "assignee": "Sarah", "due_date": "2026-05-10", "completed": False},
        {"id": str(uuid.uuid4()), "text": "Coordinate staging environment setup", "assignee": "David", "due_date": "2026-05-14", "completed": False},
        {"id": str(uuid.uuid4()), "text": "Finalize marketing campaign materials", "assignee": "Marketing Team", "due_date": "2026-05-20", "completed": False},
        {"id": str(uuid.uuid4()), "text": "Set up external contractor engagement", "assignee": "Sarah", "due_date": "2026-05-08", "completed": False}
    ]

def create_sample_summary():
    """Generate sample summary for demo"""
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


# Routes

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/process/<meeting_id>')
def process_page(meeting_id):
    return render_template('process.html', meeting_id=meeting_id)

@app.route('/result/<meeting_id>')
def result_page(meeting_id):
    return render_template('result.html', meeting_id=meeting_id)


# API Routes

@app.route('/api/upload', methods=['POST'])
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
            'status': 'uploaded'
        }
        
        return jsonify({
            'meeting_id': meeting_id,
            'status': 'uploaded',
            'filename': filename
        })
    
    return jsonify({'error': 'Invalid file type'}), 400


@app.route('/api/record', methods=['POST'])
def save_recorded_audio():
    data = request.get_json()
    
    if not data or 'audio_data' not in data:
        return jsonify({'error': 'No audio data provided'}), 400
    
    meeting_id = str(uuid.uuid4())
    filename = f"{meeting_id}_recording.webm"
    filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    
    # Decode base64 and save
    audio_bytes = base64.b64decode(data['audio_data'])
    with open(filepath, 'wb') as f:
        f.write(audio_bytes)
    
    meetings[meeting_id] = {
        'id': meeting_id,
        'name': f"Recording {datetime.now().strftime('%Y-%m-%d %H:%M')}",
        'created_at': datetime.now().isoformat(),
        'audio_file': filepath,
        'status': 'uploaded'
    }
    
    return jsonify({
        'meeting_id': meeting_id,
        'status': 'saved'
    })


@app.route('/api/process', methods=['POST'])
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
        'meeting_name': meetings[meeting_id]['name']
    })


@app.route('/api/status/<job_id>')
def get_status(job_id):
    if job_id not in processing_jobs:
        return jsonify({'error': 'Job not found'}), 404
    
    job = processing_jobs[job_id]
    
    # Simulate processing progression
    step_order = ['upload', 'validate', 'transcribe', 'speakers', 'decisions', 'tasks', 'summary', 'complete']
    
    if job['status'] == 'processing':
        current_idx = step_order.index(job['step']) if job['step'] in step_order else 0
        
        # Auto-advance steps every few seconds
        if current_idx < len(step_order) - 1:
            import random
            if random.random() > 0.3:  # 70% chance to advance
                next_step = step_order[current_idx + 1]
                job['step'] = next_step
                job['progress'] = int((current_idx + 1) / (len(step_order) - 1) * 100)
                
                # Mark previous complete
                prev_step = step_order[current_idx]
                job['steps'][prev_step] = {'status': 'complete', 'progress': 100}
                
                # Set current processing
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
    
    # Check if we already have results
    if 'result' in meeting:
        return jsonify(meeting['result'])
    
    # Generate sample results for demo
    result = {
        'meeting_id': meeting_id,
        'meeting_name': meeting['name'],
        'created_at': meeting['created_at'],
        'transcription': create_sample_transcription(),
        'decisions': create_sample_decisions(),
        'tasks': create_sample_tasks(),
        'summary': create_sample_summary()
    }
    
    # Store results
    meeting['result'] = result
    meeting['status'] = 'complete'
    
    # Mark any associated job as complete
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


@app.route('/api/meeting/<meeting_id>', methods=['DELETE'])
def delete_meeting(meeting_id):
    if meeting_id not in meetings:
        return jsonify({'error': 'Meeting not found'}), 404
    
    meeting = meetings[meeting_id]
    
    # Delete audio file if exists
    audio_file = meeting.get('audio_file')
    if audio_file and os.path.exists(audio_file):
        os.remove(audio_file)
    
    del meetings[meeting_id]
    
    # Remove associated job
    for job_id, job in list(processing_jobs.items()):
        if job['meeting_id'] == meeting_id:
            del processing_jobs[job_id]
    
    return jsonify({'status': 'deleted'})


@app.route('/api/simulate-processing/<job_id>')
def simulate_processing_step(job_id):
    """Helper endpoint to manually advance processing (for demo)"""
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
@app.route('/uploads/')
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)


if __name__ == '__main__':
    os.makedirs('uploads', exist_ok=True)
    print("\n" + "="*50)
    print("🎙️  Meeting Assistant Web UI Server")
    print("="*50)
    print("\nServer running at: http://localhost:5000")
    print("Press Ctrl+C to stop\n")
    app.run(host='0.0.0.0', port=5000, debug=True)