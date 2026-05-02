const API_BASE = '';
const IS_ADMIN = window.IS_ADMIN === true || window.IS_ADMIN === 'true';

const Cache = {
    _store: {},
    set(key, data) { this._store[key] = { data, ts: Date.now() }; },
    get(key, maxAgeMs = 30000) {
        const entry = this._store[key];
        if (!entry) return null;
        if (Date.now() - entry.ts > maxAgeMs) {
            delete this._store[key];
            return null;
        }
        return entry.data;
    },
    invalidate(...keys) { keys.forEach(k => delete this._store[k]); }
};

const _inflight = {};
let _adminTrainersCache = [];
let _adminTrainersPromise = null;
let _selectedClientTrainerId = '';
let currentFilter = 'all';
let _clientsCache = null;
let _paymentsCache = null;

async function apiFetch(url, opts) {
    if (!opts && _inflight[url]) return _inflight[url];
    const p = fetch(url, opts).then(r => {
        delete _inflight[url];
        return r;
    });
    if (!opts) _inflight[url] = p;
    return p;
}

function formatCurrency(amount) {
    const n = Number(amount || 0);
    return 'INR ' + n.toLocaleString('en-IN', { minimumFractionDigits: 0, maximumFractionDigits: 0 });
}

function formatDate(dateStr) {
    if (!dateStr) return '-';
    const d = new Date(dateStr + 'T00:00:00');
    return d.toLocaleDateString('en-IN', { day: 'numeric', month: 'short', year: 'numeric' });
}

function formatTimeSlot(timeStr) {
    if (!timeStr) return '';
    const [h24, min] = timeStr.split(':');
    let h = parseInt(h24, 10);
    const ampm = h >= 12 ? 'PM' : 'AM';
    h = h % 12 || 12;
    const endH24 = parseInt(h24, 10) + 1;
    const endAmpm = endH24 >= 12 && endH24 < 24 ? 'PM' : 'AM';
    const endH = endH24 % 12 || 12;
    return `${h}:${min} ${ampm} - ${endH}:${min} ${endAmpm}`;
}

function timeHue(timeStr) {
    if (!timeStr) return 0;
    let hash = 0;
    for (let i = 0; i < timeStr.length; i++) hash = timeStr.charCodeAt(i) + ((hash << 5) - hash);
    return Math.abs(hash % 360);
}

function escapeHtml(text) {
    const d = document.createElement('div');
    d.textContent = text || '';
    return d.innerHTML;
}

function renderClients(clients) {
    if (!clients.length) return '<p class="text-muted">No clients found</p>';
    return '<div class="clients-list">' + clients.map(c => {
        const hue = c.time_slot ? timeHue(c.time_slot) : null;
        const borderStyle = hue !== null ? `border-left: 3px solid hsl(${hue},70%,55%);` : '';
        const timeBadge = c.time_slot
            ? `<span style="background:hsl(${hue},60%,20%);color:hsl(${hue},80%,75%);border-radius:4px;padding:1px 7px;font-size:11px;">${formatTimeSlot(c.time_slot)}</span>`
            : '';
        const trainerBadge = IS_ADMIN && c.trainer_username
            ? `<span style="background:rgba(255,255,255,0.06);border:1px solid var(--border-glow);border-radius:4px;padding:1px 7px;font-size:11px;">Trainer: ${escapeHtml(c.trainer_username)}</span>`
            : '';
        const renewalLabel = c.renewal_date ? formatDate(c.renewal_date) : '<span class="text-muted">Not Set</span>';
        const overdueWarning = c.is_overdue ? '<span style="color:#f87171;font-size:11px;">Overdue</span>' : '';
        return `<div class="client-item" style="${borderStyle}">
            <div class="client-info">
                <h4>${escapeHtml(c.name)}</h4>
                <div class="client-meta">
                    <span class="status-badge status-${c.status}">${c.status}</span>
                    <span>${escapeHtml(c.pt_tier || 'Silver')}</span>
                    ${timeBadge}
                    ${trainerBadge}
                    <span>Date: ${renewalLabel}</span>
                    ${overdueWarning}
                    ${c.notes ? `<span>- ${escapeHtml(c.notes)}</span>` : ''}
                </div>
            </div>
            <div class="client-actions">
                <button class="btn btn-sm btn-outline" onclick="editClient(${c.id})">Edit</button>
                ${c.status === 'ongoing'
                    ? `<button class="btn btn-sm btn-danger" onclick="deleteClient(${c.id})">Mark Lost</button>`
                    : (IS_ADMIN ? `<button class="btn btn-sm btn-danger" onclick="deleteClient(${c.id})">Delete</button>` : '')}
                ${c.email ? `<button class="btn btn-sm btn-outline" onclick="sendReminders('specific', ${c.id})" title="Send Reminder">Email</button>` : ''}
            </div>
        </div>`;
    }).join('') + '</div>';
}

