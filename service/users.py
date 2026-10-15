"""Login identities live here; Discord credentials remain inside each workspace."""
from contextlib import contextmanager
from pathlib import Path
import json
import re
import secrets
import shutil
import sqlite3
import time
import uuid

from werkzeug.security import check_password_hash, generate_password_hash


def password_hash(password):
    if not isinstance(password, str) or not 8 <= len(password) <= 256:
        raise ValueError('Mật khẩu phải có từ 8 đến 256 ký tự.')
    return generate_password_hash(password, method='pbkdf2:sha256:600000')


def public_user(user):
    return {k: user[k] for k in ('id', 'username', 'role', 'enabled', 'expires_at', 'created_at')}


def is_active(user):
    return bool(user and user['enabled'] and
                (user['expires_at'] is None or user['expires_at'] > time.time()))


class UserStore:
    def __init__(self, root, source):
        self.root, self.source = Path(root).resolve(), Path(source).resolve()
        self.root.mkdir(parents=True, exist_ok=True, mode=0o700)
        self.database = self.root / 'users.sqlite3'
        with self.db() as db:
            db.executescript('''
                CREATE TABLE IF NOT EXISTS users (
                    id TEXT PRIMARY KEY, username TEXT UNIQUE COLLATE NOCASE NOT NULL,
                    password_hash TEXT NOT NULL, role TEXT NOT NULL,
                    enabled INTEGER NOT NULL DEFAULT 1, expires_at REAL,
                    version INTEGER NOT NULL DEFAULT 1, created_at REAL NOT NULL
                );
                CREATE TABLE IF NOT EXISTS metadata (key TEXT PRIMARY KEY, value TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS login_failures (
                    key TEXT PRIMARY KEY, attempts INTEGER NOT NULL, blocked_until REAL NOT NULL
                );
            ''')
            db.execute('INSERT OR IGNORE INTO metadata VALUES (?, ?)', ('secret', secrets.token_hex(32)))
        self.database.chmod(0o600)

    @contextmanager
    def db(self):
        db = sqlite3.connect(self.database, timeout=20)
        db.row_factory = sqlite3.Row
        try:
            with db:
                yield db
        finally:
            db.close()

    @property
    def secret(self):
        with self.db() as db:
            return db.execute("SELECT value FROM metadata WHERE key='secret'").fetchone()[0]

    def all(self):
        with self.db() as db:
            return [dict(r) for r in db.execute('SELECT * FROM users ORDER BY created_at')]

    def get(self, uid):
        with self.db() as db:
            row = db.execute('SELECT * FROM users WHERE id=?', (uid,)).fetchone()
            return dict(row) if row else None

    def find(self, username):
        with self.db() as db:
            row = db.execute('SELECT * FROM users WHERE username=?', (username,)).fetchone()
            return dict(row) if row else None

    def directory(self, uid):
        if not re.fullmatch(r'[a-f0-9]{32}', uid or ''):
            raise ValueError('ID người dùng không hợp lệ.')
        return self.root / 'tenants' / uid

    def provision(self, uid, legacy=False):
        path = self.directory(uid)
        (path / 'config').mkdir(parents=True, exist_ok=True, mode=0o700)
        (path / 'data').mkdir(exist_ok=True)
        if legacy:
            for dirname in ('config', 'data'):
                for p in (self.source / dirname).glob('*'):
                    if p.is_file() and p.name not in ('auth.json', 'setup.log'):
                        shutil.copy2(p, path / dirname / p.name)
        for p in (self.source / 'defaults').glob('*.json'):
            dest = path / 'config' / p.name
            if not dest.exists():
                shutil.copy2(p, dest)
        for name, empty in [('accounts.json', {'accounts': []}), ('proxies.json', {'proxies': []})]:
            dest = path / 'config' / name
            if not dest.exists():
                dest.write_text(json.dumps(empty), encoding='utf-8')
        quotes = path / 'data/yulee_quotes.json'
        if not quotes.exists() and (self.source / 'data/yulee_quotes.json').exists():
            shutil.copy2(self.source / 'data/yulee_quotes.json', quotes)
        return path

    def create(self, username, password, role='user', expires_at=None, legacy=False):
        username = username.strip() if isinstance(username, str) else ''
        if not re.fullmatch(r'[A-Za-z0-9_.-]{3,64}', username):
            raise ValueError('Tên đăng nhập: 3–64 ký tự, dùng chữ, số, dấu . _ -')
        if role not in ('admin', 'user'):
            raise ValueError('Vai trò không hợp lệ.')
        hashed = (generate_password_hash(password, method='pbkdf2:sha256:600000')
                  if legacy else password_hash(password))
        uid = uuid.uuid4().hex
        try:
            with self.db() as db:
                db.execute('INSERT INTO users VALUES (?, ?, ?, ?, 1, ?, 1, ?)',
                           (uid, username, hashed, role, expires_at, time.time()))
                self.provision(uid, legacy=legacy)
        except sqlite3.IntegrityError:
            raise ValueError('Tên đăng nhập đã tồn tại.') from None
        return self.get(uid)

    def migrate_admin(self):
        if self.all():
            return
        legacy_file = self.source / 'config/auth.json'
        if not legacy_file.exists():
            return
        legacy = json.loads(legacy_file.read_text(encoding='utf-8'))
        if legacy.get('password') in ('yuleeself_default_password_change_me', 'neuraself_default_password_change_me'):
            return
        if legacy.get('username') and legacy.get('password'):
            self.create(legacy['username'], legacy['password'], 'admin', legacy=True)

    def change_password(self, uid, old, new):
        hashed = password_hash(new)
        with self.db() as db:
            row = db.execute('SELECT * FROM users WHERE id=?', (uid,)).fetchone()
            if not row or not check_password_hash(row['password_hash'], old):
                raise ValueError('Mật khẩu hiện tại không đúng.')
            db.execute('UPDATE users SET password_hash=?, version=version+1 WHERE id=?', (hashed, uid))
        return self.get(uid)

    def update(self, uid, payload, actor_id):
        with self.db() as db:
            db.execute('BEGIN IMMEDIATE')
            row = db.execute('SELECT * FROM users WHERE id=?', (uid,)).fetchone()
            if not row:
                raise ValueError('Không tìm thấy người dùng.')
            enabled = payload.get('enabled', bool(row['enabled']))
            if not isinstance(enabled, bool):
                raise ValueError('enabled phải là true/false.')
            expires = payload.get('expires_at', row['expires_at'])
            if row['role'] == 'admin' and (not enabled or expires is not None):
                raise ValueError('Không khóa hoặc đặt hạn dùng cho quản trị viên.')
            hashed = password_hash(payload['password']) if payload.get('password') else row['password_hash']
            db.execute('UPDATE users SET enabled=?, expires_at=?, password_hash=?, version=version+1 WHERE id=?',
                       (int(enabled), expires, hashed, uid))
        return self.get(uid)

    def delete(self, uid):
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

    def authenticate(self, username, password, ip):
        # Also limit by IP so cycling usernames cannot bypass the limit.
        keys = ['ip:' + ip, 'name:' + username.lower()]
        now = time.time()
        with self.db() as db:
            for key in keys:
                row = db.execute('SELECT * FROM login_failures WHERE key=?', (key,)).fetchone()
                if row and row['blocked_until'] > now:
                    return None
        user = self.find(username)
        good = user and check_password_hash(user['password_hash'], password) and is_active(user)
        with self.db() as db:
            for key in keys:
                if good:
                    db.execute('DELETE FROM login_failures WHERE key=?', (key,))
                    continue
                row = db.execute('SELECT * FROM login_failures WHERE key=?', (key,)).fetchone()
                count = (row['attempts'] if row and row['blocked_until'] == 0 else 0) + 1
                db.execute('INSERT OR REPLACE INTO login_failures VALUES (?, ?, ?)',
                           (key, count, now + 300 if count >= 5 else 0))
        return user if good else None
