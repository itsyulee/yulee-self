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


async function loadConfig() {
    const questCfg = currentConfig?.commands?.quest || {};
    if (questCfg.use_alt_account && accountsList.length <= 1) {
        showToast('Alt Account feature requires multiple accounts. Currently only one account is connected.', 'info');
    }
    const q = currentAccountId ? `?id=${currentAccountId}` : '';
    const r = await fetch(`/api/settings${q}`);
    currentConfig = await r.json();
    originalConfig = JSON.parse(JSON.stringify(currentConfig));
    renderSettings(currentConfig);
    checkDirty();
}

function buildConfigCategories(cfg) {
    const cats = [];
    Object.keys(cfg).forEach(key => {
        if (key === 'commands' && cfg[key] && typeof cfg[key] === 'object') {
            Object.keys(cfg[key]).forEach(cmd => {
                cats.push({
                    id: `cmd-${cmd}`,
                    name: formatCfgLabel(cmd),
                    hint: CONFIG_CMD_HINTS[cmd] || `${formatCfgLabel(cmd)} command options`,
                    path: `commands.${cmd}`,
                    data: cfg[key][cmd]
                });
            });
        } else if (typeof cfg[key] === 'object' && !Array.isArray(cfg[key])) {
            cats.push({
                id: `cat-${key}`,
                name: formatCfgLabel(key),
                hint: CONFIG_CATEGORY_HINTS[key] || `${formatCfgLabel(key)} settings`,
                path: key,
                data: cfg[key]
            });
        }
    });
    return cats;
}

function renderSettings(cfg) {
    const cats = buildConfigCategories(cfg);
    if (!cats.length) {
        document.getElementById('settings-grid').innerHTML = '<div class="cfg-empty">No settings loaded.</div>';
        return;
    }
    if (!activeConfigCategory || !cats.find(c => c.id === activeConfigCategory)) {
        activeConfigCategory = cats.find(c => c.id === 'cat-core')?.id || cats[0].id;
    }
    renderConfigNav(cats);
    if (configSearchQuery) {
        renderConfigSearchResults(cfg, configSearchQuery);
    } else {
        renderConfigPanel(cfg);
    }
}

function renderConfigNav(cats) {
    const nav = document.getElementById('config-nav-list');
    if (!nav) return;
    nav.innerHTML = cats.map(cat => `
        <button type="button" class="cfg-nav-item ${cat.id === activeConfigCategory && !configSearchQuery ? 'active' : ''}"
            data-category-id="${cat.id}" onclick="selectConfigCategory('${cat.id}')">
            ${cat.name}
            <span class="cfg-nav-hint">${cat.hint}</span>
        </button>
    `).join('');
}

function selectConfigCategory(categoryId) {
    configSearchQuery = '';
    const input = document.getElementById('config-search');
    const clearBtn = document.getElementById('config-search-clear');
    if (input) input.value = '';
    if (clearBtn) clearBtn.hidden = true;
    activeConfigCategory = categoryId;
    renderSettings(currentConfig);
}

window.clearConfigSearch = function () {
    configSearchQuery = '';
    const input = document.getElementById('config-search');
    const clearBtn = document.getElementById('config-search-clear');
    if (input) input.value = '';
    if (clearBtn) clearBtn.hidden = true;
    renderSettings(currentConfig);
};

window.filterConfigSearch = function (query) {
    configSearchQuery = (query || '').trim().toLowerCase();
    const clearBtn = document.getElementById('config-search-clear');
    if (clearBtn) clearBtn.hidden = !configSearchQuery;
    document.querySelectorAll('.cfg-nav-item').forEach(el => {
        el.classList.toggle('active', !configSearchQuery && el.dataset.categoryId === activeConfigCategory);
    });
    if (!currentConfig || !Object.keys(currentConfig).length) return;
    if (configSearchQuery) {
        renderConfigSearchResults(currentConfig, configSearchQuery);
    } else {
        renderConfigPanel(currentConfig);
    }
};

