const API_BASE = "";
const IS_ADMIN = window.IS_ADMIN === true || window.IS_ADMIN === "true";
const IS_PROFILE_PAGE = !!document.getElementById("profile-form") && !document.getElementById("stats-grid");

const Cache = {
    _store: {},
    set(key, data) {
        this._store[key] = { data, ts: Date.now() };
    },
    get(key, maxAgeMs = 30000) {
        const entry = this._store[key];
        if (!entry) return null;
        if (Date.now() - entry.ts > maxAgeMs) {
            delete this._store[key];
            return null;
        }
        return entry.data;
    },
    invalidate(...keys) {
        keys.forEach((k) => delete this._store[k]);
    },
};

const state = {
    clientFilter: "all",
    clients: [],
    clientsPagination: { page: 1, per_page: 20, pages: 1, has_next: false, has_prev: false },
    clientSearch: "",
    payments: [],
    paymentsPagination: { page: 1, per_page: 20, pages: 1, has_next: false, has_prev: false },
    paymentSearch: "",
    adminTrainers: [],
    selectedClientTrainerId: "",
};

const inflight = {};

function getCsrfToken() {
    const meta = document.querySelector('meta[name="csrf-token"]');
    return meta ? meta.content : "";
}

function showToast(message, type = "info", durationMs = 4200) {
    const root = document.getElementById("toast-root");
    if (!root) {
        console.log(`[${type}] ${message}`);
        return;
    }
    const el = document.createElement("div");
    el.className = `toast toast-${type}`;
    el.textContent = message;
    root.appendChild(el);
    requestAnimationFrame(() => el.classList.add("visible"));
    setTimeout(() => {
        el.classList.remove("visible");
        setTimeout(() => el.remove(), 320);
    }, durationMs);
}

function unwrapApi(payload) {
    if (payload && payload.ok === true && payload.data !== undefined) return payload.data;
    return payload;
}

async function parseApiResponse(response, fallback = "Request failed") {
    let payload = {};
    try {
        payload = await response.json();
    } catch {
        if (!response.ok) throw new Error(fallback);
        return {};
    }
    if (!response.ok || payload.ok === false) {
        throw new Error(payload.error || payload.message || fallback);
    }
    const unwrapped = unwrapApi(payload);
    if (payload.message && typeof unwrapped === "object" && unwrapped !== null && !Array.isArray(unwrapped)) {
        unwrapped.message = payload.message;
    } else if (payload.message && (unwrapped === undefined || typeof unwrapped !== "object")) {
        return { value: unwrapped, message: payload.message };
    }
    return unwrapped;
}

async function readErrorMessage(response, fallback) {
    try {
        const p = await response.json();
        return p.error || p.message || fallback;
    } catch {
        return fallback;
    }
}

function debounce(fn, waitMs = 350) {
    let t = null;
    return (...args) => {
        clearTimeout(t);
        t = setTimeout(() => fn(...args), waitMs);
    };
}

async function apiFetch(url, opts = {}) {
    const method = (opts.method || "GET").toUpperCase();
    const headers = { ...(opts.headers || {}) };
    if (method !== "GET" && method !== "HEAD") {
        headers["X-CSRFToken"] = getCsrfToken();
        if (opts.body && !headers["Content-Type"] && !(opts.body instanceof FormData)) {
            headers["Content-Type"] = "application/json";
        }
    }
    const merged = { ...opts, headers, credentials: "same-origin" };
    const isCacheableGet = method === "GET" && !opts.body && Object.keys(opts).length <= 1;
    if (isCacheableGet && inflight[url]) return inflight[url];

    const req = fetch(url, merged)
        .catch(error => {
            // Network error - backend might be waking up
            if (error.name === 'TypeError' && error.message.includes('fetch')) {
                console.warn('Backend connection failed, might be cold start:', error);
                showBackendWakeupUI();
            }
            throw error;
        })
        .finally(() => {
            delete inflight[url];
        });

    if (isCacheableGet) inflight[url] = req;
    return req;
}

let backendWakeupShown = false;
function showBackendWakeupUI() {
    if (backendWakeupShown) return;
    backendWakeupShown = true;

    const overlay = document.createElement('div');
    overlay.id = 'backend-wakeup-overlay';
    overlay.style.cssText = `
        position: fixed;
        top: 0;
        left: 0;
        right: 0;
        bottom: 0;
        background: rgba(10, 10, 15, 0.95);
        z-index: 10000;
        display: flex;
        align-items: center;
        justify-content: center;
        backdrop-filter: blur(8px);
    `;

    overlay.innerHTML = `
        <div style="text-align: center; max-width: 500px; padding: 20px;">
            <div style="display: inline-flex; align-items: center; justify-content: center; width: 100px; height: 100px; background: linear-gradient(135deg, #f97316, #facc15); border-radius: 20px; margin-bottom: 20px; font-size: 48px; animation: pulse 2s ease-in-out infinite;">
                💪
            </div>
            <h2 style="font-family: 'Orbitron', sans-serif; font-size: 24px; font-weight: 900; color: #f97316; margin-bottom: 12px;">
                Connecting to Server...
            </h2>
            <p style="color: #64748b; margin-bottom: 24px;">
                The backend is waking up from sleep mode. This usually takes 30-60 seconds.
            </p>
            <div style="width: 100%; height: 4px; background: #111118; border-radius: 999px; overflow: hidden; margin-bottom: 12px;">
                <div style="height: 100%; background: linear-gradient(90deg, #f97316, #facc15, #f97316); background-size: 200% 100%; animation: loading 1.5s ease-in-out infinite; border-radius: 999px;"></div>
            </div>
            <p id="wakeup-status" style="color: #64748b; font-size: 14px; animation: fadeInOut 2s ease-in-out infinite;">
                Please wait...
            </p>
        </div>
    `;

    document.body.appendChild(overlay);

    // Add animations
    const style = document.createElement('style');
    style.textContent = `
        @keyframes pulse {
            0%, 100% { transform: scale(1); box-shadow: 0 8px 32px rgba(249,115,22,0.3); }
            50% { transform: scale(1.05); box-shadow: 0 12px 48px rgba(249,115,22,0.5); }
        }
        @keyframes loading {
            0% { width: 0%; background-position: 0% 50%; }
            50% { width: 70%; background-position: 100% 50%; }
            100% { width: 100%; background-position: 0% 50%; }
        }
        @keyframes fadeInOut {
            0%, 100% { opacity: 0.5; }
            50% { opacity: 1; }
        }
    `;
    document.head.appendChild(style);

    // Update status messages
    const messages = [
        'Connecting to database...',
        'Waking up backend server...',
        'Loading your workspace...',
        'Almost ready...'
    ];
    let msgIdx = 0;
    const statusEl = document.getElementById('wakeup-status');
    const msgInterval = setInterval(() => {
        msgIdx = (msgIdx + 1) % messages.length;
        if (statusEl) statusEl.textContent = messages[msgIdx];
    }, 2000);

    // Retry connection
    let attempts = 0;
    const maxAttempts = 60;
    const retryInterval = setInterval(async () => {
        try {
            const r = await fetch('/health');
            const data = await r.json();
            if (data.ok && data.db_initialized) {
                clearInterval(msgInterval);
                clearInterval(retryInterval);
                overlay.remove();
                backendWakeupShown = false;
                // Reload the page to get fresh data
                window.location.reload();
            }
        } catch (e) {
            // Still waiting
        }

        attempts++;
        if (attempts >= maxAttempts) {
            clearInterval(msgInterval);
            clearInterval(retryInterval);
            if (statusEl) {
                statusEl.textContent = 'Taking longer than expected. Refreshing page...';
                statusEl.style.color = '#f97316';
            }
            setTimeout(() => window.location.reload(), 2000);
        }
    }, 1000);
}

