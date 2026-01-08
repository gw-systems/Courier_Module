/**
 * Modern Toast Notification System
 * Replaces generic browser alerts with beautiful, animated toast notifications
 */

class ToastManager {
    constructor() {
        this.container = null;
        this.toasts = [];
        this.init();
    }

    init() {
        // Create container if it doesn't exist
        if (!document.querySelector('.toast-container')) {
            this.container = document.createElement('div');
            this.container.className = 'toast-container';
            document.body.appendChild(this.container);
        } else {
            this.container = document.querySelector('.toast-container');
        }
    }

    /**
     * Show a toast notification
     * @param {string} message - The message to display
     * @param {string} type - Type of toast: 'success', 'error', 'warning', 'info'
     * @param {number} duration - Duration in milliseconds (default: 4000)
     * @param {string} title - Optional title for the toast
     */
    show(message, type = 'info', duration = 4000, title = null) {
        const toast = this.createToast(message, type, title);
        this.container.appendChild(toast);
        this.toasts.push(toast);

        // Trigger animation
        requestAnimationFrame(() => {
            toast.classList.add('show');
        });

        // Auto dismiss
        if (duration > 0) {
            const progressBar = toast.querySelector('.toast-progress');
            if (progressBar) {
                progressBar.style.width = '100%';
                progressBar.style.transition = `width ${duration}ms linear`;
                requestAnimationFrame(() => {
                    progressBar.style.width = '0%';
                });
            }

            setTimeout(() => {
                this.dismiss(toast);
            }, duration);
        }

        return toast;
    }

    createToast(message, type, title) {
        const toast = document.createElement('div');
        toast.className = `toast ${type}`;

        const icon = this.getIcon(type);
        const defaultTitle = this.getDefaultTitle(type);

        toast.innerHTML = `
            <div class="toast-icon">${icon}</div>
            <div class="toast-content">
                ${title || defaultTitle ? `<div class="toast-title">${title || defaultTitle}</div>` : ''}
                <div class="toast-message">${message}</div>
            </div>
            <button class="toast-close" aria-label="Close">&times;</button>
            <div class="toast-progress"></div>
        `;

        // Close button handler
        const closeBtn = toast.querySelector('.toast-close');
        closeBtn.addEventListener('click', () => {
            this.dismiss(toast);
        });

        return toast;
    }

    getIcon(type) {
        const icons = {
            success: '✓',
            error: '✕',
            warning: '!',
            info: 'i'
        };
        return icons[type] || icons.info;
    }

    getDefaultTitle(type) {
        const titles = {
            success: 'Success',
            error: 'Error',
            warning: 'Warning',
            info: 'Info'
        };
        return titles[type] || '';
    }

    dismiss(toast) {
        toast.classList.remove('show');
        toast.classList.add('hide');

        setTimeout(() => {
            if (toast.parentNode) {
                toast.parentNode.removeChild(toast);
            }
            const index = this.toasts.indexOf(toast);
            if (index > -1) {
                this.toasts.splice(index, 1);
            }
        }, 300);
    }

    // Convenience methods
    success(message, title = null, duration = 4000) {
        return this.show(message, 'success', duration, title);
    }

    error(message, title = null, duration = 5000) {
        return this.show(message, 'error', duration, title);
    }

    warning(message, title = null, duration = 4500) {
        return this.show(message, 'warning', duration, title);
    }

    info(message, title = null, duration = 4000) {
        return this.show(message, 'info', duration, title);
    }

    // Clear all toasts
    clearAll() {
        this.toasts.forEach(toast => this.dismiss(toast));
    }
}

// Create global instance
const toast = new ToastManager();

// Also expose as window.toast for easy access
window.toast = toast;

// Override alert() to use toast (optional - can be enabled if desired)
// window.alert = function(message) {
//     toast.info(message);
// };