function renderConfigPanel(cfg) {
    const grid = document.getElementById('settings-grid');
    const titles = document.getElementById('config-panel-titles');
    const cats = buildConfigCategories(cfg);
    const cat = cats.find(c => c.id === activeConfigCategory) || cats[0];
    if (!cat) return;
    if (titles) {
        titles.innerHTML = `<h2>${cat.name}</h2><p>${cat.hint}</p>`;
    }
    const panelOn = cat.data?.enabled !== false;
    grid.innerHTML = `<div class="cfg-panel-body ${panelOn ? '' : 'cfg-panel-disabled'}">${renderCategoryFlat(cat.data, cat.path, cat.name, 0, true)}</div>`;
    applyDisabledPanelState(grid);
}


function categoryMatchesSearch(cat, query) {
    const q = query.toLowerCase();
    if (cat.name.toLowerCase().includes(q)) return true;
    if (cat.hint.toLowerCase().includes(q)) return true;
    if (cat.path.toLowerCase().includes(q)) return true;
    const hits = [];
    collectConfigMatches(cat.data, cat.path, cat.name, [], q, hits);
    return hits.length > 0;
}

function searchMatchScore(cat, query) {
    const q = query.toLowerCase();
    const name = cat.name.toLowerCase();
    if (name === q) return 0;
    if (name.startsWith(q)) return 1;
    if (name.includes(q)) return 2;
    if (cat.path.toLowerCase().includes(q)) return 3;
    return 4;
}

function renderConfigSearchResults(cfg, query) {
    const grid = document.getElementById('settings-grid');
    const cats = buildConfigCategories(cfg);
    const matching = cats.filter(cat => categoryMatchesSearch(cat, query));
    matching.sort((a, b) => searchMatchScore(a, query) - searchMatchScore(b, query));
    const titles = document.getElementById('config-panel-titles');
    if (titles) {
        titles.innerHTML = `
            <h2>Search results</h2>
            <p>Full panels matching "${query.replace(/</g, '')}"</p>
        `;
    }
    if (!matching.length) {
        grid.innerHTML = `<div class="cfg-empty">No settings match <mark>${query}</mark>. Try <mark>gem</mark>, <mark>hunt</mark>, or <mark>giveaway</mark>.</div>`;
        return;
    }
    let html = '';
    matching.forEach(cat => {
        const panelOn = cat.data?.enabled !== false;
        html += `
            <div class="cfg-search-group">
                <div class="cfg-search-group-title">${cat.name}</div>
                <p class="cfg-search-group-hint">${cat.hint}</p>
                <div class="cfg-panel-body ${panelOn ? '' : 'cfg-panel-disabled'}">
                    ${renderCategoryFlat(cat.data, cat.path, cat.name, 0, true)}
                </div>
            </div>
        `;
    });
    grid.innerHTML = html;
    applyDisabledPanelState(grid);
}

function applyDisabledPanelState(root) {
    if (!root) return;
    root.querySelectorAll('.cfg-panel-disabled, .cfg-section-disabled').forEach(block => {
        block.querySelectorAll('input, button').forEach(el => { el.disabled = true; });
        block.querySelectorAll('.neura-toggle:not([data-master-toggle])').forEach(el => {
            el.style.pointerEvents = 'none';
        });
    });
}