async function saveProfile(event) {
    event.preventDefault();
    const emailInput = document.getElementById('profile-email');
    const statusEl = document.getElementById('profile-status');
    if (!emailInput || !statusEl) return;

    statusEl.textContent = 'Saving...';
    try {
        const response = await apiFetch(`${API_BASE}/api/security/profile`, {
            method: 'PUT',
            body: JSON.stringify({ email: emailInput.value.trim() }),
        });
        const data = await parseApiResponse(response, 'Unable to update recovery email');
        const user = data.user || data;
        emailInput.value = user?.email || '';
        statusEl.textContent = user?.email ? `Saved: ${user.email}` : 'Recovery email cleared';
        showToast('Profile updated', 'success');
    } catch (error) {
        console.error('Error saving profile:', error);
        statusEl.textContent = 'Unable to update recovery email';
    }
}

function formatCurrency(amount) {
    const n = Number(amount || 0);
    // Indian currency formatting with ₹ symbol
    return "₹" + n.toLocaleString("en-IN", { minimumFractionDigits: 0, maximumFractionDigits: 0 });
}

function formatDate(dateStr) {
    if (!dateStr) return "-";
    const d = new Date(dateStr + "T00:00:00");
    return d.toLocaleDateString("en-IN", { day: "numeric", month: "short", year: "numeric" });
}

function formatTimeSlot(timeStr) {
    if (!timeStr) return "";
    const [h24, min] = timeStr.split(":");
    let h = parseInt(h24, 10);
    const ampm = h >= 12 ? "PM" : "AM";
    h = h % 12 || 12;
    const endH24 = parseInt(h24, 10) + 1;
    const endAmpm = endH24 >= 12 && endH24 < 24 ? "PM" : "AM";
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
    const d = document.createElement("div");
    d.textContent = text || "";
    return d.innerHTML;
}

function setLoading(containerId, text = "Loading...") {
    const el = document.getElementById(containerId);
    if (el) el.innerHTML = `<p class="text-muted">${escapeHtml(text)}</p>`;
}

function renderClients(clients) {
    if (!clients.length) return '<p class="text-muted">No clients found</p>';
    return (
        '<div class="clients-list">' +
        clients
            .map((c) => {
                const hue = c.time_slot ? timeHue(c.time_slot) : null;
                const borderStyle = hue !== null ? `border-left: 3px solid hsl(${hue},70%,55%);` : "";
                const timeBadge = c.time_slot
                    ? `<span style="background:hsl(${hue},60%,20%);color:hsl(${hue},80%,75%);border-radius:4px;padding:1px 7px;font-size:11px;">${formatTimeSlot(c.time_slot)}</span>`
                    : "";
                const trainerBadge =
                    IS_ADMIN && c.trainer_username
                        ? `<span style="background:rgba(255,255,255,0.06);border:1px solid var(--border-glow);border-radius:4px;padding:1px 7px;font-size:11px;">Trainer: ${escapeHtml(c.trainer_username)}</span>`
                        : "";
                const gymBadge = c.gym_name
                    ? `<span style="background:rgba(59,130,246,0.1);border:1px solid rgba(59,130,246,0.3);border-radius:4px;padding:1px 7px;font-size:11px;">🏋️ ${escapeHtml(c.gym_name)}</span>`
                    : "";
                const renewalLabel = c.renewal_date ? formatDate(c.renewal_date) : '<span class="text-muted">Not Set</span>';
                const overdueWarning = c.is_overdue ? '<span style="color:#f87171;font-size:11px;">Overdue</span>' : "";
                return `<div class="client-item" style="${borderStyle}">
                <div class="client-info">
                    <h4>${escapeHtml(c.name)}</h4>
                    <div class="client-meta">
                        <span class="status-badge status-${c.status}">${c.status}</span>
                        <span>${escapeHtml(c.pt_tier || "Silver")}</span>
                        ${timeBadge}
                        ${gymBadge}
                        ${trainerBadge}
                        ${c.notes ? `<span>- ${escapeHtml(c.notes)}</span>` : ""}
                    </div>
                </div>
                <div class="client-actions">
                    <button class="btn btn-sm btn-outline" onclick="editClient(${c.id})">Edit</button>
                    ${
                        c.status === "ongoing"
                            ? `<button class="btn btn-sm btn-danger" onclick="deleteClient(${c.id}, false)">Mark Lost</button>`
                            : `<button class="btn btn-sm btn-danger" onclick="deleteClient(${c.id}, false)">Delete</button>`
                    }
                    <button class="btn btn-sm btn-danger" onclick="deleteClient(${c.id}, true)" style="opacity:0.7;" title="Permanently delete this client and all associated data">Delete Permanently</button>
                    ${c.email ? `<button class="btn btn-sm btn-outline" onclick="sendEmail(${c.id})" title="Send Email">Email</button>` : ""}
                </div>
            </div>`;
            })
            .join("") +
        "</div>"
    );
}

function renderPayments(payments) {
    if (!payments.length) return '<p class="text-muted">No payments logged yet</p>';
    return (
        '<div class="payments-list">' +
        payments
            .map(
                (p) => {
                    const paymentModeLabel = p.payment_mode ? `<span style="background:rgba(34,197,94,0.1);border:1px solid rgba(34,197,94,0.3);border-radius:4px;padding:1px 7px;font-size:11px;">💳 ${escapeHtml(p.payment_mode.toUpperCase())}</span>` : '';
                    const gymPaymentLabel = p.gym_payment_done
                        ? `<span style="background:rgba(34,197,94,0.1);border:1px solid rgba(34,197,94,0.3);border-radius:4px;padding:1px 7px;font-size:11px;">✓ Gym Paid ${p.gym_payment_amount ? formatCurrency(p.gym_payment_amount) : ''}</span>`
                        : `<span style="background:rgba(239,68,68,0.1);border:1px solid rgba(239,68,68,0.3);border-radius:4px;padding:1px 7px;font-size:11px;">✗ Gym Pending</span>`;
                    return `
        <div class="payment-item">
            <div class="payment-info">
                <h4>${formatCurrency(p.amount)} <span style="font-weight:400;color:var(--text-muted)">from</span> ${escapeHtml(p.client_name)}</h4>
                <div class="client-meta">
                    ${p.description ? `<span>${escapeHtml(p.description)}</span>` : ""}
                    <span>${formatDate(p.payment_date)}</span>
                    ${paymentModeLabel}
                    ${gymPaymentLabel}
                </div>
            </div>
            <div style="display:flex;gap:6px;">
                <button class="btn btn-sm btn-danger" onclick="deletePayment(${p.id}, false)">Delete</button>
                <button class="btn btn-sm btn-danger" onclick="deletePayment(${p.id}, true)" style="opacity:0.7;" title="Permanently delete this payment from database">Delete Permanently</button>
            </div>
        </div>
    `;
                }
            )
            .join("") +
        "</div>"
    );
}

