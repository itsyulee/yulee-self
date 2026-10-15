"""Public dashboard: session -> user ID -> private worker. No client-selected tenant."""
from datetime import datetime, timezone, timedelta
from pathlib import Path
from urllib.parse import urlsplit
import atexit
import math
import os
import secrets
import threading

from flask import Flask, Response, abort, g, jsonify, redirect, render_template, request, session
from werkzeug.exceptions import HTTPException
import requests

from service.users import UserStore, is_active, public_user
from service.workers import WorkerManager

SOURCE = Path(__file__).resolve().parents[1]


def expiry(value):
    if value is None or value == '':
        return None
    try:
        if isinstance(value, str):
            parsed = datetime.fromisoformat(value.replace('Z', '+00:00'))
            value = parsed.replace(tzinfo=parsed.tzinfo or timezone.utc).timestamp()
        if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
            raise ValueError
        return float(value)
    except (ValueError, OverflowError):
        raise ValueError('Thời hạn sử dụng không hợp lệ.') from None


def create_app(data_root=None, manager_class=WorkerManager):
    app = Flask(__name__, template_folder=str(SOURCE / 'dashboard/templates'),
                static_folder=str(SOURCE / 'dashboard/static'))
    store = UserStore(data_root or os.environ.get('YULEESELF_SERVICE_DIR', SOURCE / 'data/service'), SOURCE)
    store.migrate_admin()
    manager = manager_class(store)
    app.extensions.update(user_store=store, worker_manager=manager)
    app.secret_key = store.secret
    app.config.update(SESSION_COOKIE_NAME='yuleeself_session', SESSION_COOKIE_HTTPONLY=True,
                      SESSION_COOKIE_SAMESITE='Lax', SESSION_COOKIE_SECURE=os.environ.get('YULEESELF_HTTPS') == '1',
                      PERMANENT_SESSION_LIFETIME=timedelta(hours=12), MAX_CONTENT_LENGTH=1024 * 1024)

    @app.before_request
    def authorize():
        if request.endpoint == 'static':
            return
        if request.method not in ('GET', 'HEAD', 'OPTIONS'):
            origin = request.headers.get('Origin')
            if origin and urlsplit(origin).netloc != request.host:
                abort(403, 'Nguồn yêu cầu không hợp lệ.')
        if request.method in ('POST', 'PATCH') and request.endpoint in ('login', 'change_password', 'users', 'edit_user'):
            if not isinstance(request.get_json(silent=True), dict):
                abort(400, 'Dữ liệu phải là một JSON object.')
        if request.endpoint == 'login':
            return
        user = store.get(session.get('user_id', ''))
        if not is_active(user) or session.get('version') != user['version']:
            session.clear()
            if request.path.startswith('/api/'):
                return jsonify(error='Phiên đã hết hạn hoặc tài khoản đã bị khóa.', success=False), 401
            return redirect('/login')
        g.user = user
        if request.method not in ('GET', 'HEAD', 'OPTIONS'):
            supplied = request.headers.get('X-CSRF-Token', '')
            expected = session.get('csrf', '')
            if not expected or not secrets.compare_digest(supplied, expected):
                abort(403, 'Hãy tải lại trang trước khi tiếp tục.')

    @app.after_request
    def headers(response):
        if request.endpoint != 'static':
            response.headers['Cache-Control'] = 'no-store'
        response.headers['X-Content-Type-Options'] = 'nosniff'
        response.headers['X-Frame-Options'] = 'DENY'
        return response

    @app.errorhandler(ValueError)
    def bad_value(error):
        return jsonify(success=False, status='error', error=str(error), message=str(error)), 400

    @app.errorhandler(HTTPException)
    def http_error(error):
        return jsonify(success=False, status='error', error=error.description, message=error.description), error.code

    @app.route('/login', methods=['GET', 'POST'])
    def login():
        if request.method == 'GET':
            return render_template('login.html')
        data = request.get_json()
        if not isinstance(data, dict):
            abort(400)
        username, password = data.get('username', ''), data.get('password', '')
        if not isinstance(username, str) or not isinstance(password, str) or len(username) > 64 or len(password) > 256:
            abort(400)
        user = store.authenticate(username.strip(), password, request.remote_addr or 'unknown')
        if not user:
            return jsonify(success=False, error='Sai thông tin, tài khoản bị khóa/hết hạn hoặc đăng nhập quá nhiều lần.'), 401
        session.clear()
        session.update(user_id=user['id'], version=user['version'], csrf=secrets.token_urlsafe(32))
        session.permanent = True
        return jsonify(success=True)

    @app.route('/logout', methods=['POST'])
    def logout():
        session.clear()
        return jsonify(success=True)

    @app.route('/')
    def home():
        return render_template('index.html', login_user=public_user(g.user), csrf_token=session['csrf'])

    @app.route('/api/me')
    def me():
        return jsonify(user=public_user(g.user), csrf_token=session['csrf'])

    @app.route('/api/me/password', methods=['POST'])
    def change_password():
        data = request.get_json()
        old = data.get('current_password', '')
        if not isinstance(old, str) or len(old) > 256:
            abort(400)
        user = store.change_password(g.user['id'], old, data.get('new_password'))
        # Keep this browser signed in; every other old session is invalidated.
        session['version'] = user['version']
        session['csrf'] = secrets.token_urlsafe(32)
        return jsonify(success=True, csrf_token=session['csrf'])

    def require_admin():
        if g.user['role'] != 'admin':
            abort(403, 'Chỉ admin được quản lý tài khoản sử dụng.')

    @app.route('/api/admin/users', methods=['GET', 'POST'])
    def users():
        require_admin()
        if request.method == 'GET':
            return jsonify(users=[public_user(u) for u in store.all()])
        data = request.get_json()
        user = store.create(data.get('username'), data.get('password'),
                            expires_at=expiry(data.get('expires_at')))
        if data.get('enabled') is False:
            user = store.update(user['id'], {'enabled': False}, g.user['id'])
        return jsonify(success=True, user=public_user(user)), 201

    @app.route('/api/admin/users/<uid>', methods=['PATCH'])
    def edit_user(uid):
        require_admin()
        data = request.get_json()
        if 'expires_at' in data:
            data['expires_at'] = expiry(data['expires_at'])
        if uid == g.user['id']:
            abort(400, 'Dùng mục Đổi mật khẩu để thay mật khẩu của bạn.')
        user = store.update(uid, data, g.user['id'])
        if not is_active(user):
            manager.stop(uid)
        return jsonify(success=True, user=public_user(user))

    @app.route('/api/admin/users/<uid>', methods=['DELETE'])
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

    @app.route('/api/<path:path>', methods=['GET', 'POST', 'DELETE'])
    def tenant_api(path):
        if path.startswith(('admin/', 'me/')) or path == 'me':
            abort(404)
        # No arbitrary URL, host, tenant ID or forwarded auth header accepted.
        if any(piece in ('.', '..', '') for piece in path.split('/')) or '\\' in path:
            abort(404)
        uid = g.user['id']
        try:
            with manager.user_lock(uid):
                response = manager.request(uid, request.method, 'api/' + path,
                                           request.query_string,
                                           request.get_json(silent=True) if request.method != 'GET' else None)
                # A restart affects only the current login and applies new tokens/proxies immediately.
                mutation = request.method in ('POST', 'DELETE') and (
                    path in ('accounts', 'accounts/config', 'proxies', 'proxies/assign') or
                    (path.startswith('proxies/') and request.method == 'DELETE'))
                if mutation and response.status_code < 300:
                    manager.stop(uid)
                return Response(response.content, status=response.status_code,
                                content_type=response.headers.get('Content-Type', 'application/json'))
        except (requests.RequestException, RuntimeError) as error:
            app.logger.warning('Tenant worker unavailable for %s: %s', uid, type(error).__name__)
            return jsonify(success=False, status='error', message='Worker chưa sẵn sàng. Thử lại sau vài giây.'), 503

    return app


