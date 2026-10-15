let sessionCsrf = document.querySelector('meta[name="csrf-token"]')?.content || '';
const originalFetch = window.fetch.bind(window);
window.fetch = async function(input, options = {}) {
    const url = new URL(typeof input === 'string' ? input : input.url, location.origin);
    const method = (options.method || 'GET').toUpperCase();
    if (url.origin === location.origin && !['GET', 'HEAD', 'OPTIONS'].includes(method)) {
        options.headers = new Headers(options.headers || {});
        options.headers.set('X-CSRF-Token', sessionCsrf);
    }
    const response = await originalFetch(input, options);
    if (response.status === 401 && url.origin === location.origin) {
        location.replace('/login');
        throw new Error('Phiên đăng nhập đã hết hạn.');
    }
    return response;
};

function escapeHtml(value) {
    return String(value ?? '').replace(/[&<>"']/g, char => ({
        '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;'
    })[char]);
}

async function sessionRequest(url, method, body) {
    const response = await fetch(url, {
        method, headers: { 'Content-Type': 'application/json' },
        body: body === undefined ? undefined : JSON.stringify(body)
    });
    const data = await response.json();
    if (!response.ok) throw new Error(data.error || data.message || 'Không thực hiện được yêu cầu.');
    return data;
}

async function logoutSession() {
    await sessionRequest('/logout', 'POST');
    location.replace('/login');
}

async function changeLoginPassword(event) {
    event.preventDefault();
    const result = document.getElementById('password-result');
    const password = document.getElementById('new-password').value;
    if (password !== document.getElementById('confirm-password').value) {
        result.textContent = 'Hai mật khẩu mới không khớp.';
        return;
    }
    const button = event.target.querySelector('button[type="submit"]');
    button.disabled = true;
    try {
        const data = await sessionRequest('/api/me/password', 'POST', {
            current_password: document.getElementById('current-password').value,
            new_password: password
        });
        sessionCsrf = data.csrf_token;
        event.target.reset();
        result.textContent = 'Đã đổi mật khẩu và đăng xuất các phiên đăng nhập cũ khác.';
    } catch (error) {
        result.textContent = error.message;
    } finally {
        button.disabled = false;
    }
}

let loginUsers = [];
async function loadUsers() {
    const list = document.getElementById('login-user-list');
    if (!list) return;
    try {
        const response = await fetch('/api/admin/users');
        const data = await response.json();
        if (!response.ok) throw new Error(data.error || 'Không tải được danh sách.');
        loginUsers = data.users;
        list.innerHTML = loginUsers.map((user, index) => {
            const expired = user.expires_at && user.expires_at * 1000 <= Date.now();
            const status = !user.enabled ? 'Đã khóa' : expired ? 'Hết hạn' : 'Đang hoạt động';
            const deadline = user.expires_at ? new Date(user.expires_at * 1000).toLocaleString() : 'Không giới hạn';
            return `<div class="account-config-card"><div class="account-config-info">
                <strong>${escapeHtml(user.username)}</strong>
                <span>${escapeHtml(user.role)} · ${status}</span>
                <span>Hạn dùng: ${escapeHtml(deadline)}</span></div>
                ${user.role === 'user' ? `<button class="btn-proxy-sm" onclick="editLoginUser(${index})">Sửa / khóa / đặt lại mật khẩu</button>` : ''}
            </div>`;
        }).join('');
    } catch (error) {
        list.textContent = error.message;
    }
}

function resetUserForm() {
    document.getElementById('user-form').reset();
    document.getElementById('login-user-id').value = '';
    document.getElementById('login-user-name').disabled = false;
    document.getElementById('user-form-title').textContent = 'Cấp tài khoản mới';
    document.getElementById('user-result').textContent = '';
}

function editLoginUser(index) {
    const user = loginUsers[index];
    resetUserForm();
    document.getElementById('login-user-id').value = user.id;
    document.getElementById('login-user-name').value = user.username;
    document.getElementById('login-user-name').disabled = true;
    document.getElementById('login-user-enabled').checked = Boolean(user.enabled);
    if (user.expires_at) {
        const date = new Date(user.expires_at * 1000);
        const local = new Date(date.getTime() - date.getTimezoneOffset() * 60000);
        document.getElementById('login-user-expiry').value = local.toISOString().slice(0, 16);
    }
    document.getElementById('user-form-title').textContent = `Chỉnh quyền: ${user.username}`;
    document.getElementById('user-form').scrollIntoView({ behavior: 'smooth', block: 'start' });
}

async function saveLoginUser(event) {
    event.preventDefault();
    const result = document.getElementById('user-result');
    const id = document.getElementById('login-user-id').value;
    const deadline = document.getElementById('login-user-expiry').value;
    const body = {
        username: document.getElementById('login-user-name').value.trim(),
        password: document.getElementById('login-user-password').value,
        enabled: document.getElementById('login-user-enabled').checked,
        expires_at: deadline ? new Date(deadline).toISOString() : null
    };
    if (!id && body.password.length < 8) {
        result.textContent = 'Tài khoản mới cần mật khẩu ít nhất 8 ký tự.';
        return;
    }
    const button = event.target.querySelector('button[type="submit"]');
    button.disabled = true;
    try {
        await sessionRequest(id ? `/api/admin/users/${id}` : '/api/admin/users', id ? 'PATCH' : 'POST', body);
        resetUserForm();
        result.textContent = 'Đã lưu quyền sử dụng. Thay đổi chỉ áp dụng cho người dùng này.';
        await loadUsers();
    } catch (error) {
        result.textContent = error.message;
    } finally {
        button.disabled = false;
    }
}