function renderNotifications(notifications) {
    if (!notifications.length) return '<p class="text-muted">No notifications yet</p>';
    return (
        '<div class="payments-list">' +
        notifications
            .map(
                (n) => `
        <div class="payment-item">
            <div class="payment-info">
                <h4 style="font-size:13px;">${escapeHtml(n.trainer_username || "Admin")}</h4>
                <div class="client-meta">${formatDate(n.created_at)}</div>
                <div style="margin-top:4px;font-size:13px;">${escapeHtml(n.message)}</div>
            </div>
            ${!n.is_read ? `<button class="btn btn-sm btn-outline" onclick="markNotificationRead(${n.id})">Mark Read</button>` : ""}
        </div>
    `,
            )
            .join("") +
        "</div>"
    );
}

function renderRenewals(renewals) {
    return '<p class="text-muted">Renewal tracking removed - PT software only</p>';
}

function renderOverdue(overdueClients) {
    return '<p class="text-muted">Renewal tracking removed - PT software only</p>';
}

function applyStats(data) {
    const totalIncome = document.getElementById("total-income");
    const monthlyIncome = document.getElementById("monthly-income");
    const activeClients = document.getElementById("active-clients");
    const lostClients = document.getElementById("lost-clients");

    if (totalIncome) totalIncome.textContent = formatCurrency(data.total_income);
    if (monthlyIncome) monthlyIncome.textContent = formatCurrency(data.monthly_income);
    if (activeClients) activeClients.textContent = data.total_active_clients;
    if (lostClients) lostClients.textContent = data.total_lost_clients;

    if (!IS_ADMIN && data.payout_summary) {
        const payout = document.getElementById("estimated-payout");
        const meta = document.getElementById("payout-meta");
        if (payout) payout.textContent = formatCurrency(data.payout_summary.estimated_payout);
        if (meta) meta.textContent = `${data.payout_summary.payout_percent}% | Target ${formatCurrency(data.payout_summary.monthly_target)} | ${data.payout_summary.payout_rule}`;
    }
}

async function loadExpiringClients(force = false) {
    const listEl = document.getElementById("expiring-clients-list");
    if (!listEl) return;

    const cached = !force && Cache.get("expiring_list", 20000);
    if (cached) {
        listEl.innerHTML = renderExpiringClients(cached.clients);
        return;
    }

    setLoading("expiring-clients-list", "Loading expiring clients...");

    try {
        const r = await apiFetch(`${API_BASE}/api/expiring-clients`);
        if (!r.ok) return;
        const data = await r.json();
        Cache.set("expiring_list", data);

        // Update the stat card count
        const expiringEl = document.getElementById("expiring-clients");
        if (expiringEl) expiringEl.textContent = data.count || 0;

        listEl.innerHTML = renderExpiringClients(data.clients);
    } catch (e) {
        console.error("Expiring clients error:", e);
        listEl.innerHTML = '<p class="text-muted">Failed to load expiring clients</p>';
    }
}

function renderExpiringClients(clients) {
    if (!clients || !clients.length) {
        return '<p class="text-muted">✅ No clients expiring in the next 5 days!</p>';
    }

    return (
        '<div class="clients-list">' +
        clients
            .map((c) => {
                const daysUntil = c.days_until;
                const urgencyColor = daysUntil <= 0 ? '#ef4444' : daysUntil <= 2 ? '#f59e0b' : '#10b981';
                const urgencyText = daysUntil <= 0 ? 'EXPIRED' : daysUntil === 0 ? 'TODAY' : `${daysUntil} days`;
                const emailBtn = c.email
                    ? `<button class="btn btn-sm btn-warning" onclick="sendReminderToClient(${c.id})" title="Send renewal reminder email">📧 Send Email</button>`
                    : '<span class="text-muted" style="font-size:11px;">No email</span>';

                return `<div class="client-item" style="border-left: 4px solid ${urgencyColor};">
                    <div class="client-info">
                        <h4>${escapeHtml(c.name)}</h4>
                        <div class="client-meta">
                            <span style="color:${urgencyColor};font-weight:600;">⏰ ${urgencyText}</span>
                            <span>Renewal: ${formatDate(c.renewal_date)}</span>
                            <span>${escapeHtml(c.pt_tier || "Silver")}</span>
                            <span>${c.contact_number}</span>
                            ${c.email ? `<span>📧 ${escapeHtml(c.email)}</span>` : ''}
                        </div>
                    </div>
                    <div class="client-actions">
                        ${emailBtn}
                        <button class="btn btn-sm btn-outline" onclick="editClient(${c.id})">Edit</button>
                    </div>
                </div>`;
            })
            .join("") +
        "</div>"
    );
}

async function sendReminderToClient(clientId) {
    if (!confirm("Send renewal reminder email to this client?")) return;

    try {
        const r = await apiFetch(`${API_BASE}/api/reminders/send`, {
            method: "POST",
            body: JSON.stringify({ type: "specific", client_id: clientId }),
        });
        const data = await parseApiResponse(r, "Failed to send reminder.");
        const msg = data.message || `Renewal reminder sent successfully!`;
        showToast(msg, "success");

        // Refresh the expiring clients list
        await loadExpiringClients(true);
    } catch (e) {
        console.error(e);
        showToast(e.message || "Error sending reminder.", "error");
    }
}

async function sendExpiringRenewalReminders() {
    if (!confirm("Send renewal reminder emails to ALL clients expiring in the next 5 days?\n\nOnly clients with email reminders enabled will receive emails.")) return;

    try {
        const r = await apiFetch(`${API_BASE}/api/reminders/send`, {
            method: "POST",
            body: JSON.stringify({ type: "due_closest" }),
        });
        const data = await parseApiResponse(r, "Failed to send reminders.");
        const msg = data.message || `Dispatched ${data.sent_count ?? 0} renewal reminder(s).`;
        showToast(msg, "success", 6000);

        // Refresh the expiring clients list
        await loadExpiringClients(true);
    } catch (e) {
        console.error(e);
        showToast(e.message || "Error sending reminders.", "error");
    }
}

async function loadStats(force = false) {
    const cached = !force && Cache.get("stats", 20000);
    if (cached) {
        applyStats(cached);
        return;
    }
    try {
        const r = await apiFetch(`${API_BASE}/api/stats`);
        if (!r.ok) {
            console.error("Stats load failed:", r.status);
            return;
        }
        const data = await r.json();
        Cache.set("stats", data);
        applyStats(data);
    } catch (e) {
        console.error("Stats error:", e);
        // Don't show toast on initial load failure - wakeup UI will handle it
    }
}

async function refreshAllData() {
    showToast("Refreshing all data...", "info", 2000);
    Cache.invalidate("stats", "insights", "expiring", "expiring_list");
    try {
        await Promise.all([
            loadStats(true),
            loadInsights(true),
            loadClients(true),
            loadPayments(true),
            loadNotifications(),
            loadExpiringClients(true),
            loadEmailLogs(1),
            loadExpiringClients(true),
        ]);
        showToast("All data refreshed successfully!", "success");
    } catch (e) {
        console.error("Refresh error:", e);
        showToast("Error refreshing data", "error");
    }
}

