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

function initDashCharts() {
    try {
        const c2 = document.getElementById('lineChart').getContext('2d');
        lineChart = new Chart(c2, {
            type: 'line',
            data: { labels: Array(30).fill(''), datasets: [{ data: Array(30).fill(0), borderColor: '#ff1f1f', backgroundColor: 'rgba(255,31,31,0.05)', fill: true, pointRadius: 2, pointHoverRadius: 5, tension: 0.3 }] },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                scales: { x: { display: false }, y: { min: 0, suggestedMax: 10, grid: { color: '#222' }, ticks: { color: '#555', font: { size: 10 } } } },
                plugins: { legend: { display: false } }
            }
        });
    } catch (e) { console.warn("Dashboard charts blocked"); }
}

    
function update() {
    const q = currentAccountId ? `?id=${currentAccountId}` : '';
    fetch(`/api/stats${q}`).then(r => r.json()).then(d => {
        console.log('Logs received:', d.logs);
        if (!d || Object.keys(d).length === 0) return;
        if (d.bot) {
            console.log(`[Stats Update] ${d.bot.username} (#${d.bot.user_id}): ${Object.keys(d.cmd_states || {}).length} commands in scheduler.`);
            const nameEl = document.getElementById('currentAccountName');
            if (nameEl) nameEl.innerText = `ACCOUNT: ${d.bot.username}`;
        }
        if (d.cash) document.getElementById('cash').innerText = d.cash.toLocaleString();
        if (d.uptime) document.getElementById('uptimeDisplay').innerText = d.uptime;
        if (d.logs) renderLogs(d.logs);
        const dot = document.getElementById('statusDot'), lbl = document.getElementById('botStatus');
        lbl.innerText = d.status; dot.className = "ping-dot " + (d.status === "PAUSED" ? "paused" : "");
        if (d.status === "PAUSED" && d.security && d.security.last_message) {
            document.getElementById('securityAlert').style.display = 'flex';
            document.getElementById('captchaMsg').innerText = d.security.last_message;

            const section = document.getElementById('captcha-solver-section');
            if (section && section.style.display !== 'block') {
                const acc = accountsList.find(a => a.id === currentAccountId);
                if (acc) openEmbeddedCaptcha(currentAccountId, acc.username);
            }
        } else {
            document.getElementById('securityAlert').style.display = 'none';
        }
        if (d.chart_data) {
            document.getElementById('huntsToday').innerHTML = `${d.chart_data.hunt} <span style="font-size:0.5em; color:var(--success);" id="huntsSession">(${d.chart_data.session_hunt} this session)</span>`;
            document.getElementById('battlesToday').innerHTML = `${d.chart_data.battle} <span style="font-size:0.5em; color:#3b82f6;" id="battlesSession">(${d.chart_data.session_battle} this session)</span>`;
            document.getElementById('cpm').innerText = d.chart_data.perf_bpm;
            if (document.getElementById('totalOwO')) document.getElementById('totalOwO').innerHTML = `${d.chart_data.owo} <span style="font-size:0.5em; color:#a855f7;" id="owoSession">(${d.chart_data.session_owo} this session)</span>`;
        }
        if (d.security) {
            const sc = document.getElementById('sec-captchas'); if (sc) sc.innerText = d.security.captchas;
            const sb = document.getElementById('sec-bans'); if (sb) sb.innerText = d.security.bans;
            const sw = document.getElementById('sec-warns'); if (sw) sw.innerText = d.security.warnings;
        }
        if (lineChart && d.chart_data) {
            lineChart.data.datasets[0].data.push(d.chart_data.perf_bpm);
            lineChart.data.datasets[0].data.shift();
            lineChart.update('none');
        }
        try { renderQuests(d.quest_data, d.next_quest_timer); } catch(e) { console.error("Quest Render Error:", e); }
        try { if (d.cmd_states) renderScheduler(d.cmd_states); } catch(e) { console.error("Scheduler Render Error in update():", e); }
        try { fetchSecuritySummary(); } catch(e) { console.error("Security Summary Error:", e); }
    });
}


