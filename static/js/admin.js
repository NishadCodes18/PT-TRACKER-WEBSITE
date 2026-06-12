const API_BASE = '';
let trainersCache = [];

function getCsrfToken() {
    const meta = document.querySelector('meta[name="csrf-token"]');
    return meta ? meta.content : '';
}

async function apiFetch(url, opts = {}) {
    const method = (opts.method || 'GET').toUpperCase();
    const headers = { ...(opts.headers || {}) };
    if (method !== 'GET' && method !== 'HEAD') {
        headers['X-CSRFToken'] = getCsrfToken();
        if (opts.body && !headers['Content-Type'] && !(opts.body instanceof FormData)) {
            headers['Content-Type'] = 'application/json';
        }
    }
    return fetch(url, { ...opts, headers, credentials: 'same-origin' });
}
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
function formatLockoutStatus(trainer) {
    if (!trainer.is_locked || !trainer.lockout_remaining_seconds) {
        if ((trainer.failed_login_attempts || 0) > 0) {
            return `${trainer.failed_login_attempts} failed attempt(s)`;
        }
        return 'No lockout';
    }
    return `Locked for ${trainer.lockout_remaining_minutes} min`;
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
                    <div class="client-meta">Clients: ${t.client_count ?? 0} · Role: ${escapeHtml(t.role || 'trainer')} · ${escapeHtml(formatLockoutStatus(t))}</div>
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
                        Role
                        <select data-trainer-field="role">
                            <option value="trainer" ${t.role === 'trainer' ? 'selected' : ''}>Trainer</option>
                            <option value="manager" ${t.role === 'manager' ? 'selected' : ''}>Manager</option>
                            <option value="assistant" ${t.role === 'assistant' ? 'selected' : ''}>Assistant</option>
                        </select>
                    </label>
                </div>
                <div style="display:flex; gap:8px; flex-wrap:wrap; margin-top:12px; align-items:center;">
                    <button type="submit" class="btn btn-sm btn-primary">Save Trainer</button>
                    ${t.is_locked ? `<button type="button" class="btn btn-sm btn-outline" onclick="unlockTrainer(${t.id}, ${JSON.stringify(t.username)})">Unlock</button>` : ''}
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
        const payload = await response.json();
        const trainers = Array.isArray(payload) ? payload : (payload.trainers || []);
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
        const response = await apiFetch(`${API_BASE}/api/admin/trainers/${trainerId}/commission-policy`, {
            method: 'PUT',
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
        role: document.getElementById('trainer-role').value || 'trainer',
    };
    try {
        const response = await apiFetch(`${API_BASE}/api/admin/trainers`, {
            method: 'POST',
            body: JSON.stringify(payload),
        });
        const data = await response.json();
        if (!response.ok) {
            alert(data.error || 'Failed to create trainer');
            return;
        }
        document.getElementById('trainer-create-form').reset();
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
        role: form.querySelector('[data-trainer-field="role"]').value || 'trainer',
    };
    if (!payload.password) {
        delete payload.password;
    }
    try {
        const response = await apiFetch(`${API_BASE}/api/admin/trainers/${trainerId}`, {
            method: 'PUT',
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
        const response = await apiFetch(`${API_BASE}/api/admin/trainers/${trainerId}`, {
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
async function unlockTrainer(trainerId, username) {
    if (!confirm(`Unlock ${username}'s account now?`)) {
        return;
    }
    try {
        const response = await apiFetch(`${API_BASE}/api/admin/trainers/${trainerId}/unlock`, {
            method: 'POST',
        });
        const data = await response.json();
        if (!response.ok) {
            alert(data.error || 'Failed to unlock trainer');
            return;
        }
        await Promise.all([loadTrainersAndPolicies(), loadPayouts()]);
    } catch (error) {
        console.error('Error unlocking trainer:', error);
        alert('Failed to unlock trainer');
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
        const response = await apiFetch(`${API_BASE}/api/admin/notifications`, {
            method: 'POST',
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

async function refreshAllAdminData() {
    try {
        await Promise.all([
            loadTrainersAndPolicies(),
            loadPayouts(),
            loadNotificationHistory(),
            loadEmailLogs(1)
        ]);
        alert('All admin data refreshed successfully!');
    } catch (error) {
        console.error('Error refreshing admin data:', error);
        alert('Error refreshing some data. Check console for details.');
    }
}

// Email Logs Functions
async function loadEmailStats() {
    try {
        const days = document.getElementById('email-days-filter')?.value || '30';
        const response = await fetch(`${API_BASE}/api/email-logs/stats?days=${days}`);
        if (!response.ok) throw new Error('Failed to load email stats');

        const stats = await response.json();
        const sentEl = document.getElementById('stat-sent');
        const failedEl = document.getElementById('stat-failed');
        const rateEl = document.getElementById('stat-success-rate');

        if (sentEl) sentEl.textContent = stats.total_sent || 0;
        if (failedEl) failedEl.textContent = stats.total_failed || 0;
        if (rateEl) rateEl.textContent = `${stats.success_rate || 0}%`;
    } catch (error) {
        console.error('Error loading email stats:', error);
    }
}

async function loadEmailLogs(page = 1) {
    try {
        const emailType = document.getElementById('email-type-filter').value;
        const status = document.getElementById('email-status-filter').value;
        const days = document.getElementById('email-days-filter').value;

        const params = new URLSearchParams({ page, per_page: 20, days });
        if (emailType) params.append('email_type', emailType);
        if (status) params.append('status', status);

        const response = await fetch(`${API_BASE}/api/email-logs?${params}`);
        if (!response.ok) throw new Error('Failed to load email logs');

        const data = await response.json();
        const tbody = document.getElementById('email-logs-table');

        if (!data.items || data.items.length === 0) {
            tbody.innerHTML = '<tr><td colspan="5" class="text-center text-muted">No email logs found</td></tr>';
            document.getElementById('email-logs-pagination').innerHTML = '';
            return;
        }

        tbody.innerHTML = data.items.map(log => `
            <tr>
                <td>${formatEmailDate(log.sent_at)}</td>
                <td>
                    <div><strong>${escapeHtml(log.recipient_name || 'N/A')}</strong></div>
                    <div style="font-size:12px;color:#6c757d;">${escapeHtml(log.recipient_email)}</div>
                </td>
                <td>${escapeHtml(log.subject)}</td>
                <td><span style="font-size:12px;padding:4px 8px;border-radius:4px;background:#e9ecef;">${escapeHtml(log.email_type || 'N/A')}</span></td>
                <td>${getStatusBadge(log.status)}</td>
            </tr>
        `).join('');

        renderEmailLogsPagination(data.pagination, page);
        await loadEmailStats();
    } catch (error) {
        console.error('Error loading email logs:', error);
        document.getElementById('email-logs-table').innerHTML = '<tr><td colspan="5" class="text-center text-muted">Unable to load email logs</td></tr>';
    }
}

function formatEmailDate(isoString) {
    const date = new Date(isoString);
    const now = new Date();
    const diffMs = now - date;
    const diffMins = Math.floor(diffMs / 60000);

    if (diffMins < 60) return `${diffMins}m ago`;
    if (diffMins < 1440) return `${Math.floor(diffMins / 60)}h ago`;

    return date.toLocaleDateString('en-IN', {
        day: '2-digit',
        month: 'short',
        year: 'numeric',
        hour: '2-digit',
        minute: '2-digit'
    });
}

function getStatusBadge(status) {
    if (status === 'sent') {
        return '<span style="padding:4px 12px;border-radius:12px;background:#d4edda;color:#155724;font-size:12px;font-weight:500;">✓ Sent</span>';
    } else if (status === 'failed') {
        return '<span style="padding:4px 12px;border-radius:12px;background:#f8d7da;color:#721c24;font-size:12px;font-weight:500;">✗ Failed</span>';
    }
    return '<span style="padding:4px 12px;border-radius:12px;background:#e9ecef;color:#495057;font-size:12px;">Unknown</span>';
}

function renderEmailLogsPagination(pagination, currentPage) {
    const container = document.getElementById('email-logs-pagination');
    if (!pagination || pagination.pages <= 1) {
        container.innerHTML = '';
        return;
    }

    let html = '<div style="display:flex;gap:5px;align-items:center;">';

    if (pagination.has_prev) {
        html += `<button onclick="loadEmailLogs(${currentPage - 1})" class="btn btn-sm btn-secondary">← Prev</button>`;
    }

    html += `<span style="padding:0 15px;color:#6c757d;">Page ${currentPage} of ${pagination.pages}</span>`;

    if (pagination.has_next) {
        html += `<button onclick="loadEmailLogs(${currentPage + 1})" class="btn btn-sm btn-secondary">Next →</button>`;
    }

    html += '</div>';
    container.innerHTML = html;
}

// License Key Management
let licensePagination = { page: 1, per_page: 20, pages: 1 };

async function loadLicenseKeys() {
    const listEl = document.getElementById('license-keys-list');
    if (!listEl) return;

    const statusFilter = document.getElementById('license-status-filter')?.value || 'unused';

    try {
        const r = await apiFetch(`${API_BASE}/api/admin/licenses?page=${licensePagination.page}&per_page=${licensePagination.per_page}&status=${statusFilter}`);
        if (!r.ok) {
            listEl.innerHTML = '<p class="text-muted">Failed to load license keys</p>';
            return;
        }

        const data = await r.json();
        licensePagination = data.pagination || licensePagination;

        // Update statistics
        if (data.statistics) {
            document.getElementById('license-total').textContent = data.statistics.total;
            document.getElementById('license-unused').textContent = data.statistics.unused;
            document.getElementById('license-used').textContent = data.statistics.used;
            const usageRate = data.statistics.total > 0
                ? ((data.statistics.used / data.statistics.total) * 100).toFixed(1)
                : 0;
            document.getElementById('license-usage').textContent = usageRate + '%';
        }

        // Render license keys
        if (!data.licenses || data.licenses.length === 0) {
            listEl.innerHTML = '<p class="text-muted">No license keys found</p>';
        } else {
            listEl.innerHTML = '<div class="payments-list">' + data.licenses.map(lic => {
                const statusColor = lic.is_used ? '#ef4444' : '#22c55e';
                const statusText = lic.is_used ? 'USED' : 'AVAILABLE';
                const usedBy = lic.used_by_username ? `<div style="font-size:11px;color:#666;margin-top:4px;">Used by: ${escapeHtml(lic.used_by_username)} on ${formatDate(lic.used_at)}</div>` : '';

                return `
                    <div class="payment-item">
                        <div class="payment-info">
                            <h4 style="font-family:monospace;font-size:16px;">${escapeHtml(lic.license_key)}
                                <span style="background:${lic.is_used ? 'rgba(239,68,68,0.1)' : 'rgba(34,197,94,0.1)'};border:1px solid ${statusColor};border-radius:4px;padding:1px 7px;font-size:11px;color:${statusColor};margin-left:8px;">${statusText}</span>
                            </h4>
                            <div style="font-size:12px;color:#666;margin-top:4px;">
                                Created: ${formatDate(lic.created_at)}
                                ${lic.notes ? `<span style="margin-left:15px;">Notes: ${escapeHtml(lic.notes)}</span>` : ''}
                            </div>
                            ${usedBy}
                        </div>
                        <div style="display:flex;gap:6px;">
                            <button class="btn btn-sm btn-outline" onclick="copyToClipboard('${escapeHtml(lic.license_key)}')">📋 Copy</button>
                        </div>
                    </div>
                `;
            }).join('') + '</div>';
        }

        // Update pagination
        const pagerMeta = document.getElementById('license-page-meta');
        if (pagerMeta) {
            pagerMeta.textContent = `Page ${licensePagination.page} of ${licensePagination.pages}`;
        }

    } catch (e) {
        console.error('License load error:', e);
        listEl.innerHTML = '<p class="text-muted">Error loading license keys</p>';
    }
}

function changeLicensePage(delta) {
    const nextPage = licensePagination.page + delta;
    if (nextPage < 1 || nextPage > licensePagination.pages) return;
    licensePagination.page = nextPage;
    loadLicenseKeys();
}

function openGenerateLicenseModal() {
    const modal = document.getElementById('generate-license-modal');
    if (modal) {
        document.getElementById('license-count').value = 10;
        document.getElementById('license-notes').value = '';
        document.getElementById('generated-keys-output').style.display = 'none';
        modal.classList.add('active');
    }
}

async function generateLicenseKeys(event) {
    event.preventDefault();

    const count = parseInt(document.getElementById('license-count').value);
    const notes = document.getElementById('license-notes').value;

    if (count < 1 || count > 100) {
        alert('Please enter a number between 1 and 100');
        return;
    }

    try {
        const r = await apiFetch(`${API_BASE}/api/admin/licenses/generate`, {
            method: 'POST',
            body: JSON.stringify({ count, notes })
        });

        if (!r.ok) {
            const error = await r.json();
            alert('Error: ' + (error.error || 'Failed to generate keys'));
            return;
        }

        const data = await r.json();

        // Show generated keys
        const output = document.getElementById('generated-keys-output');
        const textarea = document.getElementById('generated-keys-text');

        textarea.value = data.keys.join('\n');
        output.style.display = 'block';

        // Reload license list
        await loadLicenseKeys();

        alert(`✅ Generated ${data.count} license keys successfully!`);
    } catch (e) {
        console.error('Generate error:', e);
        alert('Error generating license keys');
    }
}

function copyGeneratedKeys() {
    const textarea = document.getElementById('generated-keys-text');
    textarea.select();
    document.execCommand('copy');
    alert('✅ License keys copied to clipboard!');
}

async function downloadLicenseKeys(status) {
    try {
        const url = `${API_BASE}/api/admin/licenses/download?status=${status}`;
        window.location.href = url;
    } catch (e) {
        console.error('Download error:', e);
        alert('Error downloading license keys');
    }
}

function copyToClipboard(text) {
    const textarea = document.createElement('textarea');
    textarea.value = text;
    textarea.style.position = 'fixed';
    textarea.style.opacity = '0';
    document.body.appendChild(textarea);
    textarea.select();
    document.execCommand('copy');
    document.body.removeChild(textarea);
    alert('✅ Copied: ' + text);
}

document.addEventListener('DOMContentLoaded', async () => {
    await Promise.all([loadTrainersAndPolicies(), loadPayouts(), loadNotificationHistory(), loadEmailLogs(), loadLicenseKeys()]);

    // Auto-refresh admin data every 60 seconds
    setInterval(() => {
        loadPayouts();
        loadNotificationHistory();
    }, 60000);
});