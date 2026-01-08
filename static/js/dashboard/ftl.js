
// ============================================================================
// FTL FUNCTIONALITY
// ============================================================================

let ftlRatesData = {};
let selectedFTLOrders = [];
let selectedShipmentFTLOrders = []; // Moved here as it belongs to FTL domain

// Load FTL routes from backend API
async function loadFTLRatesData() {
    try {
        const response = await fetch(`${API_BASE}/api/ftl/routes`);
        if (response.ok) {
            ftlRatesData = await response.json();

            // Update source city dropdown if it exists (Modal)
            const sourceCitySelect = document.getElementById('ftl-source-city');
            if (sourceCitySelect) {
                // Clear existing options except the first one
                sourceCitySelect.innerHTML = '<option value="">Select Source City</option>';
                Object.keys(ftlRatesData).forEach(city => {
                    const option = document.createElement('option');
                    option.value = city;
                    option.textContent = city;
                    sourceCitySelect.appendChild(option);
                });
            }

            // Also init Rate Calculator FTL dropdowns if they exist
            // Should be handled by calculator init, but data is here.
        }
    } catch (error) {
        console.error('Failed to load FTL rates:', error);
    }
}

// Update destination cities based on source city selection
function updateFTLDestinations(isEdit = false) {
    const sourceCity = document.getElementById('ftl-source-city').value;
    const destSelect = document.getElementById('ftl-destination-city');
    const containerSelect = document.getElementById('ftl-container-type');

    destSelect.innerHTML = '<option value="">Select Destination City</option>';
    containerSelect.innerHTML = '<option value="">Select Container Type</option>';

    if (sourceCity && ftlRatesData[sourceCity]) {
        const destinations = ftlRatesData[sourceCity];
        Object.keys(destinations).forEach(dest => {
            const option = document.createElement('option');
            option.value = dest;
            option.textContent = dest;
            destSelect.appendChild(option);
        });
    }

    // Clear pricing when source changes unless editing
    if (!isEdit) {
        document.getElementById('ftl-pricing-breakdown').classList.add('hidden');
    }
}

// Update container types based on source and destination selection
function updateFTLContainerTypes() {
    const sourceCity = document.getElementById('ftl-source-city').value;
    const destCity = document.getElementById('ftl-destination-city').value;
    const containerSelect = document.getElementById('ftl-container-type');

    containerSelect.innerHTML = '<option value="">Select Container Type</option>';

    if (sourceCity && destCity && ftlRatesData[sourceCity] && ftlRatesData[sourceCity][destCity]) {
        const containerTypes = ftlRatesData[sourceCity][destCity];
        containerTypes.forEach(type => {
            const option = document.createElement('option');
            option.value = type;
            option.textContent = type;
            containerSelect.appendChild(option);
        });
    }

    // Clear pricing when destination changes
    document.getElementById('ftl-pricing-breakdown').classList.add('hidden');
}

// Calculate FTL rate (Modal Version)
async function calculateFTLRate() {
    const sourceCity = document.getElementById('ftl-source-city').value;
    const destCity = document.getElementById('ftl-destination-city').value;
    const containerType = document.getElementById('ftl-container-type').value;

    if (!sourceCity || !destCity || !containerType) {
        document.getElementById('ftl-pricing-breakdown').classList.add('hidden');
        return;
    }

    try {
        const response = await fetch(`${API_BASE}/api/ftl/calculate-rate`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                source_city: sourceCity,
                destination_city: destCity,
                container_type: containerType
            })
        });

        if (response.ok) {
            const data = await response.json();
            document.getElementById('ftl-pricing-breakdown').classList.remove('hidden');
            // Populate breakdown - escalation hidden from UI
            if (data.base_price) document.getElementById('ftl-base-price').textContent = '₹' + data.base_price.toFixed(2);
            document.getElementById('ftl-gst').textContent = '₹' + data.gst_amount.toFixed(2);
            document.getElementById('ftl-total-price').textContent = '₹' + data.total_price.toFixed(2);
        } else {
            const error = await response.json();
            toast.error(`Error: ${error.detail}`);
            document.getElementById('ftl-pricing-breakdown').classList.add('hidden');
        }
    } catch (error) {
        console.error('Failed to calculate FTL rate:', error);
        toast.error('Failed to calculate rate');
    }
}

