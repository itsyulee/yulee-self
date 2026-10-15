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

window.loadHistory = async function() {
    console.log('loadHistory called');
    try {
        const startEl = document.getElementById('historyStartDate');
        const endEl = document.getElementById('historyEndDate');
        const start = startEl ? startEl.value : null;
        const end = endEl ? endEl.value : null;
        let url = '/api/history/analytics';
        const params = new URLSearchParams();
        if (start) params.append('start_date', start);
        if (end) params.append('end_date', end);
        if (params.toString()) {
            url += '?' + params.toString();
        }
        console.log("Fetching from:", url);
        const res = await fetch(url);
        console.log("Response status:", res.status);
        globalAnalyticsData = await res.json();
        console.log("Global analytics data:", globalAnalyticsData);
        
        const totals = globalAnalyticsData.totals || {};
        const sEl = document.getElementById('total-sessions');
        if (sEl) sEl.innerText = totals.total_sessions || 0;
        const hEl = document.getElementById('total-hunts');
        if (hEl) hEl.innerText = (totals.all_time_hunts || 0).toLocaleString();
        const bEl = document.getElementById('total-battles');
        if (bEl) bEl.innerText = (totals.all_time_battles || 0).toLocaleString();
        const cEl = document.getElementById('total-cmds');
        if (cEl) cEl.innerText = (totals.all_time_commands || 0).toLocaleString();
        const capSolvedEl = document.getElementById('totalCaptchasSolved');
        if (capSolvedEl) capSolvedEl.innerText = (totals.all_time_captchas || 0).toLocaleString();
        
        window.populateSessionDropdown();

        setTimeout(() => {
            console.log('Forced renderCharts after delay');
            renderCharts();
        }, 100);
    } catch (e) {
        console.error("History Error:", e);
    }
};

window.populateSessionDropdown = function() {
    const dropdown = document.getElementById('session-select');
    if (!dropdown || !globalAnalyticsData || !globalAnalyticsData.sessions) {
        dropdown.innerHTML = '<option value="all">ALL SESSIONS IN RANGE</option>';
        return;
    }
    const currentVal = dropdown.value;
    let html = '<option value="all">ALL SESSIONS IN RANGE</option>';
    globalAnalyticsData.sessions.forEach(s => {
        const d = s.start_time ? new Date(s.start_time * 1000).toLocaleString() : `Session ${s.id}`;
        html += `<option value="${s.id}">Session ${s.id} — ${d}</option>`;
    });
    dropdown.innerHTML = html;
    if (currentVal && dropdown.querySelector(`option[value="${currentVal}"]`)) {
        dropdown.value = currentVal;
    }
};

function getFilteredSessions() {
    console.log('getFilteredSessions called');
    if (!globalAnalyticsData || !globalAnalyticsData.sessions) return [];
    const dropdown = document.getElementById('session-select');
    const selected = dropdown ? dropdown.value : 'all';
    if (selected === 'all') return globalAnalyticsData.sessions;
    return globalAnalyticsData.sessions.filter(s => String(s.id) === String(selected));
}

function showChartEmpty(canvasId, message) {
    const el = document.getElementById(canvasId);
    if (!el) return;
    const parent = el.parentElement;
    el.style.display = 'none';
    let placeholder = parent.querySelector('.chart-empty-msg');
    if (!placeholder) {
        placeholder = document.createElement('div');
        placeholder.className = 'chart-empty-msg';
        placeholder.style.cssText = 'display:flex;align-items:center;justify-content:center;height:100%;color:#555;font-size:0.9rem;font-family:var(--font-mono);';
        parent.appendChild(placeholder);
    }
    placeholder.textContent = message;
    placeholder.style.display = 'flex';
}

function clearChartEmpty(canvasId) {
    const el = document.getElementById(canvasId);
    if (!el) return;
    el.style.display = '';
    const parent = el.parentElement;
    const placeholder = parent.querySelector('.chart-empty-msg');
    if (placeholder) placeholder.style.display = 'none';
}


