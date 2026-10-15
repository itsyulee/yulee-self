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


function initConfigSearch() {
    const input = document.getElementById('config-search');
    if (!input) return;
    input.addEventListener('input', () => filterConfigSearch(input.value));
    input.addEventListener('keydown', (e) => {
        if (e.key === 'Escape') clearConfigSearch();
    });
}

function updateMobileControls() {
    const mobileControls = document.getElementById('mobileControls');
    if (!mobileControls) return;
    const isDashboard = document.getElementById('dash').classList.contains('active-view');
    if (isDashboard && window.innerWidth <= 768) {
        mobileControls.style.display = 'flex';
    } else {
        mobileControls.style.display = 'none';
    }
}

document.addEventListener('DOMContentLoaded', () => {
    console.log("DOM Content Loaded - Initializing...");
    initDashCharts();
    window.fetchAccounts();
    if (typeof fetchProxies === 'function') fetchProxies();
    fetchAccountConfig();
    loadConfig();
    initDynamicTilt();
    initConfigSearch();
    setInterval(window.fetchAccounts, 5000);
    setInterval(update, 1000);
    setInterval(window.pollForCaptchas, 2000);
    updateMobileControls();
    window.addEventListener('resize', updateMobileControls);
});