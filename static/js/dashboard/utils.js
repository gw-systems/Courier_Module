
// ============================================================================
// TOAST NOTIFICATIONS
// ============================================================================
function showToast(message, type = 'info', duration = 4000) {
    const container = document.getElementById('toast-container');
    if (!container) return;

    const toast = document.createElement('div');
    toast.className = `toast toast-${type}`;

    const icons = {
        success: '<svg class="w-6 h-6 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"></path></svg>',
        error: '<svg class="w-6 h-6 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"></path></svg>',
        warning: '<svg class="w-6 h-6 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"></path></svg>',
        info: '<svg class="w-6 h-6 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"></path></svg>'
    };

    toast.innerHTML = `
        ${icons[type] || icons.info}
        <div class="flex-1">
            <p class="font-medium">${message}</p>
        </div>
        <button class="toast-close" onclick="this.parentElement.remove()">
            <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"></path>
            </svg>
        </button>
    `;

    container.appendChild(toast);

    // Auto remove after duration
    setTimeout(() => {
        toast.classList.add('removing');
        setTimeout(() => toast.remove(), 300);
    }, duration);
}

// ============================================================================
// LOADING STATES
// ============================================================================
function showLoading(elementId, message = 'Loading...') {
    const element = document.getElementById(elementId);
    if (element) {
        element.dataset.originalContent = element.innerHTML;
        element.innerHTML = `
            <div class="flex flex-col items-center justify-center py-12">
                <div class="spinner spinner-lg mb-4"></div>
                <p class="text-slate-500">${message}</p>
            </div>
        `;
    }
}

function hideLoading(elementId) {
    const element = document.getElementById(elementId);
    if (element && element.dataset.originalContent) {
        element.innerHTML = element.dataset.originalContent;
        delete element.dataset.originalContent;
    }
}

function renderSkeletonCards(elementId, count = 3) {
    const element = document.getElementById(elementId);
    if (element) {
        const skeletons = Array(count).fill(`
            <div class="bg-white border border-slate-200 rounded-lg p-4">
                <div class="skeleton h-4 w-24 rounded mb-3"></div>
                <div class="skeleton h-5 w-40 rounded mb-2"></div>
                <div class="skeleton h-3 w-32 rounded mb-2"></div>
                <div class="skeleton h-3 w-28 rounded"></div>
            </div>
        `).join('');
        element.innerHTML = skeletons;
    }
}

// ============================================================================
// HELPERS (Depends on API_BASE global)
// ============================================================================

// Pincode Lookup Function
async function lookupPincode(type) {
    const pincodeInput = document.getElementById(`${type}_pincode`);
    const pincode = pincodeInput.value;

    if (!pincode || pincode.length !== 6) {
        document.getElementById(`${type}_city`).value = '';
        document.getElementById(`${type}_state`).value = '';
        return;
    }

    try {
        // API_BASE must be defined in the main window scope
        const response = await fetch(`${window.API_BASE || ''}/api/pincode/${pincode}/`);
        if (response.ok) {
            const data = await response.json();
            document.getElementById(`${type}_city`).value = data.city;
            document.getElementById(`${type}_state`).value = data.state;
        } else {
            document.getElementById(`${type}_city`).value = 'Invalid pincode';
            document.getElementById(`${type}_state`).value = 'Invalid pincode';
        }
    } catch (error) {
        console.error('Failed to lookup pincode', error);
        document.getElementById(`${type}_city`).value = 'Error';
        document.getElementById(`${type}_state`).value = 'Error';
    }
}

// Weight Calculation Function
function calculateWeights() {
    const weight = parseFloat(document.getElementById('weight').value) || 0;
    const length = parseFloat(document.getElementById('length').value) || 0;
    const width = parseFloat(document.getElementById('width').value) || 0;
    const height = parseFloat(document.getElementById('height').value) || 0;

    // Calculate volumetric weight: (L × W × H) ÷ 5000
    const volumetricWeight = (length * width * height) / 5000;

    // Applicable weight is max of actual and volumetric
    const applicableWeight = Math.max(weight, volumetricWeight);

    // Display results
    const volDisplay = document.getElementById('volumetric_weight_display');
    const applDisplay = document.getElementById('applicable_weight_display');

    if (volDisplay) volDisplay.textContent = volumetricWeight.toFixed(2) + ' kg';
    if (applDisplay) applDisplay.textContent = applicableWeight.toFixed(2) + ' kg';
}