function renderPayments(payments) {
    if (!payments.length) return '<p class="text-muted">No payments logged yet</p>';
    return '<div class="payments-list">' + payments.map(p => `
        <div class="payment-item">
            <div class="payment-info">
                <h4>${formatCurrency(p.amount)} <span style="font-weight:400;color:var(--text-muted)">from</span> ${escapeHtml(p.client_name)}</h4>
                <div class="client-meta">
                    ${p.description ? `<span>${escapeHtml(p.description)}</span>` : ''}
                    <span>${formatDate(p.payment_date)}</span>
                </div>
            </div>
            <button class="btn btn-sm btn-danger" onclick="deletePayment(${p.id})">Delete</button>
        </div>
    `).join('') + '</div>';
}

function renderNotifications(notifications) {
    if (!notifications.length) return '<p class="text-muted">No notifications yet</p>';
    return '<div class="payments-list">' + notifications.map(n => `
        <div class="payment-item">
            <div class="payment-info">
                <h4 style="font-size:13px;">${escapeHtml(n.trainer_username || 'Admin')}</h4>
                <div class="client-meta">${formatDate(n.created_at)}</div>
                <div style="margin-top:4px;font-size:13px;">${escapeHtml(n.message)}</div>
            </div>
            ${!n.is_read ? `<button class="btn btn-sm btn-outline" onclick="markNotificationRead(${n.id})">Mark Read</button>` : ''}
        </div>
    `).join('') + '</div>';
}

function renderRenewals(renewals) {
    if (!renewals || !renewals.length) return '<p class="text-muted">No renewals due in the next 7 days</p>';
    return '<div class="payments-list">' + renewals.map(r => `
        <div class="payment-item">
            <div class="payment-info">
                <h4>${escapeHtml(r.name)} <span style="font-size:12px;color:var(--text-muted)">(${escapeHtml(r.pt_tier || 'Silver')})</span></h4>
                <div class="client-meta">
                    <span>Renewal: ${formatDate(r.renewal_date)}</span>
                    <span>${r.days_until} day(s) left</span>
                    <span>Expected: ${formatCurrency(r.expected_amount)}</span>
                </div>
            </div>
            <button class="btn btn-sm btn-outline" onclick="editClient(${r.id})">Open</button>
        </div>
    `).join('') + '</div>';
}

function renderOverdue(overdueClients) {
    if (!overdueClients || !overdueClients.length) return '<p class="text-muted">No overdue clients</p>';
    return '<div class="payments-list">' + overdueClients.map(c => `
        <div class="payment-item" style="border-left:3px solid #f87171;">
            <div class="payment-info">
                <h4>${escapeHtml(c.name)} <span style="font-size:12px;color:#f87171;">(${c.days_overdue} day(s) overdue)</span></h4>
                <div class="client-meta">
                    <span>${escapeHtml(c.pt_tier || 'Silver')}</span>
                    <span>Renewal: ${formatDate(c.renewal_date)}</span>
                    <span>${escapeHtml(c.contact_number || 'N/A')}</span>
                </div>
            </div>
            <button class="btn btn-sm btn-outline" onclick="editClient(${c.id})">Open</button>
        </div>
    `).join('') + '</div>';
}

