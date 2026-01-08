// ============================================================================
// RATE CALCULATOR FUNCTIONALITY
// ============================================================================

// Toggle Tab
function switchCalculatorTab(tab) {
    document.querySelectorAll('.calc-tab-btn').forEach(btn => {
        btn.classList.remove('bg-brand-blue', 'text-white');
        btn.classList.add('text-slate-600');
        if (btn.dataset.tab === tab) {
            btn.classList.remove('text-slate-600');
            btn.classList.add('bg-brand-blue', 'text-white');
        }
    });

    document.querySelectorAll('.calc-tab-content').forEach(content => content.classList.add('hidden'));
    document.getElementById(`calc-${tab}-tab`).classList.remove('hidden');
}

// ============================================================================
// GLOBAL STATE & CONSTANTS
// ============================================================================

// State for Calculator Boxes
// Initial state: one box with default dimensions and order value
let calculatorBoxes = [
    { id: 1, weight: '', length: 10, width: 10, height: 10, orderValue: '' }
];

// Volumetric Divisor (Mirroring Backend)
// TODO: Ideally fetch this from an API endpoint on load
const VOLUMETRIC_DIVISOR = 5000;

// ============================================================================
// HELPER FUNCTIONS (Global Scope for HTML access)
// ============================================================================

// Initialize Calculator
function initCalculator() {
    console.log("Calculator Initializing...");

    // Render immediately if container exists (fix for initial load)
    if (document.getElementById('calc-box-list')) {
        console.log("Found box list container, rendering...");
        renderCalculatorBoxes();
    }

    // Hook into showSection navigation
    const originalShowSection = window.showSection;
    if (originalShowSection) {
        window.showSection = function (section) {
            originalShowSection(section);
            if (section === 'rate-calculator') {
                document.getElementById('page-title').textContent = 'Rate Calculator';
                document.getElementById('header-actions').innerHTML = '';

                // Fetch Divisor from backend if possible, else use default
                const volDisplay = document.getElementById('vol-divisor-display');
                if (volDisplay) volDisplay.textContent = VOLUMETRIC_DIVISOR;

                // Render initial boxes if not already done
                renderCalculatorBoxes();

                // Init FTL dropdowns if data ready
                if (window.ftlRatesData && Object.keys(ftlRatesData).length > 0) {
                    initFTLCalcDropdowns();
                } else if (window.loadFTLRatesData) {
                    loadFTLRatesData().then(initFTLCalcDropdowns);
                }
            }
        };
    }
}

// Render Box List
function renderCalculatorBoxes() {
    const container = document.getElementById('calc-box-list');
    if (!container) return;

    container.innerHTML = calculatorBoxes.map((box, index) => `
    <div class="relative grid grid-cols-2 md:grid-cols-5 gap-3 p-3 bg-white border border-slate-200 rounded-lg group">
        ${calculatorBoxes.length > 1 ? `
            <button type="button" onclick="removeCalculatorBox(${box.id})" 
                class="absolute -top-2 -right-2 bg-red-100 text-red-600 rounded-full w-5 h-5 flex items-center justify-center hover:bg-red-200 transition-colors shadow-sm">
                &times;
            </button>
        ` : ''}
        
        <div>
            <label class="block text-[10px] uppercase font-bold text-slate-400 mb-1">Weight (kg)</label>
            <input type="number" step="0.01" min="0.01" value="${box.weight}" 
                class="w-full px-2 py-1.5 text-sm border border-slate-300 rounded focus:ring-1 focus:ring-brand-blue"
                onchange="updateCalculatorBox(${box.id}, 'weight', this.value)" placeholder="0.00">
        </div>
        <div>
            <label class="block text-[10px] uppercase font-bold text-slate-400 mb-1">L (cm)</label>
            <input type="number" step="0.1" min="0.1" value="${box.length}" 
                class="w-full px-2 py-1.5 text-sm border border-slate-300 rounded focus:ring-1 focus:ring-brand-blue"
                onchange="updateCalculatorBox(${box.id}, 'length', this.value)" placeholder="10">
        </div>
        <div>
            <label class="block text-[10px] uppercase font-bold text-slate-400 mb-1">W (cm)</label>
            <input type="number" step="0.1" min="0.1" value="${box.width}" 
               class="w-full px-2 py-1.5 text-sm border border-slate-300 rounded focus:ring-1 focus:ring-brand-blue"
               onchange="updateCalculatorBox(${box.id}, 'width', this.value)" placeholder="10">
        </div>
        <div>
            <label class="block text-[10px] uppercase font-bold text-slate-400 mb-1">H (cm)</label>
            <input type="number" step="0.1" min="0.1" value="${box.height}" 
                class="w-full px-2 py-1.5 text-sm border border-slate-300 rounded focus:ring-1 focus:ring-brand-blue"
                onchange="updateCalculatorBox(${box.id}, 'height', this.value)" placeholder="10">
        </div>
        <div>
            <label class="block text-[10px] uppercase font-bold text-slate-400 mb-1">Value (₹)</label>
            <input type="number" step="0.01" min="0" value="${box.orderValue}" 
                class="w-full px-2 py-1.5 text-sm border border-slate-300 rounded focus:ring-1 focus:ring-brand-blue"
                onchange="updateCalculatorBox(${box.id}, 'orderValue', this.value)" placeholder="0">
        </div>
    </div>
    `).join('');

    calculateBoxTotals();
}

