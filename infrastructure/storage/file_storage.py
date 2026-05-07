"""
Infrastructure Storage: File Storage
Handles file upload, storage, and retrieval.
"""

import os
import uuid
import logging
from werkzeug.utils import secure_filename
from typing import Optional

logger = logging.getLogger(__name__)

ALLOWED_EXTENSIONS = {'mp3', 'wav', 'm4a', 'flac', 'webm', 'ogg', 'mp4'}


class FileStorage:
    """Handles file storage operations."""

    def __init__(self, upload_folder: str, max_content_length: int = 500 * 1024 * 1024):
        self.upload_folder = upload_folder
        self.max_content_length = max_content_length
        os.makedirs(upload_folder, exist_ok=True)

    def allowed_file(self, filename: str) -> bool:
        """Check if file extension is allowed."""
        return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

    def save_file(self, file, original_filename: str, meeting_id: str = None) -> Optional[dict]:
        """
        Save an uploaded file.

        Args:
            file: FileStorage uploaded file
            original_filename: Original filename
            meeting_id: Optional meeting ID for association

        Returns:
            Dict with file info or None if failed
        """
        if not file or file.filename == '':
            return None

        if not self.allowed_file(file.filename):
            logger.warning(f"File type not allowed: {file.filename}")
            return None

        meeting_id = meeting_id or str(uuid.uuid4())
        filename = secure_filename(f"{meeting_id}_{file.filename}")
        filepath = os.path.join(self.upload_folder, filename)

        try:
            file.save(filepath)
            file_size = os.path.getsize(filepath)

            return {
                'meeting_id': meeting_id,
                'filename': filename,
                'original_filename': original_filename,
                'file_path': filepath,
                'file_size': file_size,
                'status': 'uploaded'
            }
        except Exception as e:
            logger.error(f"Failed to save file: {e}")
            return None

    def save_base64_audio(self, audio_data: str, meeting_id: str = None) -> Optional[dict]:
        """
        Save base64-encoded audio data.

        Args:
            audio_data: Base64-encoded audio data
            meeting_id: Optional meeting ID

        Returns:
            Dict with file info or None if failed
        """
        import base64

        meeting_id = meeting_id or str(uuid.uuid4())
        filename = f"{meeting_id}_recording.webm"
        filepath = os.path.join(self.upload_folder, filename)

        try:
            audio_bytes = base64.b64decode(audio_data)
            with open(filepath, 'wb') as f:
                f.write(audio_bytes)

            file_size = os.path.getsize(filepath)

            return {
                'meeting_id': meeting_id,
                'filename': filename,
                'original_filename': f"Recording",
                'file_path': filepath,
                'file_size': file_size,
                'status': 'uploaded'
            }
        except Exception as e:
            logger.error(f"Failed to save base64 audio: {e}")
            return None

    def delete_file(self, filepath: str) -> bool:
        """Delete a file from storage."""
        try:
            if os.path.exists(filepath):
                os.remove(filepath)
                return True
            return False
        except Exception as e:
            logger.error(f"Failed to delete file {filepath}: {e}")
            return False

    def get_file_path(self, filename: str) -> str:
        """Get full path for a filename."""
        return os.path.join(self.upload_folder, filename)