function applyStats(data) {
    const totalIncome = document.getElementById('total-income');
    const monthlyIncome = document.getElementById('monthly-income');
    const activeClients = document.getElementById('active-clients');
    const lostClients = document.getElementById('lost-clients');
    if (totalIncome) totalIncome.textContent = formatCurrency(data.total_income);
    if (monthlyIncome) monthlyIncome.textContent = formatCurrency(data.monthly_income);
    if (activeClients) activeClients.textContent = data.total_active_clients;
    if (lostClients) lostClients.textContent = data.total_lost_clients;

    if (!IS_ADMIN && data.payout_summary) {
        const el = document.getElementById('estimated-payout');
        const meta = document.getElementById('payout-meta');
        if (el) el.textContent = formatCurrency(data.payout_summary.estimated_payout);
        if (meta) meta.textContent = `${data.payout_summary.payout_percent}% | Target ${formatCurrency(data.payout_summary.monthly_target)} | ${data.payout_summary.payout_rule}`;
    }

    const renewalsList = document.getElementById('renewals-list');
    if (renewalsList) renewalsList.innerHTML = renderRenewals(data.upcoming_renewals || []);

    const overdueSection = document.getElementById('overdue-section');
    const overdueList = document.getElementById('overdue-list');
    const overdue = data.overdue_clients || [];
    if (overdueSection && overdueList) {
        if (overdue.length) {
            overdueSection.style.display = '';
            overdueList.innerHTML = renderOverdue(overdue);
        } else {
            overdueSection.style.display = 'none';
        }
    }
}

async function loadStats(force = false) {
    const cached = !force && Cache.get('stats', 20000);
    if (cached) {
        applyStats(cached);
        return;
    }
    try {
        const r = await apiFetch(`${API_BASE}/api/stats`);
        if (!r.ok) return;
        const data = await r.json();
        Cache.set('stats', data);
        applyStats(data);
    } catch (e) {
        console.error('Stats error:', e);
    }
}

function applyClientsFilter() {
    if (!_clientsCache) return;
    const list = currentFilter === 'all' ? _clientsCache : _clientsCache.filter(c => c.status === currentFilter);
    const clientsList = document.getElementById('clients-list');
    if (clientsList) clientsList.innerHTML = renderClients(list);
}

function populateClientsDropdownFromCache() {
    const select = document.getElementById('payment-client');
    if (!select) return;
    const clients = (_clientsCache || []).filter(c => c.status === 'ongoing');
    const current = select.value;
    select.innerHTML = '<option value="">Select client</option>' + clients.map(c => (
        `<option value="${c.id}" data-amount="${c.expected_amount || 0}" data-tier="${escapeHtml(c.pt_tier || 'Silver')}">${escapeHtml(c.name)} (${escapeHtml(c.pt_tier || 'Silver')})</option>`
    )).join('');
    if (current) select.value = current;
}

async function loadClients(force = false) {
    if (!force && _clientsCache) {
        applyClientsFilter();
        return;
    }
    try {
        const r = await apiFetch(`${API_BASE}/api/clients`);
        if (!r.ok) return;
        _clientsCache = await r.json();
        applyClientsFilter();
        populateClientsDropdownFromCache();
    } catch (e) {
        console.error('Clients error:', e);
    }
}

async function loadPayments(force = false) {
    if (!force && _paymentsCache) {
        const list = document.getElementById('payments-list');
        if (list) list.innerHTML = renderPayments(_paymentsCache);
        return;
    }
    try {
        const r = await apiFetch(`${API_BASE}/api/payments`);
        if (!r.ok) return;
        _paymentsCache = await r.json();
        const list = document.getElementById('payments-list');
        if (list) list.innerHTML = renderPayments(_paymentsCache);
    } catch (e) {
        console.error('Payments error:', e);
    }
}

function populateClientTrainerDropdown(trainers, selectedTrainerId = '') {
    const select = document.getElementById('client-trainer');
    if (!select) return;
    const current = selectedTrainerId !== '' ? String(selectedTrainerId) : String(select.value || '');
    select.required = trainers.length > 0;
    if (!trainers.length) {
        select.innerHTML = '<option value="">No trainers available</option>';
        select.value = '';
        return;
    }
    select.innerHTML = '<option value="">Select trainer</option>' + trainers.map(t => (`<option value="${t.id}">${escapeHtml(t.username)}</option>`)).join('');
    if (current) select.value = current;
    else if (trainers.length === 1) select.value = String(trainers[0].id);
}

async function loadAdminTrainers(force = false) {
    if (!IS_ADMIN) return [];
    if (!force && _adminTrainersCache.length) {
        populateClientTrainerDropdown(_adminTrainersCache, _selectedClientTrainerId);
        return _adminTrainersCache;
    }
    if (!force && _adminTrainersPromise) return _adminTrainersPromise;

    const request = (async () => {
        try {
            const r = await apiFetch(`${API_BASE}/api/admin/trainers`);
            if (!r.ok) return [];
            _adminTrainersCache = await r.json();
            populateClientTrainerDropdown(_adminTrainersCache, _selectedClientTrainerId);
            return _adminTrainersCache;
        } catch (e) {
            console.error('Trainer load error:', e);
            return [];
        }
    })();

    if (!force) {
        _adminTrainersPromise = request.finally(() => { _adminTrainersPromise = null; });
        return _adminTrainersPromise;
    }

    try {
        return await request;
    } finally {
        _adminTrainersPromise = null;
    }
}