async function loadInsights(force = false) {
    const cached = !force && Cache.get("insights", 30000);
    if (cached) {
        applyInsights(cached);
        return;
    }
    try {
        const r = await apiFetch(`${API_BASE}/api/insights`);
        if (!r.ok) return;
        const data = await r.json();
        Cache.set("insights", data);
        applyInsights(data);
    } catch (e) {
        console.error("Insights error:", e);
    }
}

function applyInsights(data) {
    const retention = document.getElementById("retention-rate");
    const netProfit = document.getElementById("net-profit");
    const atRisk = document.getElementById("at-risk-count");
    const summary = document.getElementById("insight-summary");

    if (retention) retention.textContent = `${Number(data.retention_rate || 0).toFixed(1)}%`;
    if (netProfit) netProfit.textContent = formatCurrency(data.net_profit || 0);
    if (atRisk) atRisk.textContent = String(data.at_risk_clients || 0);

    const topClient = (data.top_clients_by_clv || [])[0];
    if (summary) {
        summary.textContent = topClient
            ? `Top CLV: ${topClient.client_name} (${formatCurrency(topClient.lifetime_value)}). Expense categories tracked: ${(data.expense_breakdown || []).length}.`
            : "No CLV data yet. Add more payments to unlock trend insights.";
    }

    renderRevenueChart(data.timeline || []);
}

function renderRevenueChart(timeline) {
    const canvas = document.getElementById("revenue-chart");
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    const width = canvas.clientWidth || 800;
    const height = 120;
    canvas.width = width;
    canvas.height = height;

    ctx.clearRect(0, 0, width, height);
    if (!timeline.length) {
        ctx.fillStyle = "#64748b";
        ctx.font = "12px Outfit";
        ctx.fillText("No revenue data for selected period", 12, 24);
        return;
    }

    const values = timeline.map((t) => Number(t.amount || 0));
    const maxVal = Math.max(...values, 1);
    const pad = 16;
    const stepX = (width - pad * 2) / Math.max(values.length, 1);
    const barWidth = Math.max(stepX * 0.6, 10);

    ctx.fillStyle = "#f97316";

    values.forEach((v, i) => {
        const h = (v / maxVal) * (height - pad * 2);
        const x = pad + i * stepX + (stepX - barWidth) / 2;
        const y = height - pad - h;
        
        ctx.beginPath();
        if (ctx.roundRect) {
            ctx.roundRect(x, y, barWidth, h, [4, 4, 0, 0]);
        } else {
            ctx.rect(x, y, barWidth, h);
        }
        ctx.fill();
    });
}

function updatePager(metaId, pagination) {
    const el = document.getElementById(metaId);
    if (!el || !pagination) return;
    const total = pagination.total || 0;
    el.textContent = `Page ${pagination.page} of ${pagination.pages} • ${total} total`;
}

async function loadClients(force = false) {
    const listEl = document.getElementById("clients-list");
    if (!listEl) return;
    if (force) setLoading("clients-list", "Loading clients...");

    const params = new URLSearchParams({
        paginated: "1",
        page: String(state.clientsPagination.page || 1),
        per_page: String(state.clientsPagination.per_page || 20),
        sort_by: "name",
        sort_order: "asc",
    });
    if (state.clientFilter !== "all") params.set("status", state.clientFilter);
    if (state.clientSearch.trim()) params.set("q", state.clientSearch.trim());

    try {
        const r = await apiFetch(`${API_BASE}/api/clients?${params.toString()}`);
        if (!r.ok) return;
        const data = await r.json();
        state.clients = data.items || [];
        state.clientsPagination = data.pagination || state.clientsPagination;
        listEl.innerHTML = renderClients(state.clients);
        updatePager("clients-page-meta", state.clientsPagination);
        populateClientsDropdownFromCache();
    } catch (e) {
        console.error("Clients error:", e);
    }
}

async function loadPayments(force = false) {
    const listEl = document.getElementById("payments-list");
    if (!listEl) return;
    if (force) setLoading("payments-list", "Loading payments...");

    const params = new URLSearchParams({
        paginated: "1",
        page: String(state.paymentsPagination.page || 1),
        per_page: String(state.paymentsPagination.per_page || 20),
    });
    if (state.paymentSearch.trim()) params.set("q", state.paymentSearch.trim());

    try {
        const r = await apiFetch(`${API_BASE}/api/payments?${params.toString()}`);
        if (!r.ok) return;
        const data = await r.json();
        state.payments = data.items || [];
        state.paymentsPagination = data.pagination || state.paymentsPagination;
        listEl.innerHTML = renderPayments(state.payments);
        updatePager("payments-page-meta", state.paymentsPagination);
    } catch (e) {
        console.error("Payments error:", e);
    }
}

async function loadAdminTrainers(force = false) {
    if (!IS_ADMIN && !force) return [];
    if (!force && state.adminTrainers.length) {
        populateClientTrainerDropdown(state.adminTrainers, state.selectedClientTrainerId);
        return state.adminTrainers;
    }

    try {
        const r = await apiFetch(`${API_BASE}/api/admin/trainers`);
        if (!r.ok) return [];
        state.adminTrainers = await r.json();
        populateClientTrainerDropdown(state.adminTrainers, state.selectedClientTrainerId);
        return state.adminTrainers;
    } catch (e) {
        console.error("Trainer load error:", e);
        return [];
    }
}

function populateClientsDropdownFromCache() {
    const select = document.getElementById("payment-client");
    if (!select) return;
    const clients = (state.clients || []).filter((c) => c.status === "ongoing");
    const current = select.value;
    select.innerHTML =
        '<option value="">Select client</option>' +
        clients
            .map(
                (c) =>
                    `<option value="${c.id}" data-amount="${c.expected_amount || 0}" data-tier="${escapeHtml(c.pt_tier || "Silver")}">${escapeHtml(c.name)} (${escapeHtml(c.pt_tier || "Silver")})</option>`,
            )
            .join("");
    if (current) select.value = current;
}

function populateClientTrainerDropdown(trainers, selectedTrainerId = "") {
    const select = document.getElementById("client-trainer");
    if (!select) return;
    const current = selectedTrainerId !== "" ? String(selectedTrainerId) : String(select.value || "");
    select.required = trainers.length > 0;
    if (!trainers.length) {
        select.innerHTML = '<option value="">No trainers available</option>';
        select.value = "";
        return;
    }
    select.innerHTML = '<option value="">Select trainer</option>' + trainers.map((t) => `<option value="${t.id}">${escapeHtml(t.username)}</option>`).join("");
    if (current) select.value = current;
    else if (trainers.length === 1) select.value = String(trainers[0].id);
}

function filterClients(status, btn) {
    state.clientFilter = status;
    state.clientsPagination.page = 1;
    document.querySelectorAll(".filter-bar .btn").forEach((b) => b.classList.remove("active"));
    if (btn) btn.classList.add("active");
    void loadClients(true);
}

function changeClientsPage(delta) {
    const nextPage = state.clientsPagination.page + delta;
    if (nextPage < 1 || nextPage > state.clientsPagination.pages) return;
    state.clientsPagination.page = nextPage;
    void loadClients(true);
}

