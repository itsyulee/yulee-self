"""Add permanent user deletion to YULEESELF Admin Panel.

Place this file at the root of the yulee-self checkout and run:
    python apply_yulee_delete_user.py

It makes backups before editing. It does NOT delete any existing account or database.
"""
from pathlib import Path
from datetime import datetime
import ast
import shutil
import sys

ROOT = Path(__file__).resolve().parent

USER_METHOD = '''    def delete(self, uid):
        """Permanently delete a non-admin login and its private workspace."""
        path = self.directory(uid)
        tenants = self.root / 'tenants'
        if tenants.is_symlink() or path.is_symlink():
            raise ValueError('Thư mục tài khoản không hợp lệ.')
        tombstone = None
        try:
            with self.db() as db:
                db.execute('BEGIN IMMEDIATE')
                row = db.execute('SELECT username, role FROM users WHERE id=?', (uid,)).fetchone()
                if not row:
                    raise ValueError('Không tìm thấy tài khoản.')
                if row['role'] != 'user':
                    raise ValueError('Không thể xóa tài khoản quản trị viên.')
                if path.exists():
                    tombstone = tenants / ('.deleting-' + uid + '-' + secrets.token_hex(8))
                    path.rename(tombstone)
                db.execute('DELETE FROM login_failures WHERE key=?', ('name:' + row['username'].lower(),))
                db.execute('DELETE FROM users WHERE id=?', (uid,))
        except Exception:
            if tombstone is not None and tombstone.exists() and not path.exists():
                tombstone.rename(path)
            raise
        if tombstone is not None:
            shutil.rmtree(tombstone)

'''

GATEWAY_ROUTE = '''    @app.route('/api/admin/users/<uid>', methods=['DELETE'])
    def delete_user(uid):
        require_admin()
        if uid == g.user['id']:
            abort(400, 'Không thể tự xóa tài khoản đang đăng nhập.')
        with manager.user_lock(uid):
            user = store.get(uid)
            if not user:
                abort(404, 'Không tìm thấy tài khoản.')
            if user['role'] != 'user':
                abort(403, 'Không thể xóa tài khoản quản trị viên.')
            manager.stop(uid)
            try:
                store.delete(uid)
            except OSError:
                app.logger.exception('Failed to clean deleted workspace for %s', uid)
                return jsonify(success=False, error='Đã xóa tài khoản khỏi database nhưng không thể dọn sạch dữ liệu. Hãy kiểm tra log server.'), 500
        return jsonify(success=True, message='Đã xóa hoàn toàn tài khoản và dữ liệu riêng.')

'''

JS_FUNCTION = '''async function deleteLoginUser(index) {
    const user = loginUsers[index];
    if (!user || user.role !== 'user') return;
    const typed = window.prompt(`XÓA VĨNH VIỄN tài khoản "${user.username}" và toàn bộ dữ liệu riêng (bao gồm token, proxy và lịch sử).\\n\\nNhập đúng tên đăng nhập để xác nhận:`);
    if (typed === null) return;
    if (typed !== user.username) {
        window.alert('Tên đăng nhập không khớp. Tài khoản chưa bị xóa.');
        return;
    }
    const result = document.getElementById('user-result');
    try {
        await sessionRequest(`/api/admin/users/${encodeURIComponent(user.id)}`, 'DELETE');
        if (document.getElementById('login-user-id').value === user.id) {
            resetUserForm();
        }
        await loadUsers();
        result.textContent = `Đã xóa hoàn toàn tài khoản ${user.username}.`;
    } catch (error) {
        result.textContent = error.message;
    }
}
'''

paths = {
    'users': ROOT / 'service/users.py',
    'gateway': ROOT / 'service/gateway.py',
    'js': ROOT / 'dashboard/static/js/session.js',
}
missing = [str(p.relative_to(ROOT)) for p in paths.values() if not p.is_file()]
if missing:
    sys.exit('Không tìm thấy file: ' + ', '.join(missing) + '\nHãy đặt script ở thư mục gốc yulee-self.')

original = {key: p.read_text(encoding='utf-8') for key, p in paths.items()}
if ('def delete(self, uid):' in original['users'] and
        "@app.route('/api/admin/users/<uid>', methods=['DELETE'])" in original['gateway'] and
        'async function deleteLoginUser(index)' in original['js']):
    sys.exit('Các chức năng xóa tài khoản đã tồn tại, không cần cập nhật nữa.')


def replace_once(content, old, new, file):
    count = content.count(old)
    if count != 1:
        raise ValueError(f'{file}: phải tìm thấy đúng 1 đoạn mã khớp, hiện tìm thấy {count}. Không thay đổi file nào.')
    return content.replace(old, new, 1)

try:
    updated = {}
    updated['users'] = replace_once(
        original['users'],
        '    def authenticate(self, username, password, ip):',
        USER_METHOD + '    def authenticate(self, username, password, ip):',
        'service/users.py'
    )
    updated['gateway'] = replace_once(
        original['gateway'],
        "    @app.route('/api/<path:path>', methods=['GET', 'POST', 'DELETE'])",
        GATEWAY_ROUTE + "    @app.route('/api/<path:path>', methods=['GET', 'POST', 'DELETE'])",
        'service/gateway.py'
    )
    old_btn = "                ${user.role === 'user' ? `<button class=\"btn-proxy-sm\" onclick=\"editLoginUser(${index})\">Chỉnh sửa</button>` : ''}"
    new_btn = "                ${user.role === 'user' ? `<div style=\"display:flex;gap:8px;margin-left:auto;align-items:center\"><button class=\"btn-proxy-sm\" onclick=\"editLoginUser(${index})\">Chỉnh sửa</button><button class=\"btn-proxy-sm\" style=\"color:var(--danger, #ff4d4d)\" onclick=\"deleteLoginUser(${index})\">Xóa</button></div>` : ''}"
    updated['js'] = replace_once(original['js'], old_btn, new_btn, 'dashboard/static/js/session.js')
    updated['js'] = replace_once(updated['js'], 'function resetUserForm() {', JS_FUNCTION + '\nfunction resetUserForm() {', 'dashboard/static/js/session.js')
    ast.parse(updated['users'], filename='service/users.py')
    ast.parse(updated['gateway'], filename='service/gateway.py')
except (ValueError, SyntaxError) as error:
    sys.exit('Không áp dụng được bản cập nhật: ' + str(error))

backup_dir = ROOT / ('backup_delete_user_' + datetime.now().strftime('%Y%m%d_%H%M%S'))
backup_dir.mkdir()
for key, path in paths.items():
    backup = backup_dir / path.relative_to(ROOT)
    backup.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(path, backup)

written = []
try:
    for key, path in paths.items():
        path.write_text(updated[key], encoding='utf-8')
        written.append((key, path))
except OSError:
    for key, path in written:
        shutil.copy2(backup_dir / path.relative_to(ROOT), path)
    raise

print('Đã cập nhật 3 file:')
for path in paths.values():
    print(' - ' + str(path.relative_to(ROOT)))
print('Đã sao lưu tại: ' + str(backup_dir))
print('Khởi động lại web và nhấn Ctrl + F5.')