// ============================================================================
// VALIDATION FUNCTIONS
// ============================================================================
function showError(inputElement, message) {
    inputElement.classList.add('border-red-500', 'border-2');
    inputElement.classList.remove('border-slate-300');

    // Remove existing error message
    const existingError = inputElement.parentElement.querySelector('.error-message');
    if (existingError) existingError.remove();

    // Add error message
    const errorDiv = document.createElement('div');
    errorDiv.className = 'error-message text-red-600 text-xs mt-1';
    errorDiv.textContent = message;
    inputElement.parentElement.appendChild(errorDiv);
}

function clearError(inputElement) {
    inputElement.classList.remove('border-red-500', 'border-2');
    inputElement.classList.add('border-slate-300');

    const errorMsg = inputElement.parentElement.querySelector('.error-message');
    if (errorMsg) errorMsg.remove();
}

function validateName(input) {
    const value = input.value.trim();
    if (!value) {
        clearError(input);
        return true;
    }

    const nameRegex = /^[a-zA-Z\s.-]+$/;
    if (!nameRegex.test(value)) {
        showError(input, 'Name must contain only letters, spaces, dots, and hyphens');
        return false;
    }
    clearError(input);
    return true;
}

function validateContact(input) {
    const value = input.value.replace(/[\s-]/g, '');

    if (!/^\d+$/.test(value)) {
        showError(input, 'Contact number must contain only digits');
        return false;
    }
    if (value.length !== 10) {
        showError(input, 'Contact number must be exactly 10 digits');
        return false;
    }
    clearError(input);
    return true;
}

function validatePhone(input) {
    const value = input.value.replace(/[\s-]/g, '');
    if (!value) {
        clearError(input);
        return true;
    }

    if (!/^\d+$/.test(value)) {
        showError(input, 'Phone number must contain only digits');
        return false;
    }
    if (value.length !== 10) {
        showError(input, 'Phone number must be exactly 10 digits');
        return false;
    }
    clearError(input);
    return true;
}

function validatePincode(input) {
    const value = input.value;

    if (!/^\d{6}$/.test(value)) {
        showError(input, 'Pincode must be exactly 6 digits');
        return false;
    }
    clearError(input);
    return true;
}

function validateEmail(input) {
    const value = input.value.trim();
    if (!value) {
        clearError(input);
        return true;
    }

    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    if (!emailRegex.test(value)) {
        showError(input, 'Invalid email format');
        return false;
    }
    clearError(input);
    return true;
}

function validateAddress(input) {
    const value = input.value.trim();
    if (!value) {
        clearError(input);
        return true;
    }

    const addressRegex = /^[a-zA-Z0-9\s.,/\-#()]+$/;
    if (!addressRegex.test(value)) {
        showError(input, 'Address contains invalid characters');
        return false;
    }
    clearError(input);
    return true;
}

function validateNumeric(input, fieldName) {
    const value = parseFloat(input.value);

    if (isNaN(value) || value <= 0) {
        showError(input, `${fieldName} must be a positive number`);
        return false;
    }
    clearError(input);
    clearError(input);
    return true;
}

// ============================================================================
// FORMATTING HELPERS
// ============================================================================
function getStatusColor(status) {
    const colors = {
        draft: 'bg-yellow-100 text-yellow-700',
        pending: 'bg-orange-100 text-orange-700',
        booked: 'bg-green-100 text-green-700',
        manifested: 'bg-indigo-100 text-indigo-700',
        picked_up: 'bg-blue-100 text-blue-700',
        out_for_delivery: 'bg-purple-100 text-purple-700',
        in_transit: 'bg-blue-100 text-blue-700',
        delivered: 'bg-green-100 text-green-700',
        cancelled: 'bg-red-100 text-red-700',
        pickup_exception: 'bg-orange-100 text-orange-700',
        ndr: 'bg-pink-100 text-pink-700',
        rto: 'bg-red-100 text-red-700'
    };
    return colors[status] || 'bg-slate-100 text-slate-700';
}

