/* 

# This file is part of YuleeSelf-UwU.
# Copyright (c) 2025-Present Routo
#
# YuleeSelf-UwU is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# You should have received a copy of the GNU General Public License
# along with YuleeSelf-UwU. If not, see <https://www.gnu.org/licenses/>.



*/
window.nav = function(id, el) {
    // Verify the page and the visible menu item before switching.
    const target = document.getElementById(id);
    const item = document.querySelector('.nav-item[data-view="' + id + '"]') ||
        (el && el.classList && el.classList.contains('nav-item') ? el : null);
    if (!target || !item) return;

    document.querySelectorAll('.view').forEach(v => v.classList.remove('active-view'));
    document.querySelectorAll('.nav-item').forEach(n => n.classList.remove('active'));
    target.classList.add('active-view');
    item.classList.add('active');
    if (id === 'logs') {
        requestAnimationFrame(() => {
            const terminal = document.getElementById('term');
            if (terminal) terminal.scrollTop = terminal.scrollHeight;
        });
    }
    try { sessionStorage.setItem('yulee:active-view', id); } catch (_) {}

    if (typeof checkDirty === 'function') checkDirty();
    const mobileControls = document.getElementById('mobileControls');
    if (mobileControls) mobileControls.style.display = id === 'dash' && window.innerWidth <= 768 ? 'flex' : 'none';
    const mobileTopControls = document.querySelector('.mobile-top-controls');
    if (mobileTopControls) mobileTopControls.style.display = id === 'dash' ? 'flex' : 'none';
    document.body.classList.toggle('active-dash-header', id === 'dash');
    if (window.innerWidth <= 768) {
        const sidebar = document.querySelector('.sidebar');
        if (sidebar && sidebar.classList.contains('active')) toggleMobileMenu();
    }
    if (id === 'accounts') {
        renderAccountGrid();
        fetchAccountConfig();
        if (typeof fetchProxies === 'function') fetchProxies();
    }
    if (id === 'settings') {
        let tab = 'profile';
        try { tab = sessionStorage.getItem('yulee:settings-tab') || 'profile'; } catch (_) {}
        showSettingsTab(tab);
    }
    if (id === 'users' && typeof loadUsers === 'function') loadUsers();
    if (id === 'config') loadConfig();
    if (id === 'history') loadHistory();
    if (id === 'security') {
        fetchSecuritySummary();
        pollForCaptchas();
    }
};

window.showSettingsTab = function(tab) {
    const allowed = ['profile', 'proxies'];
    if (!allowed.includes(tab)) tab = 'profile';
    document.querySelectorAll('#settings .settings-panel').forEach(panel => {
        panel.classList.toggle('active-settings-panel', panel.id === tab);
    });
    document.querySelectorAll('#settings .settings-tab').forEach(button => {
        const active = button.dataset.settingsTab === tab;
        button.classList.toggle('active', active);
        button.setAttribute('aria-selected', String(active));
    });
    try { sessionStorage.setItem('yulee:settings-tab', tab); } catch (_) {}
    if (tab === 'proxies' && typeof fetchProxies === 'function') fetchProxies();
};
window.toggleMobileMenu = function() {
    const s = document.querySelector('.sidebar'), o = document.querySelector('.sidebar-overlay'), t = document.querySelector('.mobile-menu-toggle');
    if (!s || !o || !t) return;
    s.classList.toggle('active'); o.classList.toggle('active'); t.classList.toggle('active');
    document.body.style.overflow = s.classList.contains('active') ? 'hidden' : '';
};