function changePaymentsPage(delta) {
    const nextPage = state.paymentsPagination.page + delta;
    if (nextPage < 1 || nextPage > state.paymentsPagination.pages) return;
    state.paymentsPagination.page = nextPage;
    void loadPayments(true);
}

const debouncedClientSearch = debounce(() => {
    state.clientsPagination.page = 1;
    void loadClients(true);
}, 300);

const debouncedPaymentSearch = debounce(() => {
    state.paymentsPagination.page = 1;
    void loadPayments(true);
}, 300);

function handleClientSearchInput(event) {
    state.clientSearch = event.target.value || "";
    debouncedClientSearch();
}

function handlePaymentSearchInput(event) {
    state.paymentSearch = event.target.value || "";
    debouncedPaymentSearch();
}

async function loadNotifications() {
    const container = document.getElementById("notifications-list");
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
        console.error("Notifications error:", e);
    }
}

async function markNotificationRead(id) {
    try {
        const r = await apiFetch(`${API_BASE}/api/admin/notifications/${id}/read`, { method: "POST" });
        if (r.ok) loadNotifications();
    } catch (e) {
        console.error(e);
    }
}

async function sendReminders(type, clientId = null) {
    if (!confirm(type === "specific" ? "Send reminder to this client?" : `Send ${type === "all" ? "all" : "due"} reminders now?`)) return;
    try {
        const payload = { type };
        if (clientId) payload.client_id = clientId;
        const r = await apiFetch(`${API_BASE}/api/reminders/send`, {
            method: "POST",
            body: JSON.stringify(payload),
        });
        const data = await parseApiResponse(r, "Failed to send reminders.");
        const msg = data.message || r.message || `Dispatched ${data.sent_count ?? 0} reminder(s).`;
        showToast(msg, "success");
    } catch (e) {
        console.error(e);
        showToast(e.message || "Error sending reminders.", "error");
    }
}

function sendRenewalReminders() {
    sendReminders("due_closest");
}

function openModal(modalId) {
    const modal = document.getElementById(modalId);
    if (!modal) return;
    modal.classList.add("active");

    if (modalId === "client-modal") {
        const form = document.getElementById("client-form");
        if (form) form.reset();
        document.getElementById("client-id").value = "";
        document.getElementById("client-modal-title").textContent = "Add Client";
        state.selectedClientTrainerId = "";
        if (IS_ADMIN) void loadAdminTrainers();
        updateExpectedAmount();
    }

    if (modalId === "payment-modal") {
        const form = document.getElementById("payment-form");
        if (form) form.reset();
        const today = new Date().toISOString().slice(0, 10);
        const paymentDate = document.getElementById("payment-date");
        const startDate = document.getElementById("payment-start-date");
        const duration = document.getElementById("payment-duration");
        const planType = document.getElementById("payment-plan-type");
        if (paymentDate) paymentDate.value = today;
        if (startDate) startDate.value = today;
        if (duration) duration.value = 1;
        if (planType) planType.value = "monthly";
        
        const paymentMode = document.getElementById("payment-mode");
        if (paymentMode) {
            paymentMode.value = "cash";
            handlePaymentModeChange();
        }
        
        handlePlanTypeChange();
        updatePaymentAmount();
        updateTotalPayment();
    }
}

function handlePaymentModeChange() {
    const mode = document.getElementById("payment-mode")?.value;
    const splitGroup = document.getElementById("payment-split-group");
    if (splitGroup) {
        splitGroup.style.display = (mode === "split") ? "flex" : "none";
    }
}

function closeModal(modalId) {
    const modal = document.getElementById(modalId);
    if (modal) modal.classList.remove("active");
}

async function handleClientSubmit(event) {
    event.preventDefault();
    const id = document.getElementById("client-id").value;
    const timeSlot = document.getElementById("client-time").value;

    const data = {
        name: document.getElementById("client-name").value,
        contact_number: document.getElementById("client-contact").value,
        email: document.getElementById("client-email").value,
        status: document.getElementById("client-status").value,
        pt_tier: document.getElementById("client-pt-tier").value,
        time_slot: timeSlot,
        gym_name: document.getElementById("client-gym-name")?.value || "",
        renewal_date: document.getElementById("client-renewal-date")?.value || null,
        send_email_reminders: document.getElementById("client-email-reminders").checked,
        notes: document.getElementById("client-notes").value,
    };

    if (!data.name.trim()) {
        showToast("Client name is required.", "error");
        return;
    }

    if (IS_ADMIN) {
        const trainerSelect = document.getElementById("client-trainer");
        if (trainerSelect && trainerSelect.value) data.trainer_id = parseInt(trainerSelect.value, 10);
    }

    if (timeSlot && state.clients) {
        const clash = state.clients.some((c) => c.time_slot === timeSlot && String(c.id) !== id && c.status === "ongoing");
        if (clash && !confirm("Another active client has this time slot. Proceed anyway?")) return;
    }

    const url = id ? `${API_BASE}/api/clients/${id}` : `${API_BASE}/api/clients`;
    const method = id ? "PUT" : "POST";

    try {
        const response = await apiFetch(url, {
            method,
            body: JSON.stringify(data),
        });
        if (!response.ok) {
            alert(await readErrorMessage(response, "Error saving client"));
            return;
        }
        const saved = await response.json();
        closeModal("client-modal");

        if (saved.message) {
            showToast(saved.message, saved.welcome_email_sent || !saved.email ? "success" : "warning", 5000);
        } else if (!id) {
            showToast("Client created successfully!", "success");
        } else {
            showToast("Client updated successfully!", "success");
        }

        // Optimized: Invalidate cache and reload only what's necessary
        Cache.invalidate("stats", "insights", "clients");

        // Load clients first (main data), then stats in background
        loadClients(true).then(() => {
            loadStats(true);
            loadInsights(true);
        });
    } catch (e) {
        console.error(e);
        alert("Error saving client");
    }
}

async function editClient(id) {
    const local = (state.clients || []).find((c) => c.id === id);
    if (local) {
        openModal("client-modal");
        populateClientForm(local);
        return;
    }

    try {
        const r = await apiFetch(`${API_BASE}/api/clients/${id}`);
        if (!r.ok) return;
        const data = await r.json();
        openModal("client-modal");
        populateClientForm(data);
    } catch (e) {
        console.error(e);
    }
}

function populateClientForm(client) {
    state.selectedClientTrainerId = client.trainer_id || "";
    document.getElementById("client-id").value = client.id;
    document.getElementById("client-name").value = client.name || "";
    document.getElementById("client-contact").value = client.contact_number && client.contact_number !== "N/A" ? client.contact_number : "";
    document.getElementById("client-email").value = client.email || "";
    document.getElementById("client-status").value = client.status || "ongoing";
    document.getElementById("client-pt-tier").value = client.pt_tier || "Silver";
    document.getElementById("client-time").value = client.time_slot || "";
    if (document.getElementById("client-gym-name")) {
        document.getElementById("client-gym-name").value = client.gym_name || "";
    }
    if (document.getElementById("client-renewal-date")) {
        document.getElementById("client-renewal-date").value = client.renewal_date || "";
    }
    document.getElementById("client-email-reminders").checked = Boolean(client.send_email_reminders);
    document.getElementById("client-notes").value = client.notes || "";

    if (IS_ADMIN) populateClientTrainerDropdown(state.adminTrainers, state.selectedClientTrainerId);

    document.getElementById("client-modal-title").textContent = "Edit Client";
    updateExpectedAmount();
}

