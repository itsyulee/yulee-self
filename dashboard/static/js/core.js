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

let currentConfig = {};
let originalConfig = null;
let globalAnalyticsData = null;
let lineChart = null, sessChart = null, cashChart = null, pieChart = null, captchaChart = null;
let currentAccountId = null;
let accountsList = [];
let accountConfigList = [];
let activeConfigCategory = null;
let configSearchQuery = '';
let lastLogsHash = '';

const timeFormatter = new Intl.DateTimeFormat('en-US', {
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
    hour12: true
});

const CONFIG_CATEGORY_HINTS = {
    core: 'Channels, prefix, and main bot switches',
    stealth: 'Human-like delays and timing',
    security: 'Captcha handling and safety pauses',
    reactionBot: 'Auto-reactions and triggers',
    boss: 'Boss fight automation',
    level_grind: 'XP grinding behavior',
    utilities: 'Extra helper utilities',
    commands: 'Per-command automation modules'
};

const CONFIG_CMD_HINTS = {
    owo: 'OwO command scheduling',
    hunt: 'Automatic hunting',
    battle: 'Battle / PvP commands',
    curse: 'Curse command settings',
    pray: 'Pray command settings',
    cookie: 'Cookie rewards',
    daily: 'Daily claim automation',
    coinflip: 'Coinflip settings',
    slots: 'Slots settings',
    blackjack: 'Blackjack settings',
    sell_sac: 'Sell / sacrifice items',
    gems: 'Gem usage by tier',
    giveaway: 'Giveaway participation',
    huntbot: 'Huntbot integration',
    open: 'Open crates / boxes',
    quest: 'Quest tracking',
    rpp: 'RPP command',
    shop: 'Shop and ring purchases'
};


function showToast(message, type = 'success') {
    const toast = document.getElementById('neura-toast');
    const msgEl = document.getElementById('toast-message');
    if (!toast || !msgEl) return;
    msgEl.innerText = message;
    toast.className = `neura-toast show ${type}`;
    setTimeout(() => { toast.classList.remove('show'); }, 3000);
}

function checkDirty() {
    const bar = document.getElementById('floating-save-bar');
    if (!bar) return;
    const configView = document.getElementById('config');
    const isConfigActive = configView && configView.classList.contains('active-view');
    const isDirty = JSON.stringify(currentConfig) !== JSON.stringify(originalConfig);
    if (isDirty && isConfigActive) {
        bar.classList.add('visible');
    } else {
        bar.classList.remove('visible');
    }
}

window.discardChanges = function() {
    if (originalConfig) {
        currentConfig = JSON.parse(JSON.stringify(originalConfig));
        renderSettings(currentConfig);
        checkDirty();
        showToast("Changes Discarded", "info");
    }
};

function setDeep(o, p, v) {
    if (p.length === 1) o[p[0]] = v;
    else {
        if (!o[p[0]]) o[p[0]] = {};
        setDeep(o[p[0]], p.slice(1), v);
    }
}
function getDeep(o, p) {
    if (!o || p.length === 0) return o;
    return getDeep(o[p[0]], p.slice(1));
}

function formatCfgLabel(key) {
    return String(key).replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase());
}

function cfgSearchBlob(path, label, categoryName, sections) {
    return [label, path, categoryName, ...(sections || [])].join(' ').toLowerCase();
}


function initDynamicTilt() {
    const cards = document.querySelectorAll('.kpi-card');
    cards.forEach(card => {
        const icon = card.querySelector('.kpi-icon');
        if (!icon) return;
        card.addEventListener('mousemove', (e) => {
            const rect = card.getBoundingClientRect();
            const x = e.clientX - rect.left;
            const y = e.clientY - rect.top;
            const centerX = rect.width / 2;
            const centerY = rect.height / 2;
            const rotateX = -(y - centerY) / 5;
            const rotateY = (x - centerX) / 5;
            icon.style.transform = `rotateX(${rotateX}deg) rotateY(${rotateY}deg) translateZ(10px)`;
        });
        card.addEventListener('mouseleave', () => {
            icon.style.transform = `rotateX(0deg) rotateY(0deg) translateZ(0px)`;
        });
    });
}