window.renderCharts = function renderCharts() {
    console.log('renderCharts called');
    console.log('globalAnalyticsData:', globalAnalyticsData);
    
    if (!globalAnalyticsData) {
        console.warn('No globalAnalyticsData');
        return;
    }
    
    const sessions = getFilteredSessions();
    console.log('sessions count:', sessions.length);
    if (sessions.length > 0) {
        console.log('first session:', sessions[0]);
    }
    
    const sessionCanvas = document.getElementById('sessionChart');
    const pieCanvas = document.getElementById('pieChart');
    const cashCanvas = document.getElementById('cashHistoryChart');
    
    console.log('sessionChart element:', sessionCanvas);
    console.log('pieChart element:', pieCanvas);
    console.log('cashHistoryChart element:', cashCanvas);
    
    console.log('Chart available:', typeof Chart !== 'undefined' ? 'Yes' : 'No');

    const sessEl = sessionCanvas;
    if (sessEl) {
        if (!sessions || sessions.length === 0) {
            showChartEmpty('sessionChart', '— No session data in range —');
            if (sessChart) { sessChart.destroy(); sessChart = null; }
            console.log(' No sessions data, showing empty state');
        } else {
            clearChartEmpty('sessionChart');
            const sctx = sessEl.getContext('2d');
            if (sessChart) sessChart.destroy();
            const revSessions = [...sessions].reverse();
            try {
                sessChart = new Chart(sctx, {
                    type: 'bar',
                    data: {
                        labels: revSessions.map(s => {
                            if (s.start_time) {
                                const dt = new Date(s.start_time * 1000);
                                return `S${s.id} (${dt.toLocaleDateString()})`;
                            }
                            return `S${s.id}`;
                        }),
                        datasets: [
                            { label: 'Hunts', data: revSessions.map(s => s.stats?.hunts || 0), backgroundColor: '#ff1f1f', borderRadius: 4 },
                            { label: 'Battles', data: revSessions.map(s => s.stats?.battles || 0), backgroundColor: '#3b82f6', borderRadius: 4 },
                            { label: 'Captchas', data: revSessions.map(s => s.stats?.captchas || 0), backgroundColor: '#00d16e', borderRadius: 4 }
                        ]
                    },
                    options: {
                        responsive: true,
                        maintainAspectRatio: false,
                        scales: {
                            x: { grid: { display: false }, ticks: { color: '#888' } },
                            y: { grid: { color: 'rgba(255,255,255,0.05)' }, ticks: { color: '#888' } }
                        },
                        plugins: { legend: { labels: { color: '#ccc' } } }
                    }
                });
                console.log(' Session chart created successfully');
            } catch (e) {
                console.error(' Error creating session chart:', e);
            }
        }
    } else {
        console.warn('sessionChart canvas not found');
    }

    const cashEl = cashCanvas;
    if (cashEl) {
        const cashData = globalAnalyticsData.cash_history || [];
        console.log(' cashData length:', cashData.length);
        if (!cashData || cashData.length === 0) {
            showChartEmpty('cashHistoryChart', '— No cash history recorded —');
            if (cashChart) { cashChart.destroy(); cashChart = null; }
            console.log(' No cash data, showing empty state');
        } else {
            clearChartEmpty('cashHistoryChart');
            const cctx = cashEl.getContext('2d');
            if (cashChart) cashChart.destroy();
            try {
                cashChart = new Chart(cctx, {
                    type: 'line',
                    data: {
                        labels: cashData.map(c => c.timestamp ? c.timestamp.split(' ')[1] || c.timestamp : ''),
                        datasets: [{
                            label: 'Cash Flow',
                            data: cashData.map(c => c.amount),
                            borderColor: '#ffd700',
                            backgroundColor: 'rgba(255, 215, 0, 0.1)',
                            fill: true,
                            tension: 0.4,
                            pointRadius: cashData.length > 30 ? 0 : 3
                        }]
                    },
                    options: {
                        responsive: true,
                        maintainAspectRatio: false,
                        plugins: { legend: { display: false } },
                        scales: {
                            x: { display: cashData.length <= 30, ticks: { color: '#888', maxRotation: 0 } },
                            y: { grid: { color: 'rgba(255,255,255,0.05)' }, ticks: { color: '#888' } }
                        }
                    }
                });
                console.log(' Cash chart created successfully');
            } catch (e) {
                console.error(' Error creating cash chart:', e);
            }
        }
    } else {
        console.warn(' cashHistoryChart canvas not found');
    }


    const pieEl = pieCanvas;
    if (pieEl) {
        let totalHunts = 0, totalBattles = 0, totalCaptchas = 0, totalOther = 0;
        sessions.forEach(s => {
            totalHunts += s.stats?.hunts || 0;
            totalBattles += s.stats?.battles || 0;
            totalCaptchas += s.stats?.captchas || 0;
            totalOther += Math.max(0, (s.stats?.commands || 0) - (s.stats?.hunts || 0) - (s.stats?.battles || 0) - (s.stats?.captchas || 0));
        });
        const total = totalHunts + totalBattles + totalCaptchas + totalOther;
        console.log(' Pie chart totals:', { totalHunts, totalBattles, totalCaptchas, totalOther, total });
        
        if (total === 0) {
            showChartEmpty('pieChart', '— No activity data —');
            if (pieChart) { pieChart.destroy(); pieChart = null; }
            console.log(' No activity data, showing empty state');
        } else {
            clearChartEmpty('pieChart');
            const pctx = pieEl.getContext('2d');
            if (pieChart) pieChart.destroy();
            try {
                pieChart = new Chart(pctx, {
                    type: 'doughnut',
                    data: {
                        labels: ['Hunts', 'Battles', 'Captchas', 'Other'],
                        datasets: [{
                            data: [totalHunts, totalBattles, totalCaptchas, totalOther],
                            backgroundColor: ['#ff1f1f', '#3b82f6', '#00d16e', '#888'],
                            borderWidth: 0
                        }]
                    },
                    options: {
                        responsive: true,
                        maintainAspectRatio: false,
                        cutout: '70%',
                        plugins: { legend: { position: 'right', labels: { color: '#ccc' } } }
                    }
                });
                console.log(' Pie chart created successfully');
            } catch (e) {
                console.error(' Error creating pie chart:', e);
            }
        }
    } else {
        console.warn('pieChart canvas not found');
    }
};