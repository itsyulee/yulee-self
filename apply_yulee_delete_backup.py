"""Update the YULEESELF deletion feature so every deleted user is backed up.

Run from the repository root, after installing apply_yulee_delete_user.py:
    python apply_yulee_delete_backup.py

This patch does NOT delete any accounts. It only updates service/users.py.
"""
from datetime import datetime
from pathlib import Path
import ast
import shutil
import sys

ROOT = Path(__file__).resolve().parent
SOURCE = ROOT / 'service' / 'users.py'

NEW_METHOD = '''    def delete(self, uid):
        """Back up a user's credentials and workspace before deleting their login."""
        path = self.directory(uid)
        tenants = self.root / 'tenants'
        backup_root = self.root / 'backup'
        if tenants.is_symlink() or path.is_symlink() or backup_root.is_symlink():
            raise ValueError('Thư mục tài khoản hoặc sao lưu không hợp lệ.')

        tombstone = None
        unfinished = None
        backup_path = None
        try:
            with self.db() as db:
                db.execute('BEGIN IMMEDIATE')
                row = db.execute('SELECT * FROM users WHERE id=?', (uid,)).fetchone()
                if not row:
                    raise ValueError('Không tìm thấy tài khoản.')
                if row['role'] != 'user':
                    raise ValueError('Không thể xóa tài khoản quản trị viên.')

                # Keep credentials private: this location is excluded from Git.
                backup_root.mkdir(parents=True, exist_ok=True, mode=0o700)
                backup_root.chmod(0o700)
                backup_name = (row['username'] + '_' +
                               time.strftime('%Y%m%d_%H%M%S', time.localtime()) + '_' +
                               uid[:8] + '_' + secrets.token_hex(4))
                unfinished = backup_root / ('.incomplete_' + backup_name)
                backup_path = backup_root / backup_name
                unfinished.mkdir(mode=0o700)

                # Copy first. If copying fails, the DB transaction rolls back
                # and the original workspace is left untouched.
                if path.exists():
                    shutil.copytree(path, unfinished / 'workspace', symlinks=True)
                record = {'deleted_at': time.time(), 'user': dict(row)}
                metadata = unfinished / 'user.json'
                metadata.write_text(json.dumps(record, ensure_ascii=False, indent=2),
                                    encoding='utf-8')
                metadata.chmod(0o600)
                unfinished.rename(backup_path)
                unfinished = None

                # Hide the original workspace until the DB transaction commits.
                if path.exists():
                    tombstone = tenants / ('.deleting-' + uid + '-' + secrets.token_hex(8))
                    path.rename(tombstone)
                db.execute('DELETE FROM login_failures WHERE key=?',
                           ('name:' + row['username'].lower(),))
                db.execute('DELETE FROM users WHERE id=?', (uid,))
        except Exception:
            if tombstone is not None and tombstone.exists() and not path.exists():
                tombstone.rename(path)
            if unfinished is not None and unfinished.exists():
                shutil.rmtree(unfinished)
            raise

        # The backup stays in data/service/backup even after the live workspace
        # is removed. On cleanup failure, the backup remains intact.
        if tombstone is not None:
            shutil.rmtree(tombstone)
        return str(backup_path)

'''

if not SOURCE.is_file():
    sys.exit('Không tìm thấy service/users.py. Đặt script ở thư mục gốc yulee-self.')

original = SOURCE.read_text(encoding='utf-8')
start_mark = '    def delete(self, uid):\n'
end_mark = '    def authenticate(self, username, password, ip):\n'
if original.count(start_mark) != 1 or original.count(end_mark) != 1:
    sys.exit('Chưa có chức năng xóa tài khoản. Hãy chạy apply_yulee_delete_user.py trước.')
start = original.index(start_mark)
end = original.index(end_mark, start)
old_method = original[start:end]

if "backup_root = self.root / 'backup'" in old_method:
    sys.exit('Chức năng sao lưu trước khi xóa đã được cài. Không cần chạy lại.')
if ("Permanently delete a non-admin login and its private workspace." not in old_method
        or "db.execute('DELETE FROM users WHERE id=?', (uid,))" not in old_method
        or 'tombstone' not in old_method):
    sys.exit('Hàm xóa đã được sửa khác bản trước. Mình không tự ghi đè để tránh mất code.')

# service/users.py already imports json, secrets, shutil and time in this version.
for statement in ('import json', 'import secrets', 'import shutil', 'import time'):
    if statement not in original:
        sys.exit(f'Thiếu {statement} trong service/users.py; không tự sửa.')
updated = original[:start] + NEW_METHOD + original[end:]
try:
    ast.parse(updated, filename=str(SOURCE))
except SyntaxError as exc:
    sys.exit('Bản cập nhật có lỗi cú pháp; không ghi file: ' + str(exc))

backup_code = ROOT / ('backup_users_code_' + datetime.now().strftime('%Y%m%d_%H%M%S_%f'))
backup_code.mkdir()
shutil.copy2(SOURCE, backup_code / 'users.py')
try:
    SOURCE.write_text(updated, encoding='utf-8')
except OSError:
    shutil.copy2(backup_code / 'users.py', SOURCE)
    raise

print('Đã cập nhật: service/users.py')
print('Từ nay, xóa tài khoản sẽ sao lưu vào: data/service/backup/<username>_<time>_<id>/')
print('Bản sao code trước khi sửa: ' + str(backup_code))
print('Khởi động lại web để áp dụng.')