// Show/Hide FTL Modal
function showCreateFTLModal() {
    document.getElementById('createFTLModal').classList.remove('hidden');
    loadFTLRatesData();
}

function hideCreateFTLModal() {
    document.getElementById('createFTLModal').classList.add('hidden');
    const form = document.getElementById('createFTLForm');
    form.reset();
    delete form.dataset.editId;
    document.getElementById('ftl-modal-title').textContent = 'Create FTL Order';
    document.getElementById('submit-ftl-btn').textContent = 'Create FTL Order';
    document.getElementById('ftl-pricing-breakdown').classList.add('hidden');
}

// Create/Update FTL Order (Event Listener attachment logic needed, 
// usually done by `document.addEventListener` but here we'll define a handler function to be attached or called)
// Since the HTML already has `onsubmit` or we were adding event listener via JS at bottom.
// We should expose a function to init listeners or run this inline if script is loaded at bottom.
// We will assign it to an init function called by main.

function initFTLListeners() {
    const form = document.getElementById('createFTLForm');
    if (form) {
        form.removeEventListener('submit', handleFTLSubmit); // Prevent duplicates
        form.addEventListener('submit', handleFTLSubmit);
    }
}

async function handleFTLSubmit(e) {
    e.preventDefault();

    const formData = new FormData(e.target);
    const data = {};

    formData.forEach((value, key) => {
        if (value !== '') {
            if (['source_pincode', 'destination_pincode'].includes(key)) {
                data[key] = parseInt(value);
            } else {
                data[key] = value;
            }
        }
    });

    try {
        const editId = e.target.dataset.editId;
        const isEdit = editId !== undefined && editId !== '';

        const url = isEdit ? `${API_BASE}/api/ftl-orders/${editId}/` : `${API_BASE}/api/ftl-orders/`;
        const method = isEdit ? 'PATCH' : 'POST';

        const response = await fetch(url, {
            method: method,
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(data)
        });

        if (response.ok) {
            toast.success(isEdit ? 'FTL Order updated successfully!' : 'FTL Order created successfully!');
            hideCreateFTLModal();
            loadFTLOrders();
            // Also reload shipment FTL orders if that tab is visible
            const shipTab = document.getElementById('shipment-ftl-tab');
            if (shipTab && !shipTab.classList.contains('hidden')) {
                loadShipmentFTLOrders();
            }
        } else {
            const error = await response.json();
            let errorMessage = '';

            if (error.detail) {
                errorMessage = typeof error.detail === 'string' ? error.detail : JSON.stringify(error.detail);
            } else {
                const errors = [];
                for (const [field, messages] of Object.entries(error)) {
                    const fieldName = field.charAt(0).toUpperCase() + field.slice(1).replace('_', ' ');
                    const message = Array.isArray(messages) ? messages.join(', ') : messages;
                    errors.push(`${fieldName}: ${message}`);
                }
                errorMessage = errors.join('\n');
            }

            toast.error(`Error:\n${errorMessage}`);
        }
    } catch (error) {
        console.error('FTL order creation error:', error);
        toast.error('Failed to create FTL order: ' + error.message);
    }
}

