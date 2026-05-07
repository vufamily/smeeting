"""
Routes - Presentation layer route handlers.
Registration and grouping of all route blueprints.
"""

from flask import Blueprint

# Create route blueprints
auth_bp = Blueprint('auth', __name__, url_prefix='/auth')
admin_bp = Blueprint('admin', __name__, url_prefix='/admin')
meeting_bp = Blueprint('meeting', __name__)

__all__ = ["auth_bp", "admin_bp", "meeting_bp"]