async function deleteClient(id, permanent = false) {
    const client = (state.clients || []).find((c) => c.id === id);
    const clientName = client ? client.name : "this client";
    const isLostClient = client && client.status === "lost";

    if (permanent) {
        const confirmMsg = `⚠️ WARNING: PERMANENT DELETE ⚠️\n\nYou are about to PERMANENTLY DELETE "${clientName}".\n\nThis action will:\n• Remove the client completely from the database\n• Delete ALL associated payments\n• Delete ALL attendance records\n• Delete ALL progress photos\n• This CANNOT be undone\n\nType DELETE in the box below to confirm:`;

        const userInput = prompt(confirmMsg);
        if (userInput !== "DELETE") {
            if (userInput !== null) {
                alert("Deletion cancelled. You must type DELETE exactly to confirm.");
            }
            return;
        }

        const doubleConfirm = confirm(`Final confirmation: Permanently delete "${clientName}" and all associated data?\n\nThis is your last chance to cancel.`);
        if (!doubleConfirm) return;

        try {
            const r = await apiFetch(`${API_BASE}/api/clients/${id}`, { method: "DELETE" });
            if (!r.ok) {
                alert(await readErrorMessage(r, "Could not delete client."));
                return;
            }
            showToast(`Client "${clientName}" permanently deleted`, "success");

            // Optimized: Remove from local state immediately for instant UI update
            state.clients = state.clients.filter(c => c.id !== id);
            const listEl = document.getElementById("clients-list");
            if (listEl) listEl.innerHTML = renderClients(state.clients);

            // Invalidate cache and refresh in background
            Cache.invalidate("stats", "insights", "clients");
            loadStats(true);
            loadInsights(true);
        } catch (e) {
            console.error(e);
            alert("Error deleting client");
        }
        return;
    }

    // If client is already lost, permanently delete them
    if (isLostClient) {
        if (!confirm(`Permanently delete "${clientName}"? This will remove all data and cannot be undone.`)) return;

        try {
            const r = await apiFetch(`${API_BASE}/api/clients/${id}`, { method: "DELETE" });
            if (!r.ok) {
                alert(await readErrorMessage(r, "Could not delete client."));
                return;
            }
            showToast(`Client "${clientName}" permanently deleted`, "success");

            // Optimized: Remove from local state immediately for instant UI update
            state.clients = state.clients.filter(c => c.id !== id);
            const listEl = document.getElementById("clients-list");
            if (listEl) listEl.innerHTML = renderClients(state.clients);

            Cache.invalidate("stats", "insights", "clients");
            loadStats(true);
            loadInsights(true);
        } catch (e) {
            console.error(e);
            alert("Error deleting client");
        }
        return;
    }

    // If client is ongoing, move to lost
    if (!confirm("Move this client to the Lost section?")) return;
    try {
        const r = await apiFetch(`${API_BASE}/api/clients/${id}`, {
            method: "PUT",
            body: JSON.stringify({ status: "lost" }),
        });
        if (!r.ok) {
            alert(await readErrorMessage(r, "Could not update client."));
            return;
        }
        showToast("Client moved to Lost section", "success");

        // Optimized: Update local state immediately
        const clientIndex = state.clients.findIndex(c => c.id === id);
        if (clientIndex !== -1) {
            state.clients[clientIndex].status = "lost";
            const listEl = document.getElementById("clients-list");
            if (listEl) listEl.innerHTML = renderClients(state.clients);
        }

        Cache.invalidate("stats", "insights", "clients");
        loadStats(true);
        loadInsights(true);
    } catch (e) {
        console.error(e);
    }
}

async function handlePaymentSubmit(event) {
    event.preventDefault();
    const clientId = document.getElementById("payment-client").value;
    const planType = document.getElementById("payment-plan-type").value;
    const sessionDays = document.getElementById("payment-session-days").value;
    const startDate = document.getElementById("payment-start-date").value;
    const amount = parseFloat(document.getElementById("payment-amount").value || "0");
    const duration = parseInt(document.getElementById("payment-duration").value || "1", 10);
    const paymentDate = document.getElementById("payment-date").value;
    const description = document.getElementById("payment-description").value;

    if (!clientId || !paymentDate || !startDate || !(amount > 0) || !(duration > 0)) {
        alert("Please fill all required payment fields.");
        return;
    }

    let finalDescription = description;
    const paymentMode = document.getElementById("payment-mode")?.value || "cash";

    if (paymentMode === "split") {
        const cashAmount = parseFloat(document.getElementById("payment-cash-amount")?.value || "0");
        const onlineAmount = parseFloat(document.getElementById("payment-online-amount")?.value || "0");
        const splitText = `Cash: ₹${cashAmount}, Online: ₹${onlineAmount}`;
        finalDescription = finalDescription ? `${finalDescription} (${splitText})` : splitText;
    }

    const gymPaymentDone = document.getElementById("payment-gym-done")?.checked || false;
    const gymPaymentAmount = parseFloat(document.getElementById("payment-gym-amount")?.value || "0");

    const payload = {
        client_id: parseInt(clientId, 10),
        amount,
        payment_date: paymentDate,
        description: finalDescription,
        duration_months: duration,
        plan_type: planType,
        session_days: sessionDays,
        start_date: startDate,
        payment_mode: paymentMode,
        gym_payment_done: gymPaymentDone,
        gym_payment_amount: gymPaymentAmount > 0 ? gymPaymentAmount : null,
    };

    try {
        const r = await apiFetch(`${API_BASE}/api/payments`, {
            method: "POST",
            body: JSON.stringify(payload),
        });
        if (!r.ok) {
            alert(await readErrorMessage(r, "Error saving payment"));
            return;
        }

        closeModal("payment-modal");
        showToast("Payment logged successfully!", "success");

        // Optimized: Invalidate cache and load sequentially
        Cache.invalidate("stats", "insights", "payments", "clients");

        // Load payments first (immediate), then stats in background
        loadPayments(true).then(() => {
            loadClients(true);
            loadStats(true);
            loadInsights(true);
        });
    } catch (e) {
        console.error(e);
        alert("Error saving payment");
    }
}