// Add a new box
function addCalculatorBox() {
    const newId = Math.max(...calculatorBoxes.map(b => b.id), 0) + 1;
    calculatorBoxes.push({ id: newId, weight: '', length: 10, width: 10, height: 10, orderValue: '' });
    renderCalculatorBoxes();
}

// Remove a box
function removeCalculatorBox(id) {
    if (calculatorBoxes.length <= 1) return;
    calculatorBoxes = calculatorBoxes.filter(b => b.id !== id);
    renderCalculatorBoxes();
}

// Update box field
function updateCalculatorBox(id, field, value) {
    const box = calculatorBoxes.find(b => b.id === id);
    if (box) {
        box[field] = field === 'orderValue' ? (parseFloat(value) || 0) : (parseFloat(value) || 0);

        // Handle specialized formatting if needed, but for now generic parsing works
        if (field === 'weight' && box[field] < 0) box[field] = 0;

        calculateBoxTotals();
    }
}

// Calculate totals
function calculateBoxTotals() {
    let totalActual = 0;
    let totalApplicable = 0;
    let totalOrderValue = 0;

    calculatorBoxes.forEach(box => {
        const w = parseFloat(box.weight) || 0;
        const l = parseFloat(box.length) || 0;
        const wid = parseFloat(box.width) || 0;
        const h = parseFloat(box.height) || 0;
        const val = parseFloat(box.orderValue) || 0;

        const vol = (l * wid * h) / VOLUMETRIC_DIVISOR;
        const appl = Math.max(w, vol);

        totalActual += w;
        totalApplicable += appl;
        totalOrderValue += val;
    });

    const totalActualEl = document.getElementById('total-actual-weight');
    const totalApplicableEl = document.getElementById('total-applicable-weight');
    const totalOrderValueEl = document.getElementById('total-order-value');

    if (totalActualEl) totalActualEl.textContent = totalActual.toFixed(2) + ' kg';
    if (totalApplicableEl) totalApplicableEl.textContent = totalApplicable.toFixed(2) + ' kg';
    if (totalOrderValueEl) totalOrderValueEl.value = totalOrderValue.toFixed(2);

    return { totalApplicable, totalOrderValue };
}

// Calculate Regular Rate AND Send to API
async function calculateRegularRate(e) {
    e.preventDefault();
    const form = e.target;
    const formData = new FormData(form);

    const source = formData.get('source_pincode');
    const dest = formData.get('dest_pincode');

    // Validate Boxes
    const validBoxes = calculatorBoxes.filter(b => b.weight > 0);
    if (validBoxes.length === 0) {
        toast.error("Please add at least one box with valid weight");
        return;
    }

    const isCod = formData.get('is_cod') === 'true';
    // Get total order value from state, NOT from form input which is now readonly/auto-calc
    // But we sync'd it to DOM, so form data might have it, but safer to recalculate/use state
    const totals = calculateBoxTotals();
    const orderValue = totals.totalOrderValue;

    try {
        showLoading('calc-regular-list', 'Fetching best rates...');
        document.getElementById('calc-regular-results').classList.remove('hidden');

        const requestData = {
            source_pincode: parseInt(source),
            dest_pincode: parseInt(dest),
            is_cod: isCod,
            order_value: orderValue,
            mode: 'Both',
            // Send orders list instead of single weight
            orders: validBoxes.map(b => ({
                weight: parseFloat(b.weight),
                length: parseFloat(b.length),
                width: parseFloat(b.width),
                height: parseFloat(b.height)
            }))
        };

        const response = await fetch(`${API_BASE}/api/compare-rates`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(requestData)
        });

        if (response.ok) {
            const rates = await response.json();
            renderRegularRates(rates);
        } else {
            const error = await response.json();
            document.getElementById('calc-regular-list').innerHTML = `
            <div class="text-center py-6 text-red-600 bg-red-50 rounded-lg">
                ${error.detail || 'Failed to fetch rates'}
            </div>
        `;
        }
    } catch (error) {
        console.error('Rate calc error:', error);
        document.getElementById('calc-regular-list').innerHTML = `
            <div class="text-center py-6 text-red-600 bg-red-50 rounded-lg">
                Failed to connect to server
            </div>
        `;
    }
}