function renderCategoryFlat(obj, path, categoryName, depth = 0, parentEnabled = true) {
    let h = '';
    let keys = Object.keys(obj);
    const isTiers = path.includes('tiers');
    const isTypes = path.includes('types');
    if (isTiers) {
        const tierOrder = ['common', 'uncommon', 'rare', 'epic', 'mythical', 'legendary', 'fabled'];
        keys.sort((a, b) => tierOrder.indexOf(a) - tierOrder.indexOf(b));
    }
    if (isTiers || isTypes) {
        h += `<div class="cfg-tier-grid gem-tier-group${isTypes ? ' types-grid' : ''}">`;
        keys.forEach(key => {
            if (typeof obj[key] === 'boolean') {
                h += renderTierChip(`${path}.${key}`, key, obj[key], parentEnabled);
            }
        });
        h += '</div>';
        return h;
    }
    const selfEnabled = parentEnabled && (obj.enabled !== false || !('enabled' in obj));
    keys.forEach(key => {
        const val = obj[key];
        const fullPath = `${path}.${key}`;
        const isMasterToggle = key === 'enabled' && typeof val === 'boolean';
        if (fullPath === 'commands.shop.itemsToBuy') {
            h += renderRingSelection(fullPath, val, selfEnabled);
        } else if (path === 'security.captcha_solver' && key !== 'enabled') {
        } else if (path === 'security' && key === 'captcha_solver') {
            const solverEnabled = val.enabled !== false;
            h += `
                <div class="cfg-section cfg-section-nested ${solverEnabled ? '' : 'cfg-section-disabled'}" id="captcha-solver-section">
                    <div class="cfg-section-head">Captcha Solver</div>
                    <div class="cfg-section-rows">${renderCaptchaSolverWidget(val, fullPath, selfEnabled)}</div>
                </div>
            `;
        } else if (typeof val === 'boolean') {
            h += renderField(fullPath, { l: key, type: 'toggle', master: isMasterToggle }, val, false, isMasterToggle ? parentEnabled : selfEnabled);
        } else if (Array.isArray(val) && val.length === 2 && typeof val[0] === 'number') {
            h += renderField(fullPath, { l: key, type: 'range' }, val, false, selfEnabled);
        } else if (typeof val === 'object' && val !== null && !Array.isArray(val)) {
            const nested = depth > 0;
            const sectionOn = selfEnabled && (val.enabled !== false || !('enabled' in val));
            h += `
                <div class="cfg-section ${nested ? 'cfg-section-nested' : ''} ${sectionOn ? '' : 'cfg-section-disabled'}">
                    <div class="cfg-section-head">${formatCfgLabel(key)}</div>
                    <div class="cfg-section-rows">${renderCategoryFlat(val, fullPath, categoryName, depth + 1, selfEnabled)}</div>
                </div>
            `;
        } else if (isSelectField(fullPath)) {
            h += renderSelectDropdown(fullPath, val, selfEnabled);
        } else {
            h += renderField(fullPath, { l: key, type: key.includes('url') ? 'password' : 'text' }, val, false, selfEnabled);
        }
    });
    return h;
}


function isListField(path) {
    const name = path.split('.').pop();
    return ['channels', 'targets', 'active_commands', 'ignore_guilds'].includes(name);
}

function isSelectField(path) {
    const name = path.split('.').pop();
    return ['bet_strategy', 'speed_preset'].includes(name);
}

function getSelectOptions(path, val) {
    if (path.endsWith('bet_strategy')) {
        return [
            { value: 'flat', label: 'Flat (Fixed bet amount)' },
            { value: 'martingale', label: 'Martingale (Double after loss)' }
        ];
    }
    if (path.endsWith('speed_preset')) {
        return [
            { value: 'fast', label: 'Fast (Quick typing)' },
            { value: 'medium', label: 'Medium (Balanced)' },
            { value: 'slow', label: 'Slow (Human-like)' }
        ];
    }
    return [];
}

function renderSelectDropdown(path, v, parentEnabled = true) {
    const options = getSelectOptions(path, v);
    const dis = parentEnabled ? '' : ' disabled';
    const label = formatCfgLabel(path.split('.').pop());
    let optsHtml = options.map(opt => 
        `<option value="${opt.value}" ${opt.value === v ? 'selected' : ''}>${opt.label}</option>`
    ).join('');
    return `
        <div class="cfg-row" data-search="gambling strategy ${path}" data-path="${path}">
            <div class="cfg-row-label">
                <span class="cfg-label-text">${label}</span>
            </div>
            <div class="cfg-row-control">
                <div class="cfg-select-wrap">
                    <select class="cfg-input cfg-select" ${dis} onchange="updateDeepVal('${path}', this.value)">
                        ${optsHtml}
                    </select>
                    <span class="cfg-select-arrow">&#9660;</span>
                </div>
            </div>
        </div>
    `;
}

function renderTierChip(path, tierName, val, parentEnabled = true) {
    const tierClass = tierName === 'mythical' ? 'mythical' : tierName;
    const off = !parentEnabled ? ' cfg-tier-locked' : '';
    return `
        <div class="gem-tier-item ${tierClass} ${val ? 'selected' : ''}${off}" ${parentEnabled ? `onclick="toggleMod('${path}', this, event)"` : ''}
            role="button" aria-pressed="${val}" title="${val ? 'Selected — click to turn off' : 'Click to turn on'}">
            <span class="gem-label">${formatCfgLabel(tierName)}</span>
        </div>
    `;
}

