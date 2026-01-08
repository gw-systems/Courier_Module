// ============================================================================
// REGULAR ORDER MANAGEMENT
// ============================================================================

let searchTimeout = null;
let allOrdersCache = [];
let selectedOrders = [];
let statusChart = null;
let ordersChart = null;

// Modal Functions
function showCreateOrderModal() {
    document.getElementById('createOrderModal').classList.remove('hidden');
}

function hideCreateOrderModal() {
    document.getElementById('createOrderModal').classList.add('hidden');

    const form = document.getElementById('createOrderForm');
    form.reset();

    // Clear edit mode
    delete form.dataset.editId;
    document.getElementById('modal-title').textContent = 'Create New Order';
    document.getElementById('submit-order-btn').textContent = 'Create Order';

    // Hide COD details (if element exists)
    const codDetails = document.getElementById('cod-details');
    if (codDetails) codDetails.classList.add('hidden');
}

// Load Dashboard Stats & Charts
async function loadDashboard() {
    try {
        const response = await fetch(`${API_BASE}/api/orders/`);
        const data = await response.json();
        // Handle both array and paginated response formats
        const orders = Array.isArray(data) ? data : (data.results || []);

        // Update stats
        const draftCount = orders.filter(o => o.status === 'draft').length;
        const bookedCount = orders.filter(o => o.status === 'booked').length;
        const cancelledCount = orders.filter(o => o.status === 'cancelled').length;
        const deliveredCount = orders.filter(o => o.status === 'delivered').length;
        const otherCount = orders.length - draftCount - bookedCount - cancelledCount - deliveredCount;

        document.getElementById('stat-total-orders').textContent = orders.length;
        document.getElementById('stat-pending-orders').textContent = draftCount;
        document.getElementById('stat-booked-orders').textContent = bookedCount;

        // Render recent orders
        const recentOrders = orders.slice(0, 5);
        const recentOrdersHtml = recentOrders.map(order => `
            <div class="border-b border-slate-200 py-3 flex items-center justify-between">
                <div class="flex-1">
                    <div class="font-medium text-slate-800">${order.order_number}</div>
                    <div class="text-sm text-slate-500">${order.recipient_name} - ${order.recipient_pincode}</div>
                </div>
                <div>
                    <span class="text-xs px-2 py-1 rounded-full ${getStatusColor(order.status)}">${order.status.toUpperCase()}</span>
                </div>
            </div>
        `).join('');

        document.getElementById('recent-orders-list').innerHTML = recentOrdersHtml || '<p class="text-slate-500 text-center py-4">No orders yet</p>';

        // Render Status Pie Chart
        const statusCtx = document.getElementById('status-chart');
        if (statusCtx) {
            if (statusChart) statusChart.destroy();
            statusChart = new Chart(statusCtx, {
                type: 'doughnut',
                data: {
                    labels: ['Draft', 'Booked', 'Cancelled', 'Delivered', 'Other'],
                    datasets: [{
                        data: [draftCount, bookedCount, cancelledCount, deliveredCount, otherCount],
                        backgroundColor: [
                            '#f59e0b', // Draft - yellow
                            '#10b981', // Booked - green
                            '#ef4444', // Cancelled - red
                            '#3b82f6', // Delivered - blue
                            '#6b7280', // Other - gray
                        ],
                        borderWidth: 0,
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {
                        legend: {
                            position: 'bottom',
                            labels: {
                                padding: 20,
                                usePointStyle: true,
                            }
                        }
                    }
                }
            });
        }

        // Render Carrier Performance Bar Chart
        const carrierCounts = {};
        orders.forEach(order => {
            if (order.selected_carrier) {
                carrierCounts[order.selected_carrier] = (carrierCounts[order.selected_carrier] || 0) + 1;
            }
        });

        const ordersCtx = document.getElementById('orders-chart');
        if (ordersCtx) {
            if (ordersChart) ordersChart.destroy();

            const carrierLabels = Object.keys(carrierCounts).slice(0, 5);
            const carrierData = carrierLabels.map(c => carrierCounts[c]);

            ordersChart = new Chart(ordersCtx, {
                type: 'bar',
                data: {
                    labels: carrierLabels.length ? carrierLabels : ['No carriers yet'],
                    datasets: [{
                        label: 'Orders by Carrier',
                        data: carrierLabels.length ? carrierData : [0],
                        backgroundColor: '#1e3a8a',
                        borderRadius: 6,
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    scales: {
                        y: {
                            beginAtZero: true,
                            ticks: {
                                stepSize: 1
                            }
                        }
                    },
                    plugins: {
                        legend: {
                            display: false
                        }
                    }
                }
            });
        }
    } catch (error) {
        console.error('Failed to load dashboard', error);
        toast.error('Failed to load dashboard data');
    }
}

// Load All Orders
async function loadAllOrders(status = null) {
    try {
        const url = status && status !== 'all' ? `${API_BASE}/api/orders/?status=${status}` : `${API_BASE}/api/orders/`;
        const response = await fetch(url);
        const data = await response.json();
        // Handle both array and paginated response formats
        const orders = Array.isArray(data) ? data : (data.results || []);

        const ordersHtml = orders.map(order => `
            <div class="bg-white border border-slate-200 rounded-lg p-4 hover:border-brand-blue transition-all relative">
                <div class="absolute top-3 left-3">
                    <input type="checkbox" value="${order.id}" data-status="${order.status}" class="w-5 h-5 text-brand-blue border-slate-300 rounded focus:ring-brand-blue order-checkbox" onchange="handleOrderSelection()">
                </div>
                <div class="pl-8">
                    <div class="flex items-start justify-between mb-3">
                        <span class="text-sm font-medium text-slate-500">${order.order_number}</span>
                        <span class="text-xs px-2 py-1 rounded-full ${getStatusColor(order.status)}">${order.status.toUpperCase()}</span>
                    </div>
                    <h4 class="font-semibold text-slate-800 mb-2">${order.recipient_name}</h4>
                    <div class="grid grid-cols-2 gap-2 text-sm mb-3">
                        <div>
                            <span class="text-slate-500">Pincode:</span>
                            <span class="ml-1 font-medium text-slate-700">${order.recipient_pincode}</span>
                        </div>
                        <div>
                            <span class="text-slate-500">Weight:</span>
                            <span class="ml-1 font-medium text-slate-700">${order.applicable_weight || order.weight} kg</span>
                        </div>
                        <div class="col-span-2">
                            <span class="text-slate-500">Payment:</span>
                            <span class="ml-1 font-medium text-slate-700">${order.payment_mode.toUpperCase()}</span>
                        </div>
                    </div>
                    ${order.selected_carrier ? `
                        <div class="text-sm border-t border-slate-200 pt-2">
                            <span class="text-slate-500">Carrier:</span>
                            <span class="ml-1 font-medium text-brand-blue">${order.selected_carrier} (₹${order.total_cost})</span>
                        </div>
                    ` : ''}
                </div>
            </div>
        `).join('');

        document.getElementById('orders-list').innerHTML = ordersHtml || '<p class="text-slate-500 col-span-full text-center py-8">No orders found</p>';
    } catch (error) {
        console.error('Failed to load orders', error);
    }
}

// Filter Orders
function filterOrders(status) {
    document.querySelectorAll('.order-filter-btn').forEach(btn => {
        btn.classList.remove('bg-white', 'text-brand-blue', 'shadow-sm');
        btn.classList.add('text-slate-600');
        if (btn.dataset.filter === status) {
            btn.classList.remove('text-slate-600');
            btn.classList.add('bg-white', 'text-brand-blue', 'shadow-sm');
        }
    });
    // Clear search when filter changes
    document.getElementById('order-search').value = '';
    loadAllOrders(status);
}

// Search Orders (client-side filtering with debounce)
async function searchOrders(query) {
    // Debounce - wait 300ms before searching
    clearTimeout(searchTimeout);
    searchTimeout = setTimeout(async () => {
        if (!query.trim()) {
            // Empty search - reload all orders
            loadAllOrders();
            return;
        }

        // If cache is empty, fetch all orders first
        if (allOrdersCache.length === 0) {
            const response = await fetch(`${API_BASE}/api/orders/`);
            const data = await response.json();
            allOrdersCache = Array.isArray(data) ? data : (data.results || []);
        }

        const searchTerm = query.toLowerCase();
        const filteredOrders = allOrdersCache.filter(order =>
            order.order_number?.toLowerCase().includes(searchTerm) ||
            order.recipient_name?.toLowerCase().includes(searchTerm) ||
            order.recipient_pincode?.toString().includes(searchTerm) ||
            order.selected_carrier?.toLowerCase().includes(searchTerm) ||
            order.sender_name?.toLowerCase().includes(searchTerm) ||
            order.status?.toLowerCase().includes(searchTerm)
        );

        renderOrdersList(filteredOrders);
    }, 300);
}

// Render orders list (extracted for reuse)
function renderOrdersList(orders) {
    const ordersHtml = orders.map(order => `
        <div class="bg-white border border-slate-200 rounded-lg p-4 hover:border-brand-blue transition-all relative">
            <div class="absolute top-3 left-3">
                <input type="checkbox" value="${order.id}" data-status="${order.status}" class="w-5 h-5 text-brand-blue border-slate-300 rounded focus:ring-brand-blue order-checkbox" onchange="handleOrderSelection()">
            </div>
            <div class="pl-8">
                <div class="flex items-start justify-between mb-3">
                    <span class="text-sm font-medium text-slate-500">${order.order_number}</span>
                    <span class="text-xs px-2 py-1 rounded-full ${getStatusColor(order.status)}">${order.status.toUpperCase()}</span>
                </div>
                <h4 class="font-semibold text-slate-800 mb-2">${order.recipient_name}</h4>
                <div class="grid grid-cols-2 gap-2 text-sm mb-3">
                    <div>
                        <span class="text-slate-500">Pincode:</span>
                        <span class="ml-1 font-medium text-slate-700">${order.recipient_pincode}</span>
                    </div>
                    <div>
                        <span class="text-slate-500">Weight:</span>
                        <span class="ml-1 font-medium text-slate-700">${order.applicable_weight || order.weight} kg</span>
                    </div>
                    <div class="col-span-2">
                        <span class="text-slate-500">Payment:</span>
                        <span class="ml-1 font-medium text-slate-700">${order.payment_mode.toUpperCase()}</span>
                    </div>
                </div>
                ${order.selected_carrier ? `
                    <div class="text-sm border-t border-slate-200 pt-2">
                        <span class="text-slate-500">Carrier:</span>
                        <span class="ml-1 font-medium text-brand-blue">${order.selected_carrier} (₹${order.total_cost})</span>
                    </div>
                ` : ''}
            </div>
        </div>
    `).join('');

    document.getElementById('orders-list').innerHTML = ordersHtml || '<p class="text-slate-500 col-span-full text-center py-8">No orders found</p>';
}

// Export Orders to CSV
async function exportOrdersCSV() {
    try {
        toast.info('Preparing CSV export...');

        // Fetch all orders
        const response = await fetch(`${API_BASE}/api/orders/`);
        const data = await response.json();
        const orders = Array.isArray(data) ? data : (data.results || []);

        if (orders.length === 0) {
            toast.warning('No orders to export');
            return;
        }

        // Define CSV headers
        const headers = [
            'Order Number', 'Status', 'Recipient Name', 'Recipient Contact',
            'Recipient Pincode', 'Recipient City', 'Recipient State',
            'Sender Name', 'Sender Pincode', 'Weight (kg)', 'Payment Mode',
            'Carrier', 'Total Cost', 'Created At'
        ];

        // Build CSV rows
        const rows = orders.map(order => [
            order.order_number || '',
            order.status || '',
            order.recipient_name || '',
            order.recipient_contact || '',
            order.recipient_pincode || '',
            order.recipient_city || '',
            order.recipient_state || '',
            order.sender_name || '',
            order.sender_pincode || '',
            order.applicable_weight || order.weight || '',
            order.payment_mode || '',
            order.selected_carrier || '',
            order.total_cost || '',
            order.created_at ? new Date(order.created_at).toLocaleDateString() : ''
        ]);

        // Convert to CSV string
        const csvContent = [
            headers.join(','),
            ...rows.map(row => row.map(cell => `"${String(cell).replace(/"/g, '""')}"`).join(','))
        ].join('\n');

        // Create and download file
        const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
        const url = URL.createObjectURL(blob);
        const link = document.createElement('a');
        link.href = url;
        link.download = `orders_export_${new Date().toISOString().split('T')[0]}.csv`;
        link.click();
        URL.revokeObjectURL(url);

        toast.success(`Exported ${orders.length} orders to CSV`);
    } catch (error) {
        console.error('Export failed:', error);
        toast.error('Failed to export orders');
    }
}

// Show Tracking Timeline
async function showTrackingTimeline() {
    const checkboxes = document.querySelectorAll('.order-checkbox:checked');
    if (checkboxes.length !== 1) {
        toast.warning('Please select exactly one order to track');
        return;
    }
    const orderId = checkboxes[0].value;
    const status = checkboxes[0].dataset.status;

    try {
        const response = await fetch(`${API_BASE}/api/orders/${orderId}/`);
        if (!response.ok) throw new Error('Failed to fetch order details');
        const order = await response.json();

        document.getElementById('track-order-number').textContent = order.order_number;
        const statusSpan = document.getElementById('track-order-status');
        statusSpan.textContent = order.status.toUpperCase();
        statusSpan.className = `text-sm font-medium px-2 py-1 rounded-full ${getStatusColor(order.status)}`;

        const timelineContainer = document.getElementById('tracking-timeline');
        timelineContainer.innerHTML = ''; // Clear previous

        const steps = [
            { key: 'draft', label: 'Order Created', desc: 'Order details entered' },
            { key: 'booked', label: 'Booked', desc: 'Carrier selected & booked' },
            { key: 'picked_up', label: 'Picked Up', desc: 'Picked up by carrier' },
            { key: 'in_transit', label: 'In Transit', desc: 'On the way to destination' },
            { key: 'out_for_delivery', label: 'Out for Delivery', desc: 'Out for final delivery' },
            { key: 'delivered', label: 'Delivered', desc: 'Successfully delivered' }
        ];

        let currentIndex = -1;

        if (order.status === 'cancelled') {
            timelineContainer.innerHTML = `
                <div class="timeline-item pb-8">
                    <div class="timeline-dot error flex items-center justify-center">
                        <svg class="w-4 h-4 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"></path></svg>
                    </div>
                    <div class="timeline-content">
                        <h4>Order Cancelled</h4>
                        <p>This order has been cancelled.</p>
                        <p class="text-xs text-slate-400 mt-1">${new Date(order.updated_at).toLocaleString()}</p>
                    </div>
                </div>
            `;
        } else {
            currentIndex = steps.findIndex(s => s.key === order.status);
            if (currentIndex === -1) {
                if (order.status === 'manifested') currentIndex = 1;
                if (order.status === 'rto') currentIndex = 3;
            }

            let html = '';
            steps.forEach((step, index) => {
                let dotClass = 'timeline-dot';
                let isCompleted = index <= currentIndex;
                let isCurrent = index === currentIndex;

                if (isCurrent) {
                    dotClass += ' current';
                } else if (isCompleted) {
                    dotClass += ' active';
                }

                let dotContent = '';
                if (isCompleted && !isCurrent) {
                    dotContent = `<svg class="w-3 h-3 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7"></path></svg>`;
                }

                html += `
                    <div class="timeline-item ${index === steps.length - 1 ? '' : 'pb-8'}">
                        <div class="${dotClass}">${dotContent}</div>
                        <div class="timeline-content">
                            <h4 class="${isCompleted ? 'text-slate-800' : 'text-slate-400'}">${step.label}</h4>
                            <p class="${isCompleted ? 'text-slate-600' : 'text-slate-400'}">${step.desc}</p>
                            ${isCurrent ? `<p class="text-xs text-brand-blue mt-1 font-medium">Current Status</p>` : ''}
                        </div>
                    </div>
                `;
            });
            timelineContainer.innerHTML = html;
        }

        document.getElementById('trackingModal').classList.remove('hidden');

    } catch (error) {
        console.error('Tracking error', error);
        toast.error('Failed to load tracking info');
    }
}

function hideTrackingModal() {
    document.getElementById('trackingModal').classList.add('hidden');
}

function downloadSelectedInvoice() {
    const checkboxes = document.querySelectorAll('.order-checkbox:checked');
    if (checkboxes.length !== 1) {
        toast.warning('Please select exactly one order to download invoice');
        return;
    }

    const orderId = checkboxes[0].value;
    window.open(`${API_BASE}/api/orders/${orderId}/invoice/`, '_blank');
}

function handleOrderSelection() {
    const checkboxes = document.querySelectorAll('.order-checkbox:checked');
    selectedOrders = Array.from(checkboxes).map(cb => ({
        id: parseInt(cb.value),
        status: cb.dataset.status
    }));

    const actionsDiv = document.getElementById('order-actions');
    const selectedCount = document.getElementById('selected-count');
    const editBtn = document.getElementById('edit-btn');
    const cancelBtn = document.getElementById('cancel-btn');
    const deleteBtn = document.getElementById('delete-btn');
    const invoiceBtn = document.getElementById('invoice-btn');
    const trackBtn = document.getElementById('track-btn');

    if (selectedOrders.length > 0) {
        actionsDiv.classList.remove('hidden');
        selectedCount.textContent = `${selectedOrders.length} selected`;

        // Show Edit only if exactly 1 order selected and it's DRAFT
        if (selectedOrders.length === 1 && selectedOrders[0].status === 'draft') {
            editBtn.classList.remove('hidden');
        } else {
            editBtn.classList.add('hidden');
        }

        // Show Invoice and Track only for single selection
        if (selectedOrders.length === 1) {
            if (invoiceBtn) invoiceBtn.classList.remove('hidden');
            if (trackBtn) trackBtn.classList.remove('hidden');
        } else {
            if (invoiceBtn) invoiceBtn.classList.add('hidden');
            if (trackBtn) trackBtn.classList.add('hidden');
        }

        // Show Cancel only if all selected orders are BOOKED
        const allBooked = selectedOrders.every(o => o.status === 'booked');
        if (allBooked) {
            cancelBtn.classList.remove('hidden');
        } else {
            cancelBtn.classList.add('hidden');
        }

        // Show Delete only if all selected orders are DRAFT or CANCELLED
        const canDelete = selectedOrders.every(o => o.status === 'draft' || o.status === 'cancelled');
        if (canDelete) {
            deleteBtn.classList.remove('hidden');
        } else {
            deleteBtn.classList.add('hidden');
        }
    } else {
        actionsDiv.classList.add('hidden');
    }
}

async function editSelectedOrder() {
    if (selectedOrders.length !== 1) return;

    const orderId = selectedOrders[0].id;
    try {
        const response = await fetch(`${API_BASE}/api/orders/${orderId}/`);

        if (!response.ok) {
            const error = await response.json();
            toast.error(`Error loading order: ${error.detail || 'Unknown error'}`);
            return;
        }

        const order = await response.json();

        const form = document.getElementById('createOrderForm');

        form.querySelector('[name="recipient_name"]').value = order.recipient_name || '';
        form.querySelector('[name="recipient_contact"]').value = order.recipient_contact || '';
        form.querySelector('[name="recipient_address"]').value = order.recipient_address || '';
        form.querySelector('[name="recipient_pincode"]').value = order.recipient_pincode || '';
        form.querySelector('[name="recipient_city"]').value = order.recipient_city || '';
        form.querySelector('[name="recipient_state"]').value = order.recipient_state || '';
        form.querySelector('[name="recipient_email"]').value = order.recipient_email || '';

        form.querySelector('[name="sender_pincode"]').value = order.sender_pincode || '';
        form.querySelector('[name="sender_name"]').value = order.sender_name || '';
        form.querySelector('[name="sender_address"]').value = order.sender_address || '';
        form.querySelector('[name="sender_phone"]').value = order.sender_phone || '';

        form.querySelector('[name="weight"]').value = order.weight || '';
        form.querySelector('[name="length"]').value = order.length || '';
        form.querySelector('[name="width"]').value = order.width || '';
        form.querySelector('[name="height"]').value = order.height || '';

        form.querySelector('[name="payment_mode"]').value = order.payment_mode || 'prepaid';
        form.querySelector('[name="order_value"]').value = order.order_value || '0';
        form.querySelector('[name="item_type"]').value = order.item_type || '';
        form.querySelector('[name="sku"]').value = order.sku || '';
        form.querySelector('[name="quantity"]').value = order.quantity || '1';
        form.querySelector('[name="item_amount"]').value = order.item_amount || '0';
        form.querySelector('[name="notes"]').value = order.notes || '';

        if (order.payment_mode === 'cod') {
            const codDetails = document.getElementById('cod-details');
            if (codDetails) codDetails.classList.remove('hidden');
        }

        calculateWeights();

        form.dataset.editId = orderId;
        const modalTitle = document.getElementById('modal-title');
        const submitBtn = document.getElementById('submit-order-btn');
        if (modalTitle) modalTitle.textContent = 'Edit Order';
        if (submitBtn) submitBtn.textContent = 'Update Order';

        showCreateOrderModal();
    } catch (error) {
        console.error('Edit error:', error);
        toast.error('Failed to load order details: ' + error.message);
    }
}

async function cancelSelectedOrders() {
    if (!confirm(`Are you sure you want to cancel ${selectedOrders.length} order(s)?`)) return;

    try {
        const promises = selectedOrders.map(order =>
            fetch(`${API_BASE}/api/orders/${order.id}/cancel/`, { method: 'POST' })
        );

        await Promise.all(promises);
        toast.success('Orders cancelled successfully!');

        selectedOrders = [];
        loadAllOrders();
        loadDashboard();
    } catch (error) {
        toast.error('Failed to cancel orders');
    }
}

async function deleteSelectedOrders() {
    if (!confirm(`Are you sure you want to delete ${selectedOrders.length} order(s)? This cannot be undone.`)) return;

    try {
        const promises = selectedOrders.map(order =>
            fetch(`${API_BASE}/api/orders/${order.id}/`, { method: 'DELETE' })
        );

        await Promise.all(promises);
        toast.success('Orders deleted successfully!');

        selectedOrders = [];
        loadAllOrders();
        loadDashboard();
    } catch (error) {
        toast.error('Failed to delete orders');
    }
}

// Init Function to bind listeners
function initOrderListeners() {
    const createOrderForm = document.getElementById('createOrderForm');
    if (createOrderForm) {
        createOrderForm.addEventListener('submit', async (e) => {
            e.preventDefault();

            // Clear all previous errors
            document.querySelectorAll('.error-message').forEach(el => el.remove());
            document.querySelectorAll('.border-red-500').forEach(el => {
                el.classList.remove('border-red-500', 'border-2');
                el.classList.add('border-slate-300');
            });

            // Validate all fields before submission
            let isValid = true;
            const form = e.target;

            // Validate names
            const recipientName = form.querySelector('[name="recipient_name"]');
            if (!validateName(recipientName)) isValid = false;

            const senderName = form.querySelector('[name="sender_name"]');
            if (senderName.value && !validateName(senderName)) isValid = false;

            // Validate contacts
            const recipientContact = form.querySelector('[name="recipient_contact"]');
            if (!validateContact(recipientContact)) isValid = false;

            const senderPhone = form.querySelector('[name="sender_phone"]');
            if (senderPhone.value && !validatePhone(senderPhone)) isValid = false;

            // Validate addresses
            const recipientAddress = form.querySelector('[name="recipient_address"]');
            if (!validateAddress(recipientAddress)) isValid = false;

            const senderAddress = form.querySelector('[name="sender_address"]');
            if (senderAddress.value && !validateAddress(senderAddress)) isValid = false;

            // Validate pincodes
            const recipientPincode = form.querySelector('[name="recipient_pincode"]');
            if (!validatePincode(recipientPincode)) isValid = false;

            const senderPincode = form.querySelector('[name="sender_pincode"]');
            if (!validatePincode(senderPincode)) isValid = false;

            // Validate email
            const email = form.querySelector('[name="recipient_email"]');
            if (email.value && !validateEmail(email)) isValid = false;

            // Validate numeric fields
            if (!validateNumeric(form.querySelector('[name="weight"]'), 'Weight')) isValid = false;
            if (!validateNumeric(form.querySelector('[name="length"]'), 'Length')) isValid = false;
            if (!validateNumeric(form.querySelector('[name="width"]'), 'Width')) isValid = false;
            if (!validateNumeric(form.querySelector('[name="height"]'), 'Height')) isValid = false;

            if (!isValid) {
                // Scroll to first error
                const firstError = document.querySelector('.border-red-500');
                if (firstError) {
                    firstError.scrollIntoView({ behavior: 'smooth', block: 'center' });
                    firstError.focus();
                }
                return;
            }

            const formData = new FormData(e.target);
            const data = {};

            formData.forEach((value, key) => {
                if (value !== '') {
                    if (['recipient_pincode', 'sender_pincode', 'quantity'].includes(key)) {
                        data[key] = parseInt(value);
                    } else if (['weight', 'length', 'width', 'height', 'order_value', 'item_amount'].includes(key)) {
                        data[key] = parseFloat(value);
                    } else {
                        data[key] = value;
                    }
                }
            });

            try {
                // Check if we're editing an existing order
                const editId = e.target.dataset.editId;
                const isEdit = editId !== undefined && editId !== '';

                const url = isEdit ? `${API_BASE}/api/orders/${editId}/` : `${API_BASE}/api/orders/`;
                const method = isEdit ? 'PATCH' : 'POST';

                const response = await fetch(url, {
                    method: method,
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(data)
                });

                if (response.ok) {
                    toast.success(isEdit ? 'Order updated successfully!' : 'Order created successfully!');

                    // Clear edit mode
                    delete e.target.dataset.editId;
                    const modalTitle = document.getElementById('modal-title');
                    const submitBtn = document.getElementById('submit-order-btn');
                    if (modalTitle) modalTitle.textContent = 'Create New Order';
                    if (submitBtn) submitBtn.textContent = 'Create Order';

                    hideCreateOrderModal();

                    // Reload data
                    try {
                        await loadAllOrders();
                        await loadDashboard();
                    } catch (reloadError) {
                        console.error('Error reloading data:', reloadError);
                    }
                } else {
                    const error = await response.json();
                    // Handle validation errors from backend
                    if (error.detail && Array.isArray(error.detail)) {
                        error.detail.forEach(err => {
                            const fieldName = err.loc[err.loc.length - 1];
                            const input = form.querySelector(`[name="${fieldName}"]`);
                            if (input) {
                                showError(input, err.msg);
                            }
                        });
                        const firstError = document.querySelector('.border-red-500');
                        if (firstError) firstError.scrollIntoView({ behavior: 'smooth', block: 'center' });
                    } else {
                        toast.error(`Error: ${typeof error.detail === 'string' ? error.detail : JSON.stringify(error.detail)}`);
                    }
                }
            } catch (error) {
                console.error('Order creation error:', error);
                toast.error('Failed to create order: ' + (error.message || 'Unknown error'));
            }
        });
    }
}