function renderScheduler(states) {
    const list = document.getElementById('schedulerList');
    if (!list) return;
    try {
        const now = Date.now() / 1000;
        const items = Object.entries(states || {}).map(([id, s]) => {
            try {
                const lastRan = s.last_ran || 0;
                const delay = s.delay || 1;
                const nextRun = lastRan + delay;
                const remaining = Math.max(0, nextRun - now);
                return { id, priority: s.priority || 3, delay: delay, in_queue: !!s.in_queue, remaining };
            } catch(e) {
                return null;
            }
        }).filter(item => item !== null);
        items.sort((a, b) => (a.remaining || 0) - (b.remaining || 0));
        if (items.length === 0) {
            list.innerHTML = '<div style="color:#666; font-style:italic; font-size:0.9rem; text-align:center; padding-top:20px;">No scheduled actions</div>';
            return;
        }
        list.innerHTML = items.map(item => {
            const name = item.id.toUpperCase();
            let statusHtml = '';
            let progress = 0;
            if (item.in_queue) {
                statusHtml = `<span style="color:var(--success); font-size:0.8rem; font-weight:bold;"><span class="icon-svg" style="--icon: url('/static/assets/neura_icons/sync.svg'); animation: spin 2s linear infinite;"></span> QUEUED</span>`;
                progress = 100;
            } else {
                const displayTime = Math.ceil(item.remaining);
                const timeStr = displayTime > 60 ? `${Math.floor(displayTime / 60)}m ${displayTime % 60}s` : `${displayTime}s`;
                statusHtml = `<span style="color:#aaa; font-family:var(--font-mono); font-size:0.8rem;">in ${timeStr}</span>`;
                progress = Math.min(100, Math.max(0, 100 - (item.remaining / item.delay) * 100));
            }
            const pColor = item.priority <= 2 ? 'var(--primary)' : '#888';
            return `
                <div style="background:rgba(0,0,0,0.2); border:1px solid rgba(255,255,255,0.05); border-radius:6px; padding:8px 12px; display:flex; flex-direction:column; gap:6px;">
                    <div style="display:flex; justify-content:space-between; align-items:center;">
                        <div style="display:flex; align-items:center; gap:8px;">
                            <span style="width:8px; height:8px; border-radius:50%; background:${pColor}; display:inline-block; box-shadow:0 0 5px ${pColor};"></span>
                            <span style="color:#ddd; font-weight:600; font-size:0.85rem;">${name}</span>
                        </div>
                        ${statusHtml}
                    </div>
                    <div style="height:3px; background:rgba(255,255,255,0.05); border-radius:2px; overflow:hidden;">
                        <div style="height:100%; width:${progress}%; background:${item.in_queue ? 'var(--success)' : '#444'}; transition:width 1s linear;"></div>
                    </div>
                </div>
            `;
        }).join('');
    } catch (e) {
        console.error("Scheduler Render Error:", e);
        list.innerHTML = '<div style="color:#666; font-style:italic; font-size:0.9rem; text-align:center; padding-top:20px;">Render Error (Check Console)</div>';
    }
}

function renderQuests(quests, timer) {
    const list = document.getElementById('questList');
    const timerEl = document.getElementById('nextQuestTimer');
    if (!list || !timerEl) return;
    if (timer) {
        timerEl.innerHTML = `<span class="icon-svg" style="--icon: url('/static/assets/neura_icons/clock.svg'); width: 14px; height: 14px;"></span> Next quest in: ${timer}`;
        timerEl.style.display = 'block';
    } else {
        timerEl.style.display = 'none';
    }
    if (!quests || quests.length === 0) {
        list.innerHTML = '<div style="color:#666; font-style:italic; text-align:center; padding: 20px;">No active quests tracked.<br><span style="font-size:0.8rem; opacity:0.7;">Run "o quest" to sync with OwO.</span></div>';
        return;
    }
    list.innerHTML = quests.map(q => {
        const percent = Math.min(100, Math.round((q.current / q.total) * 100));
        const isCompleted = q.completed;
        const color = isCompleted ? 'var(--success)' : 'var(--primary)';
        let status = "Auto-solving";
        if (isCompleted) status = "Completed";
        else {
            const desc = q.description.toLowerCase();
            const socialQuests = ["friend", "pray to you", "curse you", "cookie from", "action command on you", "emote command on you"];
            if (socialQuests.some(s => desc.includes(s))) {
                status = "Alt Coordinated";
            } else if (desc.includes("hunt 3 animals")) {
                status = "Gem Optimized";
            } else if (desc.includes("gamble")) {
                status = "Auto Gambling";
            }
        }
        return `
            <div style="background:rgba(255,255,255,0.03); border:1px solid rgba(255,255,255,0.05); padding:15px; border-radius:8px;">
                <div style="display:flex; justify-content:space-between; margin-bottom:5px; font-size:0.9rem;">
                    <span style="color:#eee; font-weight:500;">${q.description}</span>
                    <span style="color:${color}; font-weight:bold;">${q.current}/${q.total}</span>
                </div>
                <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:10px;">
                    <span style="font-size:0.65rem; color:${isCompleted ? 'var(--success)' : '#888'}; text-transform:uppercase; letter-spacing:0.8px; font-family:var(--font-mono);">${status}</span>
                </div>
                <div style="height:6px; background:rgba(255,255,255,0.05); border-radius:3px; overflow:hidden;">
                    <div style="width:${percent}%; height:100%; background:${color}; box-shadow: 0 0 10px ${color}44; transition: width 0.5s ease;"></div>
                </div>
            </div>
        `;
    }).join('');
}

function renderLogs(logs) {
    const t = document.getElementById('term');
    if (!t) return;
    const currentHash = logs.slice(0, 5).map(l => l.timestamp).join('|');
    if (currentHash === lastLogsHash) return;
    lastLogsHash = currentHash;
    t.innerHTML = logs.map(l => {
        const tagClass = l.type ? `tag-${l.type.toLowerCase()}` : '';
        const localTime = l.timestamp ? timeFormatter.format(new Date(l.timestamp * 1000)) : l.time;
        const botTag = l.bot_name ? `<span style="color:magenta; margin-right:5px;">[${l.bot_name}]</span>` : '';
        return `<div class="history-item ${l.type ? l.type.toLowerCase() : ''}">${botTag}<span class="history-time">[${localTime}]</span> <span class="history-tag ${tagClass}">${l.type}</span> <span class="history-msg">${l.message}</span></div>`;
    }).join('');
}


window.resumeBot = function() { 
    console.log("Resuming bot...");
    fetch('/api/security', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ action: 'resume', id: currentAccountId })
    }).then(() => {
        document.getElementById('securityAlert').style.display = 'none';
        update();
    });
};

window.action = function(a, el) {
    console.log(`Executing action: ${a}`);
    fetch('/api/control', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ action: a, id: currentAccountId })
    }).then(() => update());
};