// Load FTL Orders
async function loadFTLOrders(status = null) {
    try {
        const url = status && status !== 'all' ? `${API_BASE}/api/ftl-orders/?status=${status}` : `${API_BASE}/api/ftl-orders/`;
        const response = await fetch(url);
        const data = await response.json();
        const orders = Array.isArray(data) ? data : (data.results || []);

        const ordersHtml = orders.map(order => `
            <div class="bg-white border border-slate-200 rounded-lg p-4 hover:border-brand-blue transition-all relative">
                <div class="absolute top-3 left-3">
                    <input type="checkbox" value="${order.id}" data-status="${order.status}" class="w-5 h-5 text-brand-blue border-slate-300 rounded focus:ring-brand-blue ftl-order-checkbox" onchange="handleFTLOrderSelection()">
                </div>
                <div class="pl-8">
                    <div class="flex items-start justify-between mb-3">
                        <span class="text-sm font-medium text-slate-500">${order.order_number}</span>
                        <span class="text-xs px-2 py-1 rounded-full ${getStatusColor(order.status)}">${order.status.toUpperCase()}</span>
                    </div>
                    <h4 class="font-semibold text-slate-800 mb-2">${order.name}</h4>
                    <div class="grid grid-cols-2 gap-2 text-sm mb-3">
                        <div class="col-span-2">
                            <span class="text-slate-500">Route:</span>
                            <span class="ml-1 font-medium text-slate-700">${order.source_city} → ${order.destination_city}</span>
                        </div>
                        <div>
                            <span class="text-slate-500">Container:</span>
                            <span class="ml-1 font-medium text-slate-700">${order.container_type}</span>
                        </div>
                        <div>
                            <span class="text-slate-500">Total:</span>
                            <span class="ml-1 font-medium text-brand-blue">₹${parseFloat(order.total_price).toFixed(2)}</span>
                        </div>
                    </div>
                </div>
            </div>
        `).join('');

        const list = document.getElementById('ftl-orders-list');
        if (list) list.innerHTML = ordersHtml || '<p class="text-slate-500 col-span-full text-center py-8">No FTL orders found</p>';
    } catch (error) {
        console.error('Failed to load FTL orders', error);
    }
}

// Filter FTL Orders
function filterFTLOrders(status) {
    document.querySelectorAll('.ftl-filter-btn').forEach(btn => {
        btn.classList.remove('bg-white', 'text-brand-blue', 'shadow-sm');
        btn.classList.add('text-slate-600');
        if (btn.dataset.filter === status) {
            btn.classList.remove('text-slate-600');
            btn.classList.add('bg-white', 'text-brand-blue', 'shadow-sm');
        }
    });
    loadFTLOrders(status);
}

// Handle FTL Order Selection
function handleFTLOrderSelection() {
    const checkboxes = document.querySelectorAll('.ftl-order-checkbox:checked');
    selectedFTLOrders = Array.from(checkboxes).map(cb => ({
        id: parseInt(cb.value),
        status: cb.dataset.status
    }));

    const actionsDiv = document.getElementById('ftl-order-actions');
    const selectedCount = document.getElementById('ftl-selected-count');
    const editBtn = document.getElementById('ftl-edit-btn');
    const deleteBtn = document.getElementById('ftl-delete-btn');
    const cancelBtn = document.getElementById('ftl-cancel-btn');

    if (selectedFTLOrders.length > 0) {
        actionsDiv.classList.remove('hidden');
        selectedCount.textContent = `${selectedFTLOrders.length} selected`;

        // Show Edit only if exactly 1 order selected and it's DRAFT
        if (selectedFTLOrders.length === 1 && selectedFTLOrders[0].status === 'draft') {
            editBtn.classList.remove('hidden');
        } else {
            editBtn.classList.add('hidden');
        }

        // Show Cancel only if all selected orders are BOOKED
        const allBooked = selectedFTLOrders.every(o => o.status === 'booked');
        if (allBooked) {
            cancelBtn.classList.remove('hidden');
        } else {
            cancelBtn.classList.add('hidden');
        }

        // Show Delete only if all selected orders are DRAFT or CANCELLED
        const canDelete = selectedFTLOrders.every(o => o.status === 'draft' || o.status === 'cancelled');
        if (canDelete) {
            deleteBtn.classList.remove('hidden');
        } else {
            deleteBtn.classList.add('hidden');
        }
    } else {
        actionsDiv.classList.add('hidden');
    }
}

