// ============================================================================
// SHIPMENT MANAGEMENT
// ============================================================================

let selectedOrdersForShipment = [];

// Show Shipment Tab (Regular or FTL)
function showShipmentTab(tab) {
    // Hide all shipment tabs
    document.querySelectorAll('.shipment-tab-content').forEach(el => el.classList.add('hidden'));

    // Show selected tab
    if (tab === 'regular') {
        document.getElementById('shipment-regular-tab').classList.remove('hidden');
        loadShipmentOrders();
    } else if (tab === 'ftl') {
        document.getElementById('shipment-ftl-tab').classList.remove('hidden');
        loadShipmentFTLOrders();
    }

    // Update tab button styles
    document.querySelectorAll('.shipment-tab-btn').forEach(btn => {
        if (btn.dataset.tab === tab) {
            btn.classList.add('bg-white', 'text-brand-blue', 'shadow-sm');
            btn.classList.remove('text-slate-600');
        } else {
            btn.classList.remove('bg-white', 'text-brand-blue', 'shadow-sm');
            btn.classList.add('text-slate-600');
        }
    });
}

// Load Shipment Orders
async function loadShipmentOrders() {
    try {
        const response = await fetch(`${API_BASE}/api/orders/?status=draft`);
        const data = await response.json();
        // Handle both array and paginated response formats
        const draftOrders = Array.isArray(data) ? data : (data.results || []);

        const ordersHtml = draftOrders.map(order => `
            <div class="bg-white border border-slate-200 rounded-lg p-4 hover:border-brand-blue cursor-pointer transition-all">
                <div class="flex items-center space-x-3">
                    <input type="checkbox" value="${order.id}" class="w-5 h-5 text-brand-blue border-slate-300 rounded focus:ring-brand-blue shipment-order-checkbox" onchange="handleShipmentOrderSelection()">
                    <div class="flex-1">
                        <div class="font-semibold text-slate-800">${order.order_number}</div>
                        <div class="text-sm text-slate-500">${order.recipient_name} - ${order.recipient_pincode}</div>
                        <div class="text-sm text-slate-600 mt-1">
                            Weight: ${order.applicable_weight || order.weight} kg | ${order.payment_mode.toUpperCase()}
                        </div>
                    </div>
                </div>
            </div>
        `).join('');

        document.getElementById('shipment-orders-list').innerHTML = ordersHtml || '<p class="text-slate-500 text-center py-4">No draft orders available</p>';
    } catch (error) {
        console.error('Failed to load shipment orders', error);
    }
}

// Handle Shipment Order Selection
async function handleShipmentOrderSelection() {
    const checkboxes = document.querySelectorAll('.shipment-order-checkbox:checked');
    selectedOrdersForShipment = Array.from(checkboxes).map(cb => parseInt(cb.value));

    if (selectedOrdersForShipment.length > 0) {
        await compareCarriersForShipment();
    } else {
        document.getElementById('carrier-comparison').innerHTML = `
            <div class="text-center py-12 text-slate-500">
                <svg class="w-16 h-16 mx-auto mb-4 text-slate-300" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M20 13V6a2 2 0 00-2-2H6a2 2 0 00-2 2v7m16 0v5a2 2 0 01-2 2H6a2 2 0 01-2-2v-5m16 0h-2.586a1 1 0 00-.707.293l-2.414 2.414a1 1 0 01-.707.293h-3.172a1 1 0 01-.707-.293l-2.414-2.414A1 1 0 006.586 13H4"></path>
                </svg>
                <p>Select orders to compare carrier rates</p>
            </div>
        `;
    }
}

// Compare Carriers for Shipment
async function compareCarriersForShipment() {
    try {
        const response = await fetch(`${API_BASE}/api/orders/compare-carriers/`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ order_ids: selectedOrdersForShipment })
        });

        const data = await response.json();

        const carriersHtml = data.carriers.map(carrier => `
            <label class="flex items-center p-3 border-b border-slate-100 hover:bg-slate-50 cursor-pointer rounded-lg transition-colors">
                <input type="radio" name="selected-carrier" value='${JSON.stringify({ carrier: carrier.carrier, mode: carrier.mode })}' class="w-4 h-4 text-brand-blue border-slate-300 focus:ring-brand-blue">
                <div class="ml-3 flex-1 flex items-center justify-between">
                    <div>
                        <div class="font-semibold text-slate-800">${carrier.carrier}</div>
                        <div class="text-xs text-slate-500">${carrier.mode} • ${carrier.applied_zone}</div>
                    </div>
                    <div class="text-right">
                        <div class="font-bold text-slate-800">₹${carrier.total_cost.toFixed(2)}</div>
                    </div>
                </div>
            </label>
        `).join('');

        document.getElementById('carrier-comparison').innerHTML = `
            <div class="mb-3">
                <div class="text-sm text-slate-600 mb-2">
                    <strong>${data.orders.length}</strong> order(s) selected | Total Weight: <strong>${data.total_weight} kg</strong>
                </div>
            </div>
            <div class="space-y-2 mb-4">
                ${carriersHtml}
            </div>
            <button onclick="bookSelectedCarrier()" class="w-full bg-brand-blue text-white py-3 rounded-lg hover:bg-blue-900 transition-colors font-medium">
                Book Selected Carrier
            </button>
        `;
    } catch (error) {
        toast.error('Failed to compare carriers');
    }
}

// Book Selected Carrier
async function bookSelectedCarrier() {
    const selected = document.querySelector('input[name="selected-carrier"]:checked');
    if (!selected) {
        toast.warning('Please select a carrier');
        return;
    }

    const { carrier, mode } = JSON.parse(selected.value);

    try {
        const response = await fetch(`${API_BASE}/api/orders/book-carrier/`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                order_ids: selectedOrdersForShipment,
                carrier_name: carrier,
                mode: mode
            })
        });

        if (response.ok) {
            const result = await response.json();
            toast.success(`Success! ${result.message}\nTotal Cost: ₹${result.total_cost}`);
            selectedOrdersForShipment = [];
            loadShipmentOrders();
            loadDashboard(); // Helper to refresh dashboard stats
        } else {
            const error = await response.json();
            toast.error(`Error: ${error.detail}`);
        }
    } catch (error) {
        toast.error('Failed to book carrier');
    }
}