def serve():
    from waitress import serve as waitress_serve
    app = create_app()
    store, manager = app.extensions['user_store'], app.extensions['worker_manager']
    from service.instance import InstanceLock
    instance_lock = InstanceLock(store.root / 'gateway.lock')
    atexit.register(instance_lock.close)
    if not store.all():
        import getpass
        username = os.environ.get('YULEESELF_ADMIN_USER')
        password = os.environ.get('YULEESELF_ADMIN_PASSWORD')
        if not username or not password:
            if not __import__('sys').stdin.isatty():
                raise RuntimeError('Lần đầu: đặt YULEESELF_ADMIN_USER và YULEESELF_ADMIN_PASSWORD hoặc chạy trên terminal để tạo admin.')
            username = input('Tên đăng nhập admin: ').strip()
            password = getpass.getpass('Mật khẩu admin (ít nhất 8 ký tự): ')
        admin = store.create(username, password, role='admin')
        store.provision(admin['id'], legacy=True)
    atexit.register(manager.close)
    import signal
    def terminate(*_):
        raise SystemExit(0)
    signal.signal(signal.SIGTERM, terminate)
    threading.Thread(target=manager.monitor, daemon=True).start()
    host = os.environ.get('YULEESELF_HOST', '0.0.0.0')
    port = int(os.environ.get('SERVER_PORT') or os.environ.get('PORT') or os.environ.get('YULEESELF_PORT') or '8000')
    print(f'YULEESELF dashboard: http://localhost:{port} — thêm Discord và proxy trên web.')
    try:
        waitress_serve(app, host=host, port=port, threads=12)
    finally:
        manager.close()
        instance_lock.close()