function renderListInput(path, v, parentEnabled = true) {
    const items = Array.isArray(v) ? [...v] : (v && String(v).trim() ? String(v).split(',').map(s => s.trim()).filter(Boolean) : []);
    const tags = items.map((item, i) => `
        <span class="cfg-tag">
            <span class="cfg-tag-text">${item}</span>
            <button type="button" class="cfg-tag-remove" onclick="removeListItem('${path}', ${i}, event)" aria-label="Remove">×</button>
        </span>
    `).join('');
    const dis = parentEnabled ? '' : ' disabled';
    return `
        <div class="cfg-list-input" data-path="${path}">
            <div class="cfg-tags">${tags || '<span class="cfg-tags-empty">No items added</span>'}</div>
            <div class="cfg-list-add">
                <div class="cfg-input-wrap cfg-input-wrap-sm">
                    <input type="text" class="cfg-input" placeholder="Add ID, press Enter" data-list-input="${path}"${dis}
                        onkeydown="if(event.key==='Enter'){addListItem('${path}', this, event);}">
                </div>
                <button type="button" class="cfg-add-btn" ${parentEnabled ? `onclick="addListItem('${path}', this.previousElementSibling.querySelector('input'), event)"` : 'disabled'}>Add</button>
            </div>
        </div>
    `;
}

window.addListItem = function (path, inputEl, ev) {
    if (ev) ev.preventDefault();
    const val = (inputEl.value || '').trim();
    if (!val) return;
    const keyPath = path.split('.');
    let list = getDeep(currentConfig, keyPath);
    if (!Array.isArray(list)) list = list ? String(list).split(',').map(s => s.trim()).filter(Boolean) : [];
    if (!list.includes(val)) list.push(val);
    setDeep(currentConfig, keyPath, list);
    inputEl.value = '';
    renderSettings(currentConfig);
    checkDirty();
};

window.removeListItem = function (path, index, ev) {
    if (ev) ev.stopPropagation();
    const keyPath = path.split('.');
    const list = getDeep(currentConfig, keyPath);
    if (!Array.isArray(list)) return;
    list.splice(index, 1);
    setDeep(currentConfig, keyPath, list);
    renderSettings(currentConfig);
    checkDirty();
};

function renderNeuraToggle(path, v, parentEnabled = true, isMaster = false) {
    const click = parentEnabled ? `onclick="toggleMod('${path}', this, event)"` : '';
    const master = isMaster ? ' data-master-toggle="1"' : '';
    return `
        <div class="neura-toggle ${v ? 'is-on' : ''}" role="switch" aria-checked="${v}" ${master} ${click}>
            <div class="neura-toggle-track">
                <span class="neura-toggle-thumb"></span>
            </div>
        </div>
    `;
}

