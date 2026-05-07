"""
Routes: Auth Routes
Handles authentication routes (login, register, logout).
"""

from flask import render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_user, logout_user, login_required, current_user

from . import auth_bp


@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    """User login page."""
    if current_user.is_authenticated:
        return redirect(url_for('index'))

    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')

        if not username or not password:
            return render_template('login.html', username=username,
                                   error='Please enter both username and password.')

        # Authenticate via service (injected at app startup)
        from app import auth_service
        success, message, user = auth_service.authenticate(username, password)

        if success:
            login_user(user, remember=True)
            flash(f'Welcome back, {user.username}!', 'success')
            next_page = request.args.get('next')
            if next_page:
                return redirect(next_page)
            return redirect(url_for('index'))

        return render_template('login.html', username=username, error=message)

    return render_template('login.html', username='', error='')


@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    """User registration page."""
    if current_user.is_authenticated:
        return redirect(url_for('index'))

    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        email = request.form.get('email', '').strip()
        password = request.form.get('password', '')
        full_name = request.form.get('full_name', '').strip()

        from app import auth_service
        success, message, user = auth_service.register_user(username, email, password, full_name)

        if success:
            flash(message, 'success')
            return redirect(url_for('auth.login'))

        errors = {}
        if 'Username' in message:
            errors['username'] = message
        if 'email' in message.lower():
            errors['email'] = message
        if 'Password' in message:
            errors['password'] = message

        return render_template('register.html',
                               username=username, email=email, full_name=full_name,
                               errors=errors)

    return render_template('register.html', username='', email='', full_name='', errors={})


@auth_bp.route('/logout')
@login_required
def logout():
    """User logout."""
    logout_user()
    flash('You have been logged out.', 'info')
    return redirect(url_for('auth.login'))