async function deletePayment(id, permanent = false) {
    const payment = (state.payments || []).find((p) => p.id === id);
    const paymentInfo = payment ? `${formatCurrency(payment.amount)} from ${payment.client_name}` : "this payment";

    if (permanent) {
        const confirmMsg = `⚠️ WARNING: PERMANENT DELETE ⚠️\n\nYou are about to PERMANENTLY DELETE:\n${paymentInfo}\n\nThis action will:\n• Remove the payment completely from the database\n• Affect income statistics and reports\n• Affect client renewal calculations\n• This CANNOT be undone\n\nType DELETE in the box below to confirm:`;

        const userInput = prompt(confirmMsg);
        if (userInput !== "DELETE") {
            if (userInput !== null) {
                alert("Deletion cancelled. You must type DELETE exactly to confirm.");
            }
            return;
        }

        const doubleConfirm = confirm(`Final confirmation: Permanently delete payment record?\n\n${paymentInfo}\n\nThis is your last chance to cancel.`);
        if (!doubleConfirm) return;
    } else {
        if (!confirm(`Delete this payment record?\n\n${paymentInfo}`)) return;
    }

    try {
        const r = await apiFetch(`${API_BASE}/api/payments/${id}`, { method: "DELETE" });
        if (!r.ok) {
            alert(await readErrorMessage(r, "Error deleting payment"));
            return;
        }
        showToast(permanent ? "Payment permanently deleted" : "Payment deleted", "success");

        // Optimized: Remove from local state immediately for instant UI update
        state.payments = state.payments.filter(p => p.id !== id);
        const listEl = document.getElementById("payments-list");
        if (listEl) listEl.innerHTML = renderPayments(state.payments);

        // Invalidate cache and refresh stats in background
        Cache.invalidate("stats", "insights", "payments");
        loadStats(true);
        loadInsights(true);
    } catch (e) {
        console.error(e);
        alert("Error deleting payment");
    }
}

function handlePlanTypeChange() {
    const planType = document.getElementById("payment-plan-type").value;
    const sessionGroup = document.getElementById("payment-session-days-group");
    const durationLabel = document.getElementById("payment-duration-label");
    if (sessionGroup) sessionGroup.style.display = planType === "session" ? "" : "none";
    if (durationLabel) durationLabel.textContent = planType === "session" ? "Number of Sessions *" : "Duration (Months) *";
    updateTotalPayment();
}

function calculateEndDate(startDateStr, duration, planType, sessionDays) {
    if (!startDateStr || !duration || duration < 1) return null;
    const start = new Date(startDateStr + "T00:00:00");
    if (Number.isNaN(start.getTime())) return null;

    if (planType !== "session") {
        const end = new Date(start);
        end.setDate(end.getDate() + duration * 30);
        return end;
    }

    const validDays = sessionDays === "MWF" ? [1, 3, 5] : [2, 4, 6];
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
    const amount = parseFloat((document.getElementById("payment-amount") || {}).value || "0");
    const duration = parseInt((document.getElementById("payment-duration") || {}).value || "1", 10);
    const planType = (document.getElementById("payment-plan-type") || {}).value || "monthly";
    const sessionDays = (document.getElementById("payment-session-days") || {}).value || "MWF";
    const startDate = (document.getElementById("payment-start-date") || {}).value || "";

    const total = amount > 0 && duration > 0 ? amount * duration : 0;
    const totalDisplay = document.getElementById("payment-total-display");
    if (totalDisplay) totalDisplay.textContent = `Total: ${formatCurrency(total)}`;

    const end = calculateEndDate(startDate, duration, planType, sessionDays);
    const endDisplay = document.getElementById("payment-end-date-display");
    if (endDisplay) {
        endDisplay.textContent = end
            ? `End Date: ${end.toLocaleDateString("en-IN", { day: "numeric", month: "short", year: "numeric" })}`
            : "End Date: -";
    }
}

function updateExpectedAmount() {
    // Disabled as amount is directly input now
}

function updatePaymentAmount() {
    const select = document.getElementById("payment-client");
    const paymentAmount = document.getElementById("payment-amount");
    if (!select || !paymentAmount) return;
    const opt = select.options[select.selectedIndex];
    const expected = opt ? Number(opt.getAttribute("data-amount") || "0") : 0;
    if (expected > 0) paymentAmount.value = expected;
    updateTotalPayment();
}

async function loadAttendanceFeed() {
    const container = document.getElementById("attendance-list");
    if (!container) return;
    setLoading("attendance-list", "Loading attendance...");

    try {
        const r = await apiFetch(`${API_BASE}/api/tracking/attendance-calendar?days=21`);
        if (!r.ok) {
            container.innerHTML = '<p class="text-muted">Unable to load attendance feed</p>';
            return;
        }
        const data = await r.json();
        const events = data.events || [];
        if (!events.length) {
            container.innerHTML = '<p class="text-muted">No attendance entries yet</p>';
            return;
        }
        container.innerHTML =
            '<div class="payments-list">' +
            events
                .slice(0, 20)
                .map(
                    (e) => `
            <div class="payment-item">
                <div class="payment-info">
                    <h4>${escapeHtml(e.client_name)} <span class="status-badge status-${e.status === "attended" ? "ongoing" : "lost"}">${escapeHtml(e.status)}</span></h4>
                    <div class="client-meta">
                        <span>${formatDate(e.date)}</span>
                        <span>${e.duration_minutes || 0} mins</span>
                    </div>
                </div>
            </div>
        `,
                )
                .join("") +
            "</div>";
    } catch (e) {
        console.error(e);
        container.innerHTML = '<p class="text-muted">Unable to load attendance feed</p>';
    }
}

function downloadExport(type) {
    window.location.href = `${API_BASE}/api/export/${type}`;
}

function downloadBackupJson() {
    window.location.href = `${API_BASE}/api/export/backup-json`;
}

async function loadImpersonateDropdown() {
    const dropdown = document.getElementById("impersonate-dropdown");
    if (!dropdown) return;

    try {
        const r = await apiFetch(`${API_BASE}/api/admin/trainers`);
        if (!r.ok) return;
        const trainers = await r.json();

        dropdown.innerHTML = '<option value="">🔄 Switch User</option>' +
            trainers.map(t => `<option value="${t.id}">${escapeHtml(t.username)}</option>`).join('');
    } catch (error) {
        console.error('Error loading trainers for impersonation:', error);
    }
}

async function switchUser(trainerId) {
    if (!trainerId) return;

    try {
        const r = await apiFetch(`${API_BASE}/api/impersonate/switch/${trainerId}`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' }
        });

        if (!r.ok) {
            const data = await r.json();
            alert(data.error || 'Failed to switch user');
            return;
        }

        // Reload the page to reflect the new user context
        window.location.reload();
    } catch (error) {
        console.error('Error switching user:', error);
        alert('Failed to switch user');
    }
}

async function checkImpersonationStatus() {
    try {
        const r = await apiFetch(`${API_BASE}/api/impersonate/status`);
        if (!r.ok) return;
        const status = await r.json();

        if (status.is_impersonating) {
            // Add a "Return to Admin" button
            const navUser = document.querySelector('.nav-user');
            if (navUser && !document.getElementById('return-to-admin-btn')) {
                const returnBtn = document.createElement('button');
                returnBtn.id = 'return-to-admin-btn';
                returnBtn.className = 'btn btn-sm btn-warning';
                returnBtn.textContent = '↩️ Return to Admin';
                returnBtn.onclick = stopImpersonating;
                navUser.insertBefore(returnBtn, navUser.firstChild);
            }
        }
    } catch (error) {
        console.error('Error checking impersonation status:', error);
    }
}

async function stopImpersonating() {
    try {
        const r = await apiFetch(`${API_BASE}/api/impersonate/stop`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' }
        });

        if (!r.ok) {
            const data = await r.json();
            alert(data.error || 'Failed to return to admin');
            return;
        }

        // Reload the page to return to admin context
        window.location.reload();
    } catch (error) {
        console.error('Error stopping impersonation:', error);
        alert('Failed to return to admin');
    }
}

const emailLogsState = {
    currentPage: 1,
    perPage: 20
};