function renderField(path, f, v, highlight = false, parentEnabled = true) {
    if (path === 'commands.shop.itemsToBuy') {
        return renderRingSelection(path, v, parentEnabled);
    }
    const label = formatCfgLabel(f.l);
    const hl = highlight ? ' cfg-row-highlight' : '';
    const locked = !parentEnabled && !f.master ? ' cfg-row-disabled' : '';
    const search = cfgSearchBlob(path, label, '', []);
    if (f.type === 'toggle') {
        return `
            <div class="cfg-row${hl}${locked}" data-search="${search}" data-path="${path}">
                <div class="cfg-row-label">
                    <span class="cfg-label-text">${label}</span>
                </div>
                <div class="cfg-row-control">
                    ${renderNeuraToggle(path, v, parentEnabled, f.master)}
                </div>
            </div>
        `;
    }
    if (f.type === 'range' || (Array.isArray(v) && v.length === 2 && typeof v[0] === 'number')) {
        return `
            <div class="cfg-row cfg-row-range${hl}${locked}" data-search="${search}" data-path="${path}">
                <div class="cfg-row-label">
                    <span class="cfg-label-text">${label}</span>
                </div>
                <div class="cfg-range-pair">
                    <div class="cfg-range-item">${renderStepperInner(`${path}.0`, 'Min', v[0], '', parentEnabled)}</div>
                    <div class="cfg-range-item">${renderStepperInner(`${path}.1`, 'Max', v[1], '', parentEnabled)}</div>
                </div>
            </div>
        `;
    }
    if (isListField(path)) {
        return `
            <div class="cfg-row cfg-row-list${hl}${locked}" data-search="${search}" data-path="${path}">
                <div class="cfg-row-label">
                    <span class="cfg-label-text">${label}</span>
                </div>
                <div class="cfg-row-control cfg-row-control-wide">
                    ${renderListInput(path, v, parentEnabled)}
                </div>
            </div>
        `;
    }
    if (typeof v === 'string' || (Array.isArray(v) && typeof v[0] === 'string') || (Array.isArray(v) && v.length === 0)) {
        const display = Array.isArray(v) ? v.join(', ') : v;
        const inputType = f.type === 'password' ? 'password' : 'text';
        const dis = parentEnabled ? '' : ' disabled';
        return `
            <div class="cfg-row${hl}${locked}" data-search="${search}" data-path="${path}">
                <div class="cfg-row-label">
                    <span class="cfg-label-text">${label}</span>
                </div>
                <div class="cfg-row-control">
                    <div class="cfg-input-wrap">
                        <input type="${inputType}" class="cfg-input" value="${display}"${dis}
                            onchange="updateDeepVal('${path}', this.value)">
                    </div>
                </div>
            </div>
        `;
    }
    if (typeof v === 'number') {
        let unit = '';
        const key = f.l.toLowerCase();
        if (key.includes('cash') || key.includes('amount') || key.includes('bet') || key.includes('balance')
            || key.includes('rate') || key === 'join_chance' || key === 'max_bet' || key === 'max_length' || key === 'min_length') {

        } else if (key.endsWith('_h') || (key.endsWith('_hour') || key === 'interval_h')) {
            unit = 'h';
        } else if (key.endsWith('_s') || key.endsWith('_sec') || key === 'interval_s') {
            unit = 's';
        } else if (key === 'interval_min' || key === 'duration_min') {

            unit = 'm';
        } else if (/^(reaction|key_delay|enter_delay)_(min|max)$/.test(key)) {

            unit = 's';
        } else if (key.endsWith('_min') || key.endsWith('_max')) {
          
            const base = key.replace(/_(min|max)$/, '');
            if (['cooldown', 'interval', 'delay', 'duration', 'reaction', 'key', 'enter'].some(k => base.includes(k))) {
                unit = 's';
            }

        } else if (['cooldown', 'interval', 'delay', 'duration'].some(k => key.includes(k))) {
            unit = 's';
        }
        const finalLabel = (path.includes('priorities') && f.l === 'radar') ? `${label} (1 = lowest)` : label;
        return `
            <div class="cfg-row${hl}${locked}" data-search="${search}" data-path="${path}">
                <div class="cfg-row-label">
                    <span class="cfg-label-text">${finalLabel}</span>
                </div>
                <div class="cfg-row-control">${renderStepperInner(path, '', v, unit, parentEnabled)}</div>
            </div>
        `;
    }
    const dis = parentEnabled ? '' : ' disabled';
    return `
        <div class="cfg-row${hl}${locked}" data-search="${search}" data-path="${path}">
            <div class="cfg-row-label">
                <span class="cfg-label-text">${label}</span>
            </div>
            <div class="cfg-row-control">
                <div class="cfg-input-wrap">
                    <input type="text" class="cfg-input" value="${v}"${dis} onchange="updateDeepVal('${path}', this.value)">
                </div>
            </div>
        </div>
    `;
}