function filterClients(status, btn) {
    currentFilter = status;
    document.querySelectorAll('.filter-bar .btn').forEach(b => b.classList.remove('active'));
    if (btn) btn.classList.add('active');
    applyClientsFilter();
}

async function loadNotifications() {
    const container = document.getElementById('notifications-list');
    if (!container) return;
    try {
        const r = await apiFetch(`${API_BASE}/api/admin/notifications/inbox`);
        if (!r.ok) {
            container.innerHTML = '<p class="text-muted">-</p>';
            return;
        }
        const data = await r.json();
        container.innerHTML = renderNotifications(data);
    } catch (e) {
        console.error('Notifications error:', e);
    }
}

async function markNotificationRead(id) {
    try {
        const r = await fetch(`${API_BASE}/api/admin/notifications/${id}/read`, { method: 'POST' });
        if (r.ok) loadNotifications();
    } catch (e) {
        console.error(e);
    }
}

async function sendReminders(type, client_id = null) {
    if (!confirm(type === 'specific' ? 'Send reminder to this client?' : `Send ${type === 'all' ? 'all' : 'due'} reminders now?`)) return;
    try {
        const payload = { type };
        if (client_id) payload.client_id = client_id;
        const r = await fetch(`${API_BASE}/api/reminders/send`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });
        const data = await r.json();
        alert(data.message || data.error || 'Failed to send reminders.');
    } catch (e) {
        console.error(e);
        alert('Error sending reminders.');
    }
}

function openModal(modalId) {
    const modal = document.getElementById(modalId);
    if (!modal) return;
    modal.classList.add('active');

    if (modalId === 'client-modal') {
        const form = document.getElementById('client-form');
        if (form) form.reset();
        document.getElementById('client-id').value = '';
        document.getElementById('client-modal-title').textContent = 'Add Client';
        _selectedClientTrainerId = '';
        if (IS_ADMIN) void loadAdminTrainers();
        updateExpectedAmount();
    }

    if (modalId === 'payment-modal') {
        const form = document.getElementById('payment-form');
        if (form) form.reset();
        const today = new Date().toISOString().slice(0, 10);
        const paymentDate = document.getElementById('payment-date');
        const startDate = document.getElementById('payment-start-date');
        const duration = document.getElementById('payment-duration');
        const planType = document.getElementById('payment-plan-type');
        if (paymentDate) paymentDate.value = today;
        if (startDate) startDate.value = today;
        if (duration) duration.value = 1;
        if (planType) planType.value = 'monthly';
        handlePlanTypeChange();
        updatePaymentAmount();
        updateTotalPayment();
    }
}

function closeModal(modalId) {
    const modal = document.getElementById(modalId);
    if (modal) modal.classList.remove('active');
}

async function readErrorMessage(response, fallback) {
    try {
        const p = await response.json();
        return p.error || fallback;
    } catch {
        return fallback;
    }
}

async function handleClientSubmit(event) {
    event.preventDefault();
    const id = document.getElementById('client-id').value;
    const time_slot = document.getElementById('client-time').value;

    const data = {
        name: document.getElementById('client-name').value,
        contact_number: document.getElementById('client-contact').value,
        email: document.getElementById('client-email').value,
        status: document.getElementById('client-status').value,
        pt_tier: document.getElementById('client-pt-tier').value,
        time_slot,
        renewal_date: document.getElementById('client-renewal-date').value || null,
        send_email_reminders: document.getElementById('client-email-reminders').checked,
        notes: document.getElementById('client-notes').value
    };

    if (IS_ADMIN) {
        const trainerSelect = document.getElementById('client-trainer');
        if (trainerSelect && trainerSelect.value) {
            data.trainer_id = parseInt(trainerSelect.value, 10);
        }
    }

    if (time_slot && _clientsCache) {
        const clash = _clientsCache.some(c => c.time_slot === time_slot && String(c.id) !== id && c.status === 'ongoing');
        if (clash && !confirm('Another active client has this time slot. Proceed anyway?')) return;
    }

    const url = id ? `${API_BASE}/api/clients/${id}` : `${API_BASE}/api/clients`;
    const method = id ? 'PUT' : 'POST';

    try {
        const response = await fetch(url, {
            method,
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(data)
        });
        if (response.ok) {
            closeModal('client-modal');
            _clientsCache = null;
            _paymentsCache = null;
            Cache.invalidate('stats');
            await Promise.all([loadClients(true), loadPayments(true), loadStats(true)]);
        } else {
            alert(await readErrorMessage(response, 'Error saving client'));
        }
    } catch (e) {
        console.error(e);
        alert('Error saving client');
    }
}

