/* 

# This file is part of NeuraSelf-UwU.
# Copyright (c) 2025-Present Routo
#
# NeuraSelf-UwU is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# You should have received a copy of the GNU General Public License
# along with NeuraSelf-UwU. If not, see <https://www.gnu.org/licenses/>.



*/

let proxyList = [];

window.fetchProxies = async function() {
    try {
        const res = await fetch('/api/proxies');
        const data = await res.json();
        proxyList = data.proxies || [];
        renderProxyStats();
        renderProxyTable();
        populateAccountProxyDropdown();
    } catch (e) {
        console.error('Failed to fetch proxies', e);
        const el = document.getElementById('proxy-table-body');
        if (el) el.innerHTML = `<tr><td colspan="7" class="no-data error">Failed to load proxies</td></tr>`;
    }
};

function renderProxyStats() {
    const total = proxyList.length;
    const enabled = proxyList.filter(p => p.enabled !== false).length;
    const healthy = proxyList.filter(p => p.status === 'ok').length;
    const assigned = proxyList.filter(p => p.assigned_to).length;
    const free = proxyList.filter(p => p.enabled !== false && !p.assigned_to).length;

    const set = (id, val) => { const el = document.getElementById(id); if (el) el.textContent = val; };
    set('proxy-stat-total', total);
    set('proxy-stat-enabled', enabled);
    set('proxy-stat-healthy', healthy);
    set('proxy-stat-assigned', assigned);
    set('proxy-stat-free', free);
}

function statusBadge(status) {
    const cls = status === 'ok' ? 'proxy-status-ok' : (status === 'fail' ? 'proxy-status-fail' : 'proxy-status-unknown');
    const label = status === 'ok' ? 'OK' : (status === 'fail' ? 'FAIL' : 'UNKNOWN');
    return `<span class="proxy-status-badge ${cls}">${label}</span>`;
}

function renderProxyTable() {
    const body = document.getElementById('proxy-table-body');
    if (!body) return;

    if (!proxyList.length) {
        body.innerHTML = '<tr><td colspan="7" class="no-data">No proxies yet. Use bulk import or add one.</td></tr>';
        return;
    }

    body.innerHTML = proxyList.map((p, i) => `
        <tr>
            <td>${i + 1}</td>
            <td>${p.label || '-'}</td>
            <td>${p.type || 'socks5'}</td>
            <td class="mono">${p.host}:${p.port}</td>
            <td>${statusBadge(p.status || 'unknown')}</td>
            <td>${p.assigned_to || '-'}</td>
            <td class="proxy-actions">
                <button class="btn-proxy-sm" onclick="testProxy('${p.id}')">Test</button>
                <button class="btn-proxy-sm danger" onclick="deleteProxy('${p.id}')">Del</button>
            </td>
        </tr>
    `).join('');
}

window.bulkImportProxies = async function() {
    const textarea = document.getElementById('proxy-bulk-text');
    const resultEl = document.getElementById('proxy-bulk-result');
    if (!textarea) return;

    const text = textarea.value.trim();
    if (!text) {
        showToast('Paste at least one proxy line', 'info');
        return;
    }

    try {
        const res = await fetch('/api/proxies/bulk', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ text }),
        });
        const data = await res.json();
        if (resultEl) {
            let msg = `Added ${data.added} proxies.`;
            if (data.errors && data.errors.length) {
                msg += ` ${data.errors.length} line(s) skipped.`;
                const errLines = data.errors.slice(0, 5).map(e => `Line ${e.line}: ${e.error}`).join('<br>');
                resultEl.innerHTML = `<div class="proxy-bulk-ok">${msg}</div><div class="proxy-bulk-err">${errLines}</div>`;
            } else {
                resultEl.innerHTML = `<div class="proxy-bulk-ok">${msg}</div>`;
            }
        }
        textarea.value = '';
        proxyList = data.proxies || [];
        renderProxyStats();
        renderProxyTable();
        populateAccountProxyDropdown();
        showToast(`Imported ${data.added} proxies`, 'success');
    } catch (e) {
        showToast('Bulk import failed', 'error');
    }
};