// Edit FTL Order
async function editSelectedFTLOrder() {
    if (selectedFTLOrders.length !== 1) return;

    const orderId = selectedFTLOrders[0].id;
    try {
        const response = await fetch(`${API_BASE}/api/ftl-orders/${orderId}/`);

        if (!response.ok) {
            const error = await response.json();
            alert(`Error loading order: ${error.detail || 'Unknown error'}`);
            return;
        }

        const order = await response.json();
        const form = document.getElementById('createFTLForm');

        // Populate fields
        form.querySelector('[name="name"]').value = order.name || '';
        form.querySelector('[name="phone"]').value = order.phone || '';
        form.querySelector('[name="email"]').value = order.email || '';
        form.querySelector('[name="source_city"]').value = order.source_city || '';

        // Trigger destination update before setting destination
        await updateFTLDestinations(true);

        form.querySelector('[name="destination_city"]').value = order.destination_city || '';
        form.querySelector('[name="source_pincode"]').value = order.source_pincode || '';
        form.querySelector('[name="source_address"]').value = order.source_address || '';
        form.querySelector('[name="destination_pincode"]').value = order.destination_pincode || '';
        form.querySelector('[name="destination_address"]').value = order.destination_address || '';
        form.querySelector('[name="container_type"]').value = order.container_type || '';
        form.querySelector('[name="notes"]').value = order.notes || '';

        // Add edit ID
        form.dataset.editId = orderId;
        document.getElementById('ftl-modal-title').textContent = 'Edit FTL Order';
        document.getElementById('submit-ftl-btn').textContent = 'Update FTL Order';

        // Show modal
        document.getElementById('createFTLModal').classList.remove('hidden');
        calculateFTLRate();

    } catch (error) {
        console.error('Edit error:', error);
        toast.error('Failed to load order details: ' + error.message);
    }
}

async function cancelSelectedFTLOrders() {
    if (!confirm(`Are you sure you want to cancel ${selectedFTLOrders.length} FTL order(s)?`)) return;

    try {
        const promises = selectedFTLOrders.map(order =>
            fetch(`${API_BASE}/api/ftl-orders/${order.id}/cancel/`, { method: 'POST' })
        );

        await Promise.all(promises);
        toast.success('FTL Orders cancelled successfully!');
        selectedFTLOrders = [];
        loadFTLOrders();
    } catch (error) {
        toast.error('Failed to cancel FTL orders');
    }
}

async function deleteSelectedFTLOrders() {
    if (!confirm(`Are you sure you want to delete ${selectedFTLOrders.length} FTL order(s)? This cannot be undone.`)) return;

    try {
        const promises = selectedFTLOrders.map(order =>
            fetch(`${API_BASE}/api/ftl-orders/${order.id}/`, { method: 'DELETE' })
                .then(response => {
                    if (!response.ok) {
                        return response.json().then(err => {
                            throw new Error(err.detail || `Failed to delete order ${order.id}`);
                        });
                    }
                    return response;
                })
        );

        await Promise.all(promises);
        toast.success('FTL orders deleted successfully!');
        selectedFTLOrders = [];
        loadFTLOrders();
    } catch (error) {
        console.error('Delete error:', error);
        showToast(error.message || 'Failed to delete FTL orders. Only DRAFT or CANCELLED orders can be deleted.', 'error');
    }
}

// Shipment Section Helpers for FTL