async function editClient(id) {
    const client = _clientsCache ? _clientsCache.find(c => c.id === id) : null;
    if (client) {
        openModal('client-modal');
        _populateClientForm(client);
        return;
    }
    try {
        const r = await fetch(`${API_BASE}/api/clients/${id}`);
        if (!r.ok) return;
        const data = await r.json();
        openModal('client-modal');
        _populateClientForm(data);
    } catch (e) {
        console.error(e);
    }
}

function _populateClientForm(client) {
    _selectedClientTrainerId = client.trainer_id || '';
    document.getElementById('client-id').value = client.id;
    document.getElementById('client-name').value = client.name || '';
    document.getElementById('client-contact').value = client.contact_number && client.contact_number !== 'N/A' ? client.contact_number : '';
    document.getElementById('client-email').value = client.email || '';
    document.getElementById('client-status').value = client.status || 'ongoing';
    document.getElementById('client-pt-tier').value = client.pt_tier || 'Silver';
    document.getElementById('client-time').value = client.time_slot || '';
    document.getElementById('client-renewal-date').value = client.renewal_date || '';
    document.getElementById('client-email-reminders').checked = Boolean(client.send_email_reminders);
    document.getElementById('client-notes').value = client.notes || '';

    if (IS_ADMIN) {
        populateClientTrainerDropdown(_adminTrainersCache, _selectedClientTrainerId);
    }
    document.getElementById('client-modal-title').textContent = 'Edit Client';
    updateExpectedAmount();
}

async function deleteClient(id) {
    const client = _clientsCache ? _clientsCache.find(c => c.id === id) : null;
    const isLost = client && client.status === 'lost';

    if (isLost) {
        if (!confirm('Permanently delete this client? All their payments will also be removed.')) return;
        if (_clientsCache) {
            _clientsCache = _clientsCache.filter(c => c.id !== id);
            applyClientsFilter();
        }
        try {
            const r = await fetch(`${API_BASE}/api/clients/${id}`, { method: 'DELETE' });
            if (!r.ok) {
                _clientsCache = null;
                await loadClients(true);
            }
            _paymentsCache = null;
            Cache.invalidate('stats');
            await Promise.all([loadPayments(true), loadStats(true)]);
        } catch (e) {
            _clientsCache = null;
            await loadClients(true);
        }
        return;
    }

    if (!confirm('Move this client to the Lost section?')) return;
    if (_clientsCache && client) {
        client.status = 'lost';
        applyClientsFilter();
    }

    try {
        const r = await fetch(`${API_BASE}/api/clients/${id}`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ status: 'lost' })
        });
        if (!r.ok) {
            _clientsCache = null;
            await loadClients(true);
        }
        Cache.invalidate('stats');
        await loadStats(true);
    } catch (e) {
        _clientsCache = null;
        await loadClients(true);
    }
}

async function handlePaymentSubmit(event) {
    event.preventDefault();
    const clientId = document.getElementById('payment-client').value;
    const planType = document.getElementById('payment-plan-type').value;
    const sessionDays = document.getElementById('payment-session-days').value;
    const startDate = document.getElementById('payment-start-date').value;
    const amount = parseFloat(document.getElementById('payment-amount').value || '0');
    const duration = parseInt(document.getElementById('payment-duration').value || '1', 10);
    const paymentDate = document.getElementById('payment-date').value;
    const description = document.getElementById('payment-description').value;

    if (!clientId || !paymentDate || !startDate || !(amount > 0) || !(duration > 0)) {
        alert('Please fill all required payment fields.');
        return;
    }

    const payload = {
        client_id: parseInt(clientId, 10),
        amount,
        payment_date: paymentDate,
        description,
        duration_months: duration,
        plan_type: planType,
        session_days: sessionDays,
        start_date: startDate
    };

    try {
        const r = await fetch(`${API_BASE}/api/payments`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });
        if (!r.ok) {
            alert(await readErrorMessage(r, 'Error saving payment'));
            return;
        }
        closeModal('payment-modal');
        _paymentsCache = null;
        _clientsCache = null;
        Cache.invalidate('stats');
        await Promise.all([loadPayments(true), loadClients(true), loadStats(true)]);
    } catch (e) {
        console.error(e);
        alert('Error saving payment');
    }
}

