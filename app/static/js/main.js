/**
 * Bella Backup System - Main JavaScript
 */

// Global configuration
const API_BASE = '/api';
const REFRESH_INTERVAL = 30000;  // 30 seconds

/**
 * Initialize application
 */
document.addEventListener('DOMContentLoaded', function() {
    console.log('Bella application initialized');

    // Set active nav link
    setActiveNavLink();

    // Check Docker health
    checkDockerHealth();
});

/**
 * Set active navigation link based on current page
 */
function setActiveNavLink() {
    const pathname = window.location.pathname;
    const navLinks = document.querySelectorAll('.navbar-nav a.nav-link');

    navLinks.forEach(link => {
        link.classList.remove('active');
        const href = link.getAttribute('href');
        if (pathname === href || (pathname === '/' && href === '/')) {
            link.classList.add('active');
        }
    });
}

/**
 * Check Docker connection health
 */
function checkDockerHealth() {
    fetch(API_BASE + '/health')
        .then(response => response.json())
        .then(data => {
            if (data.status !== 'healthy') {
                console.warn('Docker health check failed:', data);
                showAlert('warning', 'Docker connection issue detected. Some features may not work.');
            }
        })
        .catch(error => {
            console.error('Health check failed:', error);
        });
}

/**
 * Format bytes to human readable format
 * @param {number} bytes - Size in bytes
 * @returns {string} Formatted size
 */
function formatBytes(bytes) {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB', 'TB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return Math.round(bytes / Math.pow(k, i) * 100) / 100 + ' ' + sizes[i];
}

/**
 * Format date to localized string
 * @param {string|Date} date - Date to format
 * @returns {string} Formatted date
 */
function formatDate(date) {
    if (!date) return '-';
    const d = new Date(date);
    return d.toLocaleDateString() + ' ' + d.toLocaleTimeString();
}

/**
 * Show alert message
 * @param {string} type - Alert type (success, danger, warning, info)
 * @param {string} message - Alert message
 * @param {number} duration - Duration in ms (0 = no auto-close)
 */
function showAlert(type, message, duration = 0) {
    const alertDiv = document.createElement('div');
    alertDiv.className = `alert alert-${type} alert-dismissible fade show`;
    alertDiv.setAttribute('role', 'alert');
    alertDiv.innerHTML = `
        ${message}
        <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
    `;

    // Insert at top of container
    const container = document.querySelector('.container-fluid');
    if (container && container.firstChild) {
        container.insertBefore(alertDiv, container.firstChild);
    }

    // Auto close after duration
    if (duration > 0) {
        setTimeout(() => {
            alertDiv.remove();
        }, duration);
    }
}

/**
 * Make API request
 * @param {string} endpoint - API endpoint
 * @param {object} options - Fetch options
 * @returns {Promise} Response promise
 */
function apiRequest(endpoint, options = {}) {
    const defaultOptions = {
        headers: {
            'Content-Type': 'application/json'
        }
    };

    const finalOptions = { ...defaultOptions, ...options };
    return fetch(API_BASE + endpoint, finalOptions);
}

/**
 * Get container status color
 * @param {string} status - Container status
 * @returns {string} Bootstrap color class
 */
function getStatusColor(status) {
    const colorMap = {
        'running': 'success',
        'exited': 'secondary',
        'paused': 'warning',
        'restarting': 'info',
        'dead': 'danger'
    };
    return colorMap[status] || 'secondary';
}

/**
 * Get backup status color
 * @param {string} status - Backup status
 * @returns {string} Bootstrap color class
 */
function getBackupStatusColor(status) {
    const colorMap = {
        'success': 'success',
        'failed': 'danger',
        'in_progress': 'warning',
        'pending': 'secondary'
    };
    return colorMap[status] || 'secondary';
}

/**
 * Show loading spinner
 * @param {Element} element - Element to show spinner in
 */
function showSpinner(element) {
    element.innerHTML = `
        <div class="text-center">
            <div class="spinner-border" role="status">
                <span class="visually-hidden">Loading...</span>
            </div>
        </div>
    `;
}

/**
 * Show empty state
 * @param {Element} element - Element to show message in
 * @param {string} message - Empty state message
 */
function showEmptyState(element, message = 'No data found') {
    element.innerHTML = `
        <div class="text-center text-muted py-5">
            <i class="bi bi-inbox" style="font-size: 3rem; opacity: 0.5;"></i>
            <p class="mt-3">${message}</p>
        </div>
    `;
}

/**
 * Show error state
 * @param {Element} element - Element to show error in
 * @param {string} error - Error message
 */
function showErrorState(element, error = 'An error occurred') {
    element.innerHTML = `
        <div class="alert alert-danger" role="alert">
            <i class="bi bi-exclamation-triangle"></i>
            <strong>Error:</strong> ${error}
        </div>
    `;
}

