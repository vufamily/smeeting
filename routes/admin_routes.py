"""
Routes: Admin Routes
Handles admin user management.
"""

from flask import render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user

from . import admin_bp


def admin_required(f):
    """Decorator requiring user to be admin."""
    from functools import wraps
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            return redirect(url_for('auth.login'))
        if not current_user.is_admin():
            if request.is_json:
                return jsonify({'error': 'Admin access required.'}), 403
            flash('Admin access required.', 'danger')
            return redirect(url_for('index'))
        return f(*args, **kwargs)
    return decorated_function


@admin_bp.route('/users')
@admin_required
def admin_users():
    """Admin user management panel."""
    from app import auth_service
    users = auth_service.get_all_users()
    return render_template('admin.html', users=users)


@admin_bp.route('/users/create', methods=['POST'])
@admin_required
def admin_create_user():
    """Admin creates a new user directly (approved immediately)."""
    username = request.form.get('username', '').strip()
    email = request.form.get('email', '').strip()
    password = request.form.get('password', '')
    full_name = request.form.get('full_name', '').strip()
    role = request.form.get('role', 'user')

    from app import auth_service
    success, message, user = auth_service.register_user(username, email, password, full_name)
    if success:
        # Immediately approve the user
        auth_service.approve_user(user.id)
        flash(f'User "{username}" created successfully.', 'success')
    else:
        flash(message, 'danger')
    return redirect(url_for('admin.admin_users'))


@admin_bp.route('/users/<int:user_id>/approve')
@admin_required
def admin_approve_user(user_id):
    """Approve a pending user."""
    from app import auth_service
    success, message = auth_service.approve_user(user_id)
    flash(message, 'success' if success else 'danger')
    return redirect(url_for('admin.admin_users'))


@admin_bp.route('/users/<int:user_id>/reject')
@admin_required
def admin_reject_user(user_id):
    """Reject a user."""
    from app import auth_service
    success, message = auth_service.reject_user(user_id)
    flash(message, 'warning' if success else 'danger')
    return redirect(url_for('admin.admin_users'))


@admin_bp.route('/users/<int:user_id>/disable')
@admin_required
def admin_disable_user(user_id):
    """Disable a user."""
    if current_user.id == user_id:
        flash('You cannot disable your own account.', 'danger')
        return redirect(url_for('admin.admin_users'))

    from app import auth_service
    success, message = auth_service.disable_user(user_id)
    flash(message, 'warning' if success else 'danger')
    return redirect(url_for('admin.admin_users'))


@admin_bp.route('/users/<int:user_id>/enable')
@admin_required
def admin_enable_user(user_id):
    """Re-enable a disabled user."""
    from app import auth_service
    success, message = auth_service.enable_user(user_id)
    flash(message, 'success' if success else 'danger')
    return redirect(url_for('admin.admin_users'))


@admin_bp.route('/users/<int:user_id>/delete')
@admin_required
def admin_delete_user(user_id):
    """Delete a user."""
    if current_user.id == user_id:
        flash('You cannot delete your own account.', 'danger')
        return redirect(url_for('admin.admin_users'))

    from app import auth_service
    user = auth_service.get_user_by_id(user_id)
    username = user.username if user else str(user_id)
    success = auth_service.delete_user(user_id)
    flash(f'User "{username}" has been deleted.', 'success' if success else 'danger')
    return redirect(url_for('admin.admin_users'))


@admin_bp.route('/users/<int:user_id>/update', methods=['POST'])
@admin_required
def admin_update_user(user_id):
    """Update user details (role, full_name)."""
    role = request.form.get('role', 'user')
    full_name = request.form.get('full_name', '').strip()

    from app import auth_service
    user = auth_service.get_user_by_id(user_id)
    if user:
        user.role = role
        user.full_name = full_name
        auth_service.update_user(user)
        flash('User updated successfully.', 'success')
    else:
        flash('User not found.', 'danger')
    return redirect(url_for('admin.admin_users'))


@admin_bp.route('/users/<int:user_id>/reset-password', methods=['POST'])
@admin_required
def admin_reset_password(user_id):
    """Admin resets a user's password."""
    new_password = request.form.get('new_password', '')
    if not new_password or len(new_password) < 6:
        flash('Password must be at least 6 characters.', 'danger')
        return redirect(url_for('admin.admin_users'))

    from app import auth_service
    success, message = auth_service.change_password(user_id, new_password)
    flash(message, 'success' if success else 'danger')
    return redirect(url_for('admin.admin_users'))