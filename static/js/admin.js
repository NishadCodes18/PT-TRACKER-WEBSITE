const API_BASE = '';
let trainersCache = [];
function formatCurrency(amount) {
    return '₹' + parseFloat(amount || 0).toFixed(2);
}
function formatDate(dateStr) {
    const date = new Date(dateStr);
    return date.toLocaleDateString('en-US', {
        month: 'short',
        day: 'numeric',
        year: 'numeric',
    });
}
function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text || '';
    return div.innerHTML;
}
function renderTrainerManagement(trainers) {
    const container = document.getElementById('trainer-management-list');
    if (!container) return;
    if (!trainers.length) {
        container.innerHTML = '<p class="text-muted">No trainer accounts found</p>';
        return;
    }
    container.innerHTML = '<div class="clients-list">' + trainers.map(t => `
        <div class="client-item admin-policy-item">
            <form onsubmit="saveTrainer(event, ${t.id})" style="width:100%;">
                <div class="client-info">
                    <h4>${escapeHtml(t.username)}</h4>
                    <div class="client-meta">Clients: ${t.client_count ?? 0} · Shift: ${escapeHtml(t.shift_type || '8-hour')}</div>
                </div>
                <div class="admin-policy-grid">
                    <label>
                        Username
                        <input type="text" data-trainer-field="username" value="${escapeHtml(t.username)}">
                    </label>
                    <label>
                        New Password
                        <input type="password" data-trainer-field="password" placeholder="Leave blank to keep current password">
                    </label>
                    <label>
                        Shift Type
                        <input type="text" data-trainer-field="shift_type" value="${escapeHtml(t.shift_type || '8-hour')}">
                    </label>
                </div>
                <div style="display:flex; gap:8px; flex-wrap:wrap; margin-top:12px;">
                    <button type="submit" class="btn btn-sm btn-primary">Save Trainer</button>
                    <button type="button" class="btn btn-sm btn-danger" onclick='deleteTrainer(${t.id}, ${JSON.stringify(t.username)})'>Delete</button>
                </div>
            </form>
        </div>
    `).join('') + '</div>';
}
async function loadTrainersAndPolicies() {
    try {
        const response = await fetch(`${API_BASE}/api/admin/trainers`);
        if (!response.ok) {
            throw new Error('Failed to load trainers');
        }
        const trainers = await response.json();
        trainersCache = trainers;
        renderTrainerManagement(trainers);
        renderPolicies(trainers);
        populateTrainerDropdown(trainers);
    } catch (error) {
        console.error('Error loading trainer policies:', error);
        const management = document.getElementById('trainer-management-list');
        if (management) management.innerHTML = '<p class="text-muted">Unable to load trainer accounts</p>';
        document.getElementById('commission-policies-list').innerHTML = '<p class="text-muted">Unable to load trainer policies</p>';
    }
}
function renderPolicies(trainers) {
    const container = document.getElementById('commission-policies-list');
    if (!trainers.length) {
        container.innerHTML = '<p class="text-muted">No trainer accounts found</p>';
        return;
    }
    container.innerHTML = '<div class="clients-list">' + trainers.map(t => {
        const p = t.commission_policy;
        return `
            <form class="client-item admin-policy-item" onsubmit="saveCommissionPolicy(event, ${t.id})">
                <div class="client-info">
                    <h4>${escapeHtml(t.username)}</h4>
                    <div class="client-meta">Monthly target and payout logic</div>
                </div>
                <div class="admin-policy-grid">
                    <label>
                        Target
                        <input type="number" step="0.01" min="0" data-field="monthly_target" value="${p.monthly_target}">
                    </label>
                    <label>
                        Above %
                        <input type="number" step="0.01" min="0" max="100" data-field="above_target_percent" value="${p.above_target_percent}">
                    </label>
                    <label>
                        Below %
                        <input type="number" step="0.01" min="0" max="100" data-field="below_target_percent" value="${p.below_target_percent}">
                    </label>
                    <label>
                        Override %
                        <input type="number" step="0.01" min="0" max="100" data-field="override_percent" value="${p.override_percent ?? ''}" placeholder="optional">
                    </label>
                </div>
                <div>
                    <button type="submit" class="btn btn-sm btn-primary">Save</button>
                </div>
            </form>
        `;
    }).join('') + '</div>';
}
async function saveCommissionPolicy(event, trainerId) {
    event.preventDefault();
    const form = event.currentTarget;
    const data = {
        monthly_target: parseFloat(form.querySelector('[data-field="monthly_target"]').value || '0'),
        above_target_percent: parseFloat(form.querySelector('[data-field="above_target_percent"]').value || '0'),
        below_target_percent: parseFloat(form.querySelector('[data-field="below_target_percent"]').value || '0'),
        override_percent: form.querySelector('[data-field="override_percent"]').value,
    };
    try {
        const response = await fetch(`${API_BASE}/api/admin/trainers/${trainerId}/commission-policy`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(data),
        });
        const payload = await response.json();
        if (!response.ok) {
            alert(payload.error || 'Failed to save commission policy');
            return;
        }
        await Promise.all([loadTrainersAndPolicies(), loadPayouts()]);
    } catch (error) {
        console.error('Error saving commission policy:', error);
        alert('Failed to save commission policy');
    }
}
function populateTrainerDropdown(trainers) {
    const select = document.getElementById('notify-trainer');
    if (!select) return;
    select.innerHTML = '<option value="">All Trainers (Broadcast)</option>' + trainers.map(t => (
        `<option value="${t.id}">${escapeHtml(t.username)}</option>`
    )).join('');
}
async function createTrainer(event) {
    event.preventDefault();
    const payload = {
        username: document.getElementById('trainer-username').value.trim(),
        password: document.getElementById('trainer-password').value,
        shift_type: document.getElementById('trainer-shift-type').value.trim() || '8-hour',
    };
    try {
        const response = await fetch(`${API_BASE}/api/admin/trainers`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload),
        });
        const data = await response.json();
        if (!response.ok) {
            alert(data.error || 'Failed to create trainer');
            return;
        }
        document.getElementById('trainer-create-form').reset();
        document.getElementById('trainer-shift-type').value = '8-hour';
        await Promise.all([loadTrainersAndPolicies(), loadPayouts()]);
    } catch (error) {
        console.error('Error creating trainer:', error);
        alert('Failed to create trainer');
    }
}
async function saveTrainer(event, trainerId) {
    event.preventDefault();
    const form = event.currentTarget;
    const payload = {
        username: form.querySelector('[data-trainer-field="username"]').value.trim(),
        password: form.querySelector('[data-trainer-field="password"]').value,
        shift_type: form.querySelector('[data-trainer-field="shift_type"]').value.trim() || '8-hour',
    };
    if (!payload.password) {
        delete payload.password;
    }
    try {
        const response = await fetch(`${API_BASE}/api/admin/trainers/${trainerId}`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload),
        });
        const data = await response.json();
        if (!response.ok) {
            alert(data.error || 'Failed to update trainer');
            return;
        }
        await Promise.all([loadTrainersAndPolicies(), loadPayouts()]);
    } catch (error) {
        console.error('Error updating trainer:', error);
        alert('Failed to update trainer');
    }
}
async function deleteTrainer(trainerId, username) {
    if (!confirm(`Delete trainer ${username}? This will remove their related data.`)) {
        return;
    }
    try {
        const response = await fetch(`${API_BASE}/api/admin/trainers/${trainerId}`, {
            method: 'DELETE',
        });
        const data = await response.json();
        if (!response.ok) {
            alert(data.error || 'Failed to delete trainer');
            return;
        }
        await Promise.all([loadTrainersAndPolicies(), loadPayouts()]);
    } catch (error) {
        console.error('Error deleting trainer:', error);
        alert('Failed to delete trainer');
    }
}
async function loadPayouts() {
    try {
        const response = await fetch(`${API_BASE}/api/admin/payouts`);
        if (!response.ok) {
            throw new Error('Failed to load payouts');
        }
        const payouts = await response.json();
        const container = document.getElementById('payouts-list');
        if (!payouts.length) {
            container.innerHTML = '<p class="text-muted">No trainer payouts available yet</p>';
            return;
        }
        container.innerHTML = '<div class="payments-list">' + payouts.map(p => `
            <div class="payment-item">
                <div class="payment-info">
                    <h4>${escapeHtml(p.trainer_username)}</h4>
                    <div class="client-meta">
                        Income: ${formatCurrency(p.monthly_income)} · Target: ${formatCurrency(p.monthly_target)} · Rule: ${escapeHtml(p.payout_rule)}
                    </div>
                </div>
                <div>
                    <strong>${p.payout_percent}%</strong> = ${formatCurrency(p.payout_amount)}
                </div>
            </div>
        `).join('') + '</div>';
    } catch (error) {
        console.error('Error loading payouts:', error);
        document.getElementById('payouts-list').innerHTML = '<p class="text-muted">Unable to load payouts</p>';
    }
}
async function sendAdminNotification(event) {
    event.preventDefault();
    const trainerId = document.getElementById('notify-trainer').value;
    const message = document.getElementById('notify-message').value.trim();
    if (!message) {
        alert('Message is required');
        return;
    }
    const payload = { message };
    if (trainerId) {
        payload.trainer_id = parseInt(trainerId, 10);
    }
    try {
        const response = await fetch(`${API_BASE}/api/admin/notifications`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload),
        });
        const data = await response.json();
        if (!response.ok) {
            alert(data.error || 'Failed to send notification');
            return;
        }
        document.getElementById('admin-notification-form').reset();
        await loadNotificationHistory();
    } catch (error) {
        console.error('Error sending notification:', error);
        alert('Failed to send notification');
    }
}
async function loadNotificationHistory() {
    try {
        const response = await fetch(`${API_BASE}/api/admin/notifications`);
        if (!response.ok) {
            throw new Error('Failed to load notifications');
        }
        const notifications = await response.json();
        const container = document.getElementById('admin-notification-history');
        if (!notifications.length) {
            container.innerHTML = '<p class="text-muted">No notifications sent yet</p>';
            return;
        }
        container.innerHTML = '<div class="payments-list">' + notifications.map(n => `
            <div class="payment-item">
                <div class="payment-info">
                    <h4>${escapeHtml(n.trainer_username || 'All Trainers')}</h4>
                    <div class="client-meta">${formatDate(n.created_at)}</div>
                    <div>${escapeHtml(n.message)}</div>
                </div>
            </div>
        `).join('') + '</div>';
    } catch (error) {
        console.error('Error loading notification history:', error);
        document.getElementById('admin-notification-history').innerHTML = '<p class="text-muted">Unable to load notifications</p>';
    }
}
document.addEventListener('DOMContentLoaded', async () => {
    await Promise.all([loadTrainersAndPolicies(), loadPayouts(), loadNotificationHistory()]);
});