async function deletePayment(id) {
    if (!confirm('Delete this payment record?')) return;
    try {
        const r = await fetch(`${API_BASE}/api/payments/${id}`, { method: 'DELETE' });
        if (!r.ok) {
            alert(await readErrorMessage(r, 'Error deleting payment'));
            return;
        }
        _paymentsCache = null;
        Cache.invalidate('stats');
        await Promise.all([loadPayments(true), loadStats(true)]);
    } catch (e) {
        console.error(e);
        alert('Error deleting payment');
    }
}

function handlePlanTypeChange() {
    const planType = document.getElementById('payment-plan-type').value;
    const sessionGroup = document.getElementById('payment-session-days-group');
    const durationLabel = document.getElementById('payment-duration-label');
    if (sessionGroup) sessionGroup.style.display = planType === 'session' ? '' : 'none';
    if (durationLabel) durationLabel.textContent = planType === 'session' ? 'Number of Sessions *' : 'Duration (Months) *';
    updateTotalPayment();
}

function calculateEndDate(startDateStr, duration, planType, sessionDays) {
    if (!startDateStr || !duration || duration < 1) return null;
    const start = new Date(startDateStr + 'T00:00:00');
    if (Number.isNaN(start.getTime())) return null;

    if (planType !== 'session') {
        const end = new Date(start);
        end.setDate(end.getDate() + duration * 30);
        return end;
    }

    const validDays = sessionDays === 'MWF' ? [1, 3, 5] : [2, 4, 6];
    const end = new Date(start);
    let remaining = duration;
    while (remaining > 0) {
        const day = end.getDay();
        const isoDay = day === 0 ? 7 : day;
        if (validDays.includes(isoDay)) {
            remaining -= 1;
            if (remaining === 0) break;
        }
        end.setDate(end.getDate() + 1);
    }
    return end;
}

function updateTotalPayment() {
    const amount = parseFloat((document.getElementById('payment-amount') || {}).value || '0');
    const duration = parseInt((document.getElementById('payment-duration') || {}).value || '1', 10);
    const planType = (document.getElementById('payment-plan-type') || {}).value || 'monthly';
    const sessionDays = (document.getElementById('payment-session-days') || {}).value || 'MWF';
    const startDate = (document.getElementById('payment-start-date') || {}).value || '';

    const total = (amount > 0 && duration > 0) ? amount * duration : 0;
    const totalDisplay = document.getElementById('payment-total-display');
    if (totalDisplay) totalDisplay.textContent = `Total: ${formatCurrency(total)}`;

    const end = calculateEndDate(startDate, duration, planType, sessionDays);
    const endDisplay = document.getElementById('payment-end-date-display');
    if (endDisplay) {
        endDisplay.textContent = end
            ? `End Date: ${end.toLocaleDateString('en-IN', { day: 'numeric', month: 'short', year: 'numeric' })}`
            : 'End Date: -';
    }
}

function updateExpectedAmount() {
    const tierEl = document.getElementById('client-pt-tier');
    if (!tierEl) return;
    const tier = tierEl.value || 'Silver';
    const amounts = { Silver: 8000, Gold: 12000, Platinum: 15000 };
    const amount = amounts[tier] || 8000;

    const paymentAmount = document.getElementById('payment-amount');
    if (paymentAmount && (!paymentAmount.value || Number(paymentAmount.value) <= 0)) {
        paymentAmount.value = amount;
        updateTotalPayment();
    }
}

function updatePaymentAmount() {
    const select = document.getElementById('payment-client');
    const paymentAmount = document.getElementById('payment-amount');
    if (!select || !paymentAmount) return;
    const opt = select.options[select.selectedIndex];
    const expected = opt ? Number(opt.getAttribute('data-amount') || '0') : 0;
    if (expected > 0) paymentAmount.value = expected;
    updateTotalPayment();
}

document.addEventListener('DOMContentLoaded', () => {
    Promise.all([
        loadStats(),
        loadClients(),
        loadPayments(),
        loadNotifications(),
        IS_ADMIN ? loadAdminTrainers() : Promise.resolve()
    ]);
});