async function loadEmailLogs(page = 1) {
    const container = document.getElementById('email-logs-list');
    if (!container) return;

    container.innerHTML = '<p class="text-muted">Loading...</p>';
    emailLogsState.currentPage = page;

    try {
        const typeFilter = document.getElementById('email-log-type-filter')?.value || '';
        const statusFilter = document.getElementById('email-log-status-filter')?.value || '';
        const daysFilter = document.getElementById('email-log-days-filter')?.value || '30';

        const params = new URLSearchParams({
            page: String(page),
            per_page: String(emailLogsState.perPage),
            days: daysFilter
        });
        if (typeFilter) params.append('email_type', typeFilter);
        if (statusFilter) params.append('status', statusFilter);

        const r = await apiFetch(`${API_BASE}/api/email-logs?${params}`);
        if (!r.ok) {
            container.innerHTML = '<p class="text-muted">Unable to load email logs</p>';
            return;
        }

        const data = await r.json();

        if (!data.items || data.items.length === 0) {
            container.innerHTML = '<p class="text-muted">No email logs found</p>';
            updateEmailLogsPager({ page: 1, pages: 1, has_prev: false, has_next: false });
            return;
        }

        container.innerHTML = '<div class="payments-list">' + data.items.map(log => {
            const statusColor = log.status === 'sent' ? '#22c55e' : '#ef4444';
            const statusIcon = log.status === 'sent' ? '✓' : '✗';
            return `
                <div class="payment-item">
                    <div class="payment-info">
                        <h4>${escapeHtml(log.recipient_name || 'N/A')}
                            <span style="background:rgba(${log.status === 'sent' ? '34,197,94' : '239,68,68'},0.1);border:1px solid rgba(${log.status === 'sent' ? '34,197,94' : '239,68,68'},0.3);border-radius:4px;padding:1px 7px;font-size:11px;color:${statusColor};">${statusIcon} ${escapeHtml(log.status)}</span>
                        </h4>
                        <div class="client-meta">
                            <span>${escapeHtml(log.recipient_email)}</span>
                            <span>${escapeHtml(log.email_type || 'N/A')}</span>
                            <span>${formatDate(log.sent_at)}</span>
                        </div>
                        <div style="margin-top:4px;font-size:12px;color:var(--text-muted);">${escapeHtml(log.subject)}</div>
                        ${log.error_message ? `<div style="margin-top:4px;font-size:11px;color:#ef4444;">Error: ${escapeHtml(log.error_message)}</div>` : ''}
                    </div>
                </div>
            `;
        }).join('') + '</div>';

        updateEmailLogsPager(data.pagination || { page, pages: 1, has_prev: false, has_next: false });

        // Load stats separately
        await loadEmailStats();
    } catch (error) {
        console.error('Error loading email logs:', error);
        container.innerHTML = '<p class="text-muted">Unable to load email logs</p>';
    }
}

async function loadEmailStats() {
    try {
        const daysFilter = document.getElementById('email-log-days-filter')?.value || '30';
        const r = await apiFetch(`${API_BASE}/api/email-logs/stats?days=${daysFilter}`);
        if (!r.ok) return;

        const stats = await r.json();
        updateEmailStats(stats);
    } catch (error) {
        console.error('Error loading email stats:', error);
    }
}

function updateEmailStats(stats) {
    const sentEl = document.getElementById('email-stats-sent');
    const failedEl = document.getElementById('email-stats-failed');
    const rateEl = document.getElementById('email-stats-rate');

    if (sentEl) sentEl.textContent = String(stats.total_sent || 0);
    if (failedEl) failedEl.textContent = String(stats.total_failed || 0);
    if (rateEl) {
        const rate = stats.success_rate || 0;
        rateEl.textContent = `${rate}%`;
    }
}

function updateEmailLogsPager(pagination) {
    const pagerEl = document.getElementById('email-logs-pager');
    const metaEl = document.getElementById('email-logs-page-meta');
    if (!pagerEl) return;

    if (metaEl) {
        metaEl.textContent = `Page ${pagination.page} of ${pagination.pages}`;
    }

    const prevBtn = pagerEl.querySelector('button:first-child');
    const nextBtn = pagerEl.querySelector('button:last-child');
    if (prevBtn) prevBtn.disabled = !pagination.has_prev;
    if (nextBtn) nextBtn.disabled = !pagination.has_next;
}

function filterEmailLogs() {
    loadEmailLogs(1);
}

function changeEmailLogsPage(delta) {
    const newPage = emailLogsState.currentPage + delta;
    if (newPage >= 1) {
        loadEmailLogs(newPage);
    }
}

async function sendEmail(clientId) {
    const client = (state.clients || []).find((c) => c.id === clientId);

    if (!client) {
        alert("Client not found");
        return;
    }

    if (!client.email) {
        alert("This client has no email address");
        return;
    }

    const confirmMsg = `Send welcome email to ${client.name} at ${client.email}?`;
    if (!confirm(confirmMsg)) return;

    try {
        const r = await apiFetch(`${API_BASE}/api/send-email/${clientId}`, {
            method: "POST",
            body: JSON.stringify({ type: "welcome" }),
        });

        const data = await r.json();

        if (r.ok && data.success) {
            showToast(data.message || `Email sent successfully to ${client.email}`, "success");
        } else {
            alert(data.error || "Failed to send email. Check SMTP settings in Render environment variables.");
        }

        // Reload email logs to show the attempt
        await loadEmailLogs(1);
    } catch (e) {
        console.error(e);
        alert("Error sending email. Please check your SMTP configuration.");
        // Still reload logs to show the failure
        await loadEmailLogs(1);
    }
}

document.addEventListener("DOMContentLoaded", async () => {
    if (IS_PROFILE_PAGE) {
        return;
    }

    // Show initial loading state
    const statsGrid = document.getElementById("stats-grid");
    if (statsGrid) {
        statsGrid.style.opacity = "0.5";
    }

    try {
        await Promise.all([
            loadStats(true),
            loadInsights(true),
            loadClients(true),
            loadPayments(true),
            loadNotifications(),
            loadEmailLogs(1),
            loadExpiringClients(true),
            IS_ADMIN ? loadAdminTrainers() : Promise.resolve(),
            IS_ADMIN ? loadImpersonateDropdown() : Promise.resolve(),
            checkImpersonationStatus(),
        ]);

        // Data loaded successfully - restore opacity
        if (statsGrid) {
            statsGrid.style.opacity = "1";
        }
    } catch (error) {
        console.error("Initial data load failed:", error);
        // If initial load fails, backend might be waking up
        // The wakeup UI is already shown by apiFetch
    }

    // Auto-refresh notifications every 30 seconds
    setInterval(() => {
        loadNotifications();
    }, 30000);

    // Auto-refresh stats and insights every 60 seconds
    setInterval(() => {
        loadStats(false);
        loadInsights(false);
        loadExpiringClients(false);
    }, 60000);

    // Auto-check for due reminders in the background after 5 seconds
    setTimeout(() => {
        apiFetch(`${API_BASE}/api/reminders/send`, {
            method: "POST",
            body: JSON.stringify({ type: "due_closest" }),
        }).catch(err => console.error("Auto-reminder check failed:", err));
    }, 5000);
});