// Load FTL Orders in Shipment Section
async function loadShipmentFTLOrders() {
    try {
        // Fetch only DRAFT FTL orders for shipment section
        const response = await fetch(`${API_BASE}/api/ftl-orders/?status=draft`);
        const data = await response.json();
        const orders = Array.isArray(data) ? data : (data.results || []);

        const ordersHtml = orders.map(order => `
            <div class="bg-white border border-slate-200 rounded-lg p-4 hover:border-brand-blue cursor-pointer transition-all relative" onclick="toggleFTLOrderSelection(event, this)">
                <div class="absolute top-3 left-3">
                    <input type="checkbox" value="${order.id}" data-status="${order.status}" class="w-5 h-5 text-brand-blue border-slate-300 rounded focus:ring-brand-blue shipment-ftl-order-checkbox" onchange="handleShipmentFTLOrderSelection()" onclick="event.stopPropagation()">
                </div>
                <div class="pl-8">
                    <div class="flex items-start justify-between mb-3">
                        <span class="text-sm font-medium text-slate-500">${order.order_number}</span>
                        <span class="text-xs px-2 py-1 rounded-full ${getStatusColor(order.status)}">${order.status.toUpperCase()}</span>
                    </div>
                    <h4 class="font-semibold text-slate-800 mb-2">${order.name}</h4>
                    <div class="grid grid-cols-2 gap-2 text-sm mb-3">
                        <div class="col-span-2">
                            <span class="text-slate-500">Route:</span>
                            <span class="ml-1 font-medium text-slate-700">${order.source_city} → ${order.destination_city}</span>
                        </div>
                        <div class="col-span-2">
                            <span class="text-slate-500">Source Address:</span>
                            <span class="ml-1 text-slate-700">${order.source_address || 'Not provided'}</span>
                        </div>
                        <div>
                            <span class="text-slate-500">Container:</span>
                            <span class="ml-1 font-medium text-slate-700">${order.container_type}</span>
                        </div>
                        <div>
                            <span class="text-slate-500">Total:</span>
                            <span class="ml-1 font-medium text-brand-blue">₹${parseFloat(order.total_price).toFixed(2)}</span>
                        </div>
                    </div>
                </div>
            </div>
        `).join('');

        document.getElementById('shipment-ftl-orders-list').innerHTML = ordersHtml || '<p class="text-slate-500 col-span-full text-center py-8">No draft FTL orders</p>';
    } catch (error) {
        console.error('Failed to load shipment FTL orders', error);
    }
}

function handleShipmentFTLOrderSelection() {
    const checkboxes = document.querySelectorAll('.shipment-ftl-order-checkbox:checked');
    selectedShipmentFTLOrders = Array.from(checkboxes).map(cb => ({
        id: parseInt(cb.value),
        status: cb.dataset.status
    }));

    const actionsDiv = document.getElementById('shipment-ftl-actions');
    const countSpan = document.getElementById('shipment-ftl-selected-count');
    const bookBtn = document.getElementById('shipment-ftl-book-btn');

    if (selectedShipmentFTLOrders.length > 0) {
        actionsDiv.classList.remove('hidden');
        countSpan.textContent = `${selectedShipmentFTLOrders.length} selected`;
        // Only show Book button - all orders are draft
        bookBtn.classList.remove('hidden');
    } else {
        actionsDiv.classList.add('hidden');
    }
}

async function deleteSelectedShipmentFTLOrders() {
    if (selectedShipmentFTLOrders.length === 0) {
        toast.warning('Please select orders to delete');
        return;
    }

    if (!confirm(`Are you sure you want to delete ${selectedShipmentFTLOrders.length} order(s)?`)) return;

    try {
        const promises = selectedShipmentFTLOrders.map(order =>
            fetch(`${API_BASE}/api/ftl-orders/${order.id}/`, { method: 'DELETE' })
                .then(response => {
                    if (!response.ok) {
                        return response.json().then(err => {
                            throw new Error(err.detail || `Failed to delete order ${order.id}`);
                        });
                    }
                    return response;
                })
        );

        await Promise.all(promises);
        toast.success('FTL orders deleted successfully!');

        selectedShipmentFTLOrders = [];
        loadShipmentFTLOrders();
    } catch (error) {
        console.error('Failed to delete FTL orders', error);
        showToast(error.message || 'Failed to delete FTL orders. Only DRAFT or CANCELLED orders can be deleted.', 'error');
    }
}