function renderStepperInner(path, label, value, unit = '', parentEnabled = true) {
    const labelHtml = label ? `<div class="cfg-label-text">${formatCfgLabel(label)}</div>` : '';
    const dis = parentEnabled ? '' : ' disabled';
    return `
        ${labelHtml}
        <div class="cfg-stepper">
            <button type="button" class="cfg-stepper-btn" ${parentEnabled ? `onclick="updateStepper('${path}', -1, event)"` : 'disabled'}>
                <span class="icon-svg" style="--icon: url('/static/assets/neura_icons/minus.svg');"></span>
            </button>
            <input type="number" class="cfg-stepper-val" value="${value}"${dis} onchange="updateValueFromInput('${path}', this)">
            ${unit ? `<span class="cfg-stepper-unit">${unit}</span>` : ''}
            <button type="button" class="cfg-stepper-btn" ${parentEnabled ? `onclick="updateStepper('${path}', 1, event)"` : 'disabled'}>
                <span class="icon-svg" style="--icon: url('/static/assets/neura_icons/plus.svg');"></span>
            </button>
        </div>
    `;
}

window.updateValueFromInput = function(path, input) {
    let val = parseFloat(input.value);
    if (isNaN(val)) val = 0;
    const parts = path.split('.');
    const lastPart = parts[parts.length - 1];
    if (parts.length > 1 && !isNaN(lastPart)) {
        const index = parseInt(parts.pop());
        updateArrVal(parts.join('.'), index, val);
    } else {
        updateDeepVal(path, val);
    }
};

window.updateStepper = function (path, delta, ev) {
    if (ev) ev.stopPropagation();
    const btn = ev.currentTarget;
    const input = btn.parentElement.querySelector('input');
    let val = parseFloat(input.value) || 0;
    val = Math.max(0, val + delta);
    input.value = val;
    const parts = path.split('.');
    const lastPart = parts[parts.length - 1];
    if (parts.length > 1 && !isNaN(lastPart)) {
        const index = parseInt(parts.pop());
        updateArrVal(parts.join('.'), index, val);
    } else {
        updateDeepVal(path, val);
    }
};

function toggleMod(p, el, ev) {
    if (ev) ev.stopPropagation();
    const isGemTier = el.classList.contains('gem-tier-item');
    const isNeuraToggle = el.classList.contains('neura-toggle');
    const v = isGemTier
        ? !el.classList.contains('selected')
        : isNeuraToggle
            ? !el.classList.contains('is-on')
            : !el.classList.contains('on');
    setDeep(currentConfig, p.split('.'), v);
    if (isGemTier) {
        el.classList.toggle('selected', v);
        el.setAttribute('aria-pressed', v);
    } else if (isNeuraToggle) {
        el.classList.toggle('is-on', v);
        el.setAttribute('aria-checked', v);
        if (p.endsWith('.enabled') || p.split('.').pop() === 'enabled') {
            renderSettings(currentConfig);
        }
    } else if (el.classList.contains('cfg-switch')) {
        el.className = `cfg-switch ${v ? 'on' : 'off'}`;
        el.setAttribute('aria-checked', v);
    } else {
        el.className = `module-toggle ${v ? 'on' : 'off'}`;
        el.innerHTML = `<span class="icon-svg" style="--icon: url('/static/assets/neura_icons/toggle-${v ? 'on' : 'off'}.svg');"></span> ${v ? 'ON' : 'OFF'}`;
    }
    checkDirty();
}

function updateDeepVal(p, v) {
    let val = v;
    const arrayFields = ['channels', 'targets', 'active_commands', 'ignore_guilds'];
    const fieldName = p.split('.').pop();
    if (arrayFields.includes(fieldName)) {
        val = v.split(',').map(item => item.trim()).filter(item => item !== "");
    } else if (!isNaN(v) && v !== "") {
        val = (v.length < 15) ? Number(v) : v;
    }
    setDeep(currentConfig, p.split('.'), val);
    checkDirty();
}

function updateArrVal(p, i, v) {
    const a = getDeep(currentConfig, p.split('.'));
    if (a) {
        let val = v;
        if (!isNaN(v) && v !== "") {
            val = (v.length < 15) ? Number(v) : v;
        }
        a[i] = val;
    }
}

