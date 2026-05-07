/**
 * Auth JavaScript - Auth state management and utilities
 */

// Show toast notification (reuses existing toast system from main app)
function showToast(message, type = 'info') {
    let toast = document.getElementById('toast');
    if (!toast) {
        toast = document.createElement('div');
        toast.className = 'toast';
        toast.id = 'toast';
        document.body.appendChild(toast);
    }
    const toastMessage = document.getElementById('toastMessage') || toast;
    toastMessage.textContent = message;
    toast.className = `toast toast-${type} show`;
    setTimeout(() => {
        toast.classList.remove('show');
    }, 3000);
}

/**
 * Check if user is authenticated
 * Returns user object if authenticated, null otherwise
 */
async function checkAuth() {
    try {
        const response = await fetch('/api/auth/me');
        if (response.ok) {
            return await response.json();
        }
        return null;
    } catch (error) {
        console.error('Auth check failed:', error);
        return null;
    }
}

/**
 * Get the current user from the page context
 */
function getCurrentUser() {
    const userElement = document.getElementById('currentUser');
    if (userElement && userElement.dataset.user) {
        try {
            return JSON.parse(userElement.dataset.user);
        } catch (e) {
            return null;
        }
    }
    return null;
}

/**
 * Require authentication - redirect to login if not authenticated
 */
async function requireAuth() {
    const user = await checkAuth();
    if (!user) {
        window.location.href = '/auth/login?next=' + encodeURIComponent(window.location.pathname);
        return false;
    }
    return user;
}

/**
 * Require admin role - redirect if not admin
 */
async function requireAdmin() {
    const user = await requireAuth();
    if (user && user.role !== 'admin') {
        window.location.href = '/';
        return false;
    }
    return user;
}

/**
 * Form validation helper
 */
function validateForm(formElement) {
    let isValid = true;
    const inputs = formElement.querySelectorAll('input[required], select[required]');

    inputs.forEach(input => {
        const errorSpan = formElement.querySelector(`.error-${input.name}`);
        if (errorSpan) errorSpan.remove();

        if (!input.value.trim()) {
            isValid = false;
            input.classList.add('input-error');

            const error = document.createElement('span');
            error.className = `error-text error-${input.name}`;
            error.textContent = 'This field is required';
            input.parentNode.appendChild(error);
        } else {
            input.classList.remove('input-error');
        }
    });

    return isValid;
}

/**
 * Password strength checker
 */
function checkPasswordStrength(password) {
    let strength = 0;
    const feedback = [];

    if (password.length >= 6) {
        strength++;
    } else {
        feedback.push('At least 6 characters');
    }

    if (password.length >= 8) {
        strength++;
    }

    if (/[a-z]/.test(password) && /[A-Z]/.test(password)) {
        strength++;
    }

    if (/\d/.test(password)) {
        strength++;
    }

    if (/[^a-zA-Z0-9]/.test(password)) {
        strength++;
    }

    return {
        score: strength,
        feedback: feedback,
        isWeak: strength < 2
    };
}

/**
 * Confirm dialog helper
 */
function confirmAction(message, title = 'Confirm') {
    return confirm(message);
}

/**
 * Format date helper
 */
function formatDate(isoString) {
    const date = new Date(isoString);
    return date.toLocaleDateString('en-US', {
        year: 'numeric',
        month: 'short',
        day: 'numeric',
        hour: '2-digit',
        minute: '2-digit'
    });
}

/**
 * Escape HTML to prevent XSS
 */
function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

// Auto-dismiss alerts after 5 seconds
document.addEventListener('DOMContentLoaded', () => {
    const alerts = document.querySelectorAll('.alert');
    alerts.forEach(alert => {
        setTimeout(() => {
            alert.style.transition = 'opacity 0.3s ease';
            alert.style.opacity = '0';
            setTimeout(() => alert.remove(), 300);
        }, 5000);
    });
});

// Add password strength indicator on register page
document.addEventListener('DOMContentLoaded', () => {
    const passwordInput = document.getElementById('password');
    if (passwordInput) {
        passwordInput.addEventListener('input', (e) => {
            const strength = checkPasswordStrength(e.target.value);
            let indicator = document.getElementById('passwordStrength');
            if (!indicator) {
                indicator = document.createElement('div');
                indicator.id = 'passwordStrength';
                indicator.style.marginTop = '4px';
                indicator.style.fontSize = '0.8rem';
                e.target.parentNode.appendChild(indicator);
            }

            if (e.target.value.length === 0) {
                indicator.textContent = '';
                return;
            }

            const colors = ['#ef4444', '#f59e0b', '#eab308', '#22c55e', '#10b981'];
            indicator.textContent = `Password strength: ${['Weak', 'Fair', 'Good', 'Strong', 'Very Strong'][Math.min(strength.score - 1, 4)] || 'Weak'}`;
            indicator.style.color = colors[Math.min(strength.score - 1, 4)] || colors[0];
        });
    }
});