window.testAllProxies = async function() {
    showToast('Testing all proxies...', 'info');
    try {
        const res = await fetch('/api/proxies/test', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: '{}' });
        const data = await res.json();
        proxyList = data.proxies || proxyList;
        renderProxyStats();
        renderProxyTable();
        const ok = (data.results || []).filter(r => r.ok).length;
        showToast(`Test complete: ${ok} OK`, 'success');
    } catch (e) {
        showToast('Proxy test failed', 'error');
    }
};

window.testProxy = async function(id) {
    try {
        const res = await fetch('/api/proxies/test', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ id }),
        });
        const data = await res.json();
        if (data.proxies) proxyList = data.proxies;
        renderProxyStats();
        renderProxyTable();
        showToast(data.ok ? 'Proxy OK' : 'Proxy failed', data.ok ? 'success' : 'error');
    } catch (e) {
        showToast('Test failed', 'error');
    }
};

window.autoAssignProxies = async function() {
    try {
        const res = await fetch('/api/proxies/assign', { method: 'POST' });
        const data = await res.json();
        proxyList = data.proxies || proxyList;
        renderProxyStats();
        renderProxyTable();
        populateAccountProxyDropdown();
        await fetchAccountConfig();
        showToast(`Assigned ${(data.assigned || []).length} proxies`, 'success');
    } catch (e) {
        showToast('Auto-assign failed', 'error');
    }
};

window.deleteProxy = async function(id) {
    if (!confirm('Remove this proxy? Accounts using it will switch to direct.')) return;
    try {
        const res = await fetch(`/api/proxies/${id}`, { method: 'DELETE' });
        const data = await res.json();
        proxyList = data.proxies || [];
        renderProxyStats();
        renderProxyTable();
        populateAccountProxyDropdown();
        await fetchAccountConfig();
        showToast('Proxy removed', 'info');
    } catch (e) {
        showToast('Delete failed', 'error');
    }
};

window.deleteAllProxies = async function() {
    if (!confirm('⚠️ Are you sure you want to delete ALL proxies? This cannot be undone.')) return;
    try {
        const res = await fetch('/api/proxies/all', { method: 'DELETE' });
        const data = await res.json();
        if (data.status === 'success') {
            proxyList = [];
            renderProxyStats();
            renderProxyTable();
            populateAccountProxyDropdown();
            await fetchAccountConfig();
            showToast('All proxies deleted', 'info');
        } else {
            showToast('Failed to delete proxies', 'error');
        }
    } catch (e) {
        showToast('Error deleting proxies', 'error');
    }
};

window.deleteFailedProxies = async function() {
    if (!confirm('Delete all proxies with status "fail"?')) return;
    try {
        const res = await fetch('/api/proxies/failed', { method: 'DELETE' });
        const data = await res.json();
        if (data.status === 'success') {
            proxyList = data.proxies || [];
            renderProxyStats();
            renderProxyTable();
            populateAccountProxyDropdown();
            await fetchAccountConfig();
            showToast(`Deleted ${data.count || 0} failed proxies`, 'info');
        } else {
            showToast('Failed to delete failed proxies', 'error');
        }
    } catch (e) {
        showToast('Error deleting failed proxies', 'error');
    }
};

window.showAddProxyModal = function() {
    const modal = document.getElementById('proxy-add-modal');
    if (modal) modal.classList.add('visible');
};

window.hideAddProxyModal = function() {
    const modal = document.getElementById('proxy-add-modal');
    if (modal) modal.classList.remove('visible');
    const input = document.getElementById('proxy-add-line');
    if (input) input.value = '';
};

window.addSingleProxy = async function() {
    const input = document.getElementById('proxy-add-line');
    if (!input || !input.value.trim()) return;

    const res = await fetch('/api/proxies/bulk', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ text: input.value.trim() }),
    });
    const data = await res.json();
    proxyList = data.proxies || proxyList;
    renderProxyStats();
    renderProxyTable();
    populateAccountProxyDropdown();
    hideAddProxyModal();
    showToast('Proxy added', 'success');
};

function populateAccountProxyDropdown() {
    const sel = document.getElementById('acct-form-proxy');
    if (!sel) return;
    const current = sel.value;
    sel.innerHTML = '<option value="">None (direct)</option>' +
        proxyList.filter(p => p.enabled !== false).map(p =>
            `<option value="${p.id}">${p.label || p.host + ':' + p.port} [${p.type || 'socks5'}]</option>`
        ).join('');
    if (current) sel.value = current;
}