/**
 * Debounce function execution
 * @param {Function} func - Function to debounce
 * @param {number} wait - Wait time in ms
 * @returns {Function} Debounced function
 */
function debounce(func, wait) {
    let timeout;
    return function executedFunction(...args) {
        const later = () => {
            clearTimeout(timeout);
            func(...args);
        };
        clearTimeout(timeout);
        timeout = setTimeout(later, wait);
    };
}

/**
 * Throttle function execution
 * @param {Function} func - Function to throttle
 * @param {number} limit - Throttle limit in ms
 * @returns {Function} Throttled function
 */
function throttle(func, limit) {
    let inThrottle;
    return function(...args) {
        if (!inThrottle) {
            func.apply(this, args);
            inThrottle = true;
            setTimeout(() => inThrottle = false, limit);
        }
    };
}

/**
 * Copy text to clipboard
 * @param {string} text - Text to copy
 * @returns {Promise} Copy promise
 */
async function copyToClipboard(text) {
    try {
        await navigator.clipboard.writeText(text);
        return true;
    } catch (err) {
        console.error('Failed to copy:', err);
        return false;
    }
}

/**
 * Sanitize HTML string (basic XSS prevention)
 * @param {string} str - String to sanitize
 * @returns {string} Sanitized string
 */
function sanitizeHTML(str) {
    const map = {
        '&': '&amp;',
        '<': '&lt;',
        '>': '&gt;',
        '"': '&quot;',
        "'": '&#039;'
    };
    return str.replace(/[&<>"']/g, m => map[m]);
}

/**
 * Parse query parameters from URL
 * @returns {Object} Query parameters
 */
function getQueryParams() {
    const params = new URLSearchParams(window.location.search);
    return Object.fromEntries(params);
}

/**
 * Generate UUID v4
 * @returns {string} UUID
 */
function generateUUID() {
    return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, function(c) {
        const r = Math.random() * 16 | 0;
        const v = c === 'x' ? r : (r & 0x3 | 0x8);
        return v.toString(16);
    });
}

/**
 * Format duration in seconds to readable format
 * @param {number} seconds - Duration in seconds
 * @returns {string} Formatted duration
 */
function formatDuration(seconds) {
    if (!seconds || seconds < 0) return '-';

    if (seconds < 60) {
        return seconds.toFixed(0) + 's';
    } else if (seconds < 3600) {
        return (seconds / 60).toFixed(1) + 'm';
    } else {
        return (seconds / 3600).toFixed(1) + 'h';
    }
}

/**
 * Get relative time string (e.g., "2 hours ago")
 * @param {string|Date} date - Date to compare
 * @returns {string} Relative time string
 */
function getRelativeTime(date) {
    if (!date) return '-';

    const now = new Date();
    const d = new Date(date);
    const seconds = Math.floor((now - d) / 1000);

    if (seconds < 60) return 'just now';
    if (seconds < 3600) return Math.floor(seconds / 60) + 'm ago';
    if (seconds < 86400) return Math.floor(seconds / 3600) + 'h ago';
    if (seconds < 2592000) return Math.floor(seconds / 86400) + 'd ago';

    return d.toLocaleDateString();
}

/**
 * Confirm action with modal
 * @param {string} title - Modal title
 * @param {string} message - Confirmation message
 * @returns {Promise<boolean>} User confirmation
 */
async function confirmAction(title, message) {
    return new Promise((resolve) => {
        const html = `
            <div class="modal fade" id="confirmModal" tabindex="-1">
                <div class="modal-dialog">
                    <div class="modal-content">
                        <div class="modal-header">
                            <h5 class="modal-title">${title}</h5>
                            <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
                        </div>
                        <div class="modal-body">${message}</div>
                        <div class="modal-footer">
                            <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Cancel</button>
                            <button type="button" class="btn btn-danger" id="confirmActionBtn">Confirm</button>
                        </div>
                    </div>
                </div>
            </div>
        `;

        document.body.insertAdjacentHTML('beforeend', html);
        const modal = new bootstrap.Modal(document.getElementById('confirmModal'));

        document.getElementById('confirmActionBtn').addEventListener('click', function() {
            modal.hide();
            resolve(true);
        });

        modal._element.addEventListener('hidden.bs.modal', function() {
            document.getElementById('confirmModal').remove();
            resolve(false);
        });

        modal.show();
    });
}

// Export functions for use in other scripts (for modules)
if (typeof module !== 'undefined' && module.exports) {
    module.exports = {
        formatBytes,
        formatDate,
        showAlert,
        apiRequest,
        getStatusColor,
        getBackupStatusColor,
        showSpinner,
        showEmptyState,
        showErrorState,
        debounce,
        throttle,
        copyToClipboard,
        sanitizeHTML,
        getQueryParams,
        generateUUID,
        formatDuration,
        getRelativeTime,
        confirmAction
    };
}