async function bookSelectedFTLOrders() {
    if (selectedShipmentFTLOrders.length === 0) {
        toast.warning('Please select orders to book');
        return;
    }

    const nonDraftOrders = selectedShipmentFTLOrders.filter(order => order.status !== 'draft');
    if (nonDraftOrders.length > 0) {
        toast.warning('Only DRAFT orders can be booked. Please select only DRAFT orders.');
        return;
    }

    if (!confirm(`Are you sure you want to book ${selectedShipmentFTLOrders.length} FTL order(s)?`)) return;

    try {
        const orderIds = selectedShipmentFTLOrders.map(order => order.id);

        const response = await fetch(`${API_BASE}/api/ftl-orders/book/`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ order_ids: orderIds })
        });

        if (response.ok) {
            const result = await response.json();
            toast.success(result.message || 'FTL orders booked successfully!');
            selectedShipmentFTLOrders = [];
            loadShipmentFTLOrders();
            loadFTLOrders(); // Refresh main list too
        } else {
            const error = await response.json();
            toast.error(`Error: ${error.detail || 'Failed to book orders'}`);
        }
    } catch (error) {
        console.error('Failed to book FTL orders', error);
        toast.error('Failed to book FTL orders: ' + error.message);
    }
}

async function editSelectedShipmentFTLOrder() {
    if (selectedShipmentFTLOrders.length !== 1) {
        toast.warning('Please select exactly one FTL order to edit');
        return;
    }

    const orderId = selectedShipmentFTLOrders[0].id;
    try {
        const response = await fetch(`${API_BASE}/api/ftl-orders/${orderId}/`);

        if (!response.ok) {
            const error = await response.json();
            alert(`Error loading order: ${error.detail || 'Unknown error'}`);
            return;
        }

        const order = await response.json();
        const form = document.getElementById('createFTLForm');

        // Populate fields
        form.querySelector('[name="name"]').value = order.name || '';
        form.querySelector('[name="phone"]').value = order.phone || '';
        form.querySelector('[name="email"]').value = order.email || '';
        form.querySelector('[name="source_city"]').value = order.source_city || '';

        // Trigger destination update before setting destination
        await updateFTLDestinations(true);

        form.querySelector('[name="destination_city"]').value = order.destination_city || '';
        form.querySelector('[name="source_pincode"]').value = order.source_pincode || '';
        form.querySelector('[name="source_address"]').value = order.source_address || '';
        form.querySelector('[name="destination_pincode"]').value = order.destination_pincode || '';
        form.querySelector('[name="destination_address"]').value = order.destination_address || '';
        form.querySelector('[name="container_type"]').value = order.container_type || '';
        form.querySelector('[name="notes"]').value = order.notes || '';

        // Add edit ID
        form.dataset.editId = orderId;
        document.getElementById('ftl-modal-title').textContent = 'Edit FTL Order';
        document.getElementById('submit-ftl-btn').textContent = 'Update FTL Order';

        // Show modal
        document.getElementById('createFTLModal').classList.remove('hidden');
        calculateFTLRate();
    } catch (error) {
        console.error('Failed to load FTL order for editing', error);
        toast.error('Failed to load order: ' + error.message);
    }
}

// Helper to toggle FTL order selection when clicking the card
function toggleFTLOrderSelection(event, cardElement) {
    // If user clicked a button or link inside the card, don't toggle
    if (event.target.tagName === 'BUTTON' || event.target.tagName === 'A' || event.target.closest('button')) {
        return;
    }

    const checkbox = cardElement.querySelector('.shipment-ftl-order-checkbox');
    if (checkbox) {
        checkbox.checked = !checkbox.checked;
        // Trigger the manual change handler
        handleShipmentFTLOrderSelection();
    }
}