function renderRegularRates(rates) {
    const container = document.getElementById('calc-regular-list');
    if (rates.length === 0) {
        container.innerHTML = '<div class="text-center py-4 text-slate-500">No carriers available for this route.</div>';
        return;
    }

    const html = rates.map(rate => `
    <div class="bg-white border border-slate-200 rounded-lg p-4 hover:border-brand-blue transition-all flex items-center justify-between">
        <div class="flex items-center space-x-4">
            <div class="w-10 h-10 rounded-full bg-slate-100 flex items-center justify-center text-slate-600 font-bold">
                ${rate.carrier.charAt(0)}
            </div>
            <div>
                <h4 class="font-semibold text-slate-800">${rate.carrier}</h4>
                <div class="text-xs text-slate-500">${rate.mode} • Zone ${rate.zone}</div>
            </div>
        </div>
        <div class="text-right">
            <div class="font-bold text-lg text-brand-blue">₹${rate.total_cost.toFixed(2)}</div>
            <div class="text-xs text-slate-500">Base: ₹${rate.breakdown.base_transport_cost.toFixed(2)}</div>
        </div>
    </div>
`).join('');

    container.innerHTML = html;
}

// ============================================================================
// FTL Calculator Logic
// ============================================================================

function updateCalcFTLDestinations() {
    const sourceCity = document.getElementById('calc-ftl-source').value;
    const destSelect = document.getElementById('calc-ftl-dest');
    const containerSelect = document.getElementById('calc-ftl-container');

    destSelect.innerHTML = '<option value="">Select Destination</option>';
    containerSelect.innerHTML = '<option value="">Select Container</option>';

    if (sourceCity && ftlRatesData[sourceCity]) {
        const destinations = ftlRatesData[sourceCity];
        Object.keys(destinations).forEach(dest => {
            const option = document.createElement('option');
            option.value = dest;
            option.textContent = dest;
            destSelect.appendChild(option);
        });
    }
    document.getElementById('calc-ftl-results').classList.add('hidden');
}

function updateCalcFTLContainerTypes() {
    const sourceCity = document.getElementById('calc-ftl-source').value;
    const destCity = document.getElementById('calc-ftl-dest').value;
    const containerSelect = document.getElementById('calc-ftl-container');

    containerSelect.innerHTML = '<option value="">Select Container</option>';

    if (sourceCity && destCity && ftlRatesData[sourceCity] && ftlRatesData[sourceCity][destCity]) {
        const containerTypes = ftlRatesData[sourceCity][destCity];
        containerTypes.forEach(type => {
            const option = document.createElement('option');
            option.value = type;
            option.textContent = type;
            containerSelect.appendChild(option);
        });
    }
    document.getElementById('calc-ftl-results').classList.add('hidden');
}

// Populate Source on Load (triggered by showSection)
function initFTLCalcDropdowns() {
    const sourceSelect = document.getElementById('calc-ftl-source');
    if (!sourceSelect) return;

    if (sourceSelect.options.length <= 1 && Object.keys(ftlRatesData).length > 0) {
        Object.keys(ftlRatesData).forEach(city => {
            const option = document.createElement('option');
            option.value = city;
            option.textContent = city;
            sourceSelect.appendChild(option);
        });
    }
}

async function calculateFTLRateSubmit(e) {
    e.preventDefault();
    const source = document.getElementById('calc-ftl-source').value;
    const dest = document.getElementById('calc-ftl-dest').value;
    const type = document.getElementById('calc-ftl-container').value;

    try {
        const response = await fetch(`${API_BASE}/api/ftl/calculate-rate`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                source_city: source,
                destination_city: dest,
                container_type: type
            })
        });

        if (response.ok) {
            const data = await response.json();
            document.getElementById('calc-ftl-results').classList.remove('hidden');

            // User Request: Base Price = Base + Escalation
            document.getElementById('calc-ftl-base').textContent = '₹' + data.price_with_escalation.toFixed(2);
            document.getElementById('calc-ftl-gst').textContent = '₹' + data.gst_amount.toFixed(2);
            document.getElementById('calc-ftl-total').textContent = '₹' + data.total_price.toFixed(2);
        } else {
            const error = await response.json();
            toast.error(error.detail || 'Calculation failed');
        }
    } catch (err) {
        console.error(err);
        toast.error('Failed to calculate FTL rate');
    }
}