function saveAllConfigs() {
    const q = currentAccountId ? `?id=${currentAccountId}` : '';
    fetch(`/api/settings${q}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(currentConfig)
    }).then(() => {
        originalConfig = JSON.parse(JSON.stringify(currentConfig));
        checkDirty();
        showToast(`Settings Saved for Account: ${currentAccountId}`);
    });
}

function saveToAllConfigs() {
    const q = currentAccountId ? `?id=${currentAccountId}&all=true` : '?all=true';
    fetch(`/api/settings${q}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(currentConfig)
    }).then(res => res.json()).then(data => {
        if (data.status === "success") {
            originalConfig = JSON.parse(JSON.stringify(currentConfig));
            checkDirty();
            showToast("Settings Saved for ALL Accounts!", "success");
        } else {
            showToast(`Error: ${data.message || "Failed to save"}`, "error");
        }
    });
}

function renderRingSelection(path, selectedId, parentEnabled = true) {
    const ringIds = [1, 2, 3, 4, 5, 6, 7];
    const lock = parentEnabled ? '' : ' cfg-ring-locked';
    let h = `<div class="cfg-ring-block${lock}" data-search="shop ring itemsToBuy ${path}">
        <span class="cfg-label-text">Shop ring</span>
        <div class="ring-selection-grid">`;
    ringIds.forEach(id => {
        const isSelected = selectedId == id || (Array.isArray(selectedId) && selectedId.includes(id));
        const ext = id >= 6 ? 'gif' : 'webp';
        h += `
            <div class="ring-item ${isSelected ? 'selected' : ''}" data-id="${id}" ${parentEnabled ? `onclick="selectRing('${path}', ${id}, this)"` : ''}>
                <img src="/static/assets/owo_rings/ring_${id}.${ext}" alt="Ring ${id}" title="Ring ${id}">
            </div>
        `;
    });
    h += `</div></div>`;
    return h;
}

window.selectRing = function(path, id, el) {
    setDeep(currentConfig, path.split('.'), id);
    el.parentElement.querySelectorAll('.cfg-ring-opt, .ring-item').forEach(r => r.classList.remove('selected'));
    el.classList.add('selected');
    checkDirty();
};

function collectConfigMatches(obj, path, categoryName, sections, query, out) {
    let keys = Object.keys(obj);
    const isTiers = path.includes('tiers');
    const isTypes = path.includes('types');
    if (isTiers) {
        const tierOrder = ['common', 'uncommon', 'rare', 'epic', 'mythical', 'legendary', 'fabled'];
        keys.sort((a, b) => tierOrder.indexOf(a) - tierOrder.indexOf(b));
    }
    keys.forEach(key => {
        const val = obj[key];
        const fullPath = `${path}.${key}`;
        const label = formatCfgLabel(key);
        const blob = cfgSearchBlob(fullPath, label, categoryName, sections);
        if ((isTiers || isTypes) && typeof val === 'boolean') {
            if (blob.includes(query)) {
                out.push({ categoryName, html: renderTierChip(fullPath, key, val), isTier: true });
            }
        } else if (typeof val === 'boolean') {
            if (blob.includes(query)) {
                out.push({ categoryName, html: renderField(fullPath, { l: key, type: 'toggle' }, val, true) });
            }
        } else if (Array.isArray(val) && val.length === 2 && typeof val[0] === 'number') {
            if (blob.includes(query)) {
                out.push({ categoryName, html: renderField(fullPath, { l: key, type: 'range' }, val, true) });
            }
        } else if (typeof val === 'object' && val !== null && !Array.isArray(val)) {
            collectConfigMatches(val, fullPath, categoryName, [...sections, label], query, out);
        } else if (fullPath === 'commands.shop.itemsToBuy') {
            if (blob.includes(query) || query.includes('ring') || query.includes('shop')) {
                out.push({ categoryName, html: renderRingSelection(fullPath, val) });
            }
        } else if (isListField(fullPath)) {
            if (blob.includes(query)) {
                out.push({ categoryName, html: renderField(fullPath, { l: key, type: 'text' }, val, true) });
            }
        } else if (isSelectField(fullPath)) {
            if (blob.includes(query)) {
                out.push({ categoryName, html: renderSelectDropdown(fullPath, val, true) });
            }
        } else {
            if (blob.includes(query)) {
                out.push({
                    categoryName,
                    html: renderField(fullPath, { l: key, type: key.includes('url') ? 'password' : 'text' }, val, true)
                });
            }
        }
    });
}