"""One private process per login: old cog globals and files cannot mix tenants."""
from pathlib import Path
import json
import os
import secrets
import subprocess
import sys
import threading
import time

import requests
import logging
from logging.handlers import RotatingFileHandler


def collect_worker_logs(pipe, log_path):
    handler = None
    try:
        handler = RotatingFileHandler(
            log_path, maxBytes=10 * 1024 * 1024,
            backupCount=2, encoding='utf-8',
        )
        handler.setFormatter(logging.Formatter('%(message)s'))
        # Bound reads even if a worker emits a very long line.
        while True:
            line = pipe.readline(16384)
            if not line:
                break
            record = logging.LogRecord(
                'worker', logging.INFO, '', 0,
                line.rstrip('\r\n'), (), None,
            )
            handler.handle(record)
    finally:
        pipe.close()
        if handler is not None:
            handler.close()



class WorkerManager:
    def __init__(self, store):
        self.store = store
        self.workers = {}
        self.lock = threading.RLock()
        self.user_locks = {}
        self.closing = False

    def user_lock(self, uid):
        with self.lock:
            return self.user_locks.setdefault(uid, threading.RLock())

    def ensure(self, uid):
        from service.users import is_active
        with self.user_lock(uid):
            if self.closing or not is_active(self.store.get(uid)):
                raise RuntimeError('Tài khoản đã bị khóa hoặc hết hạn.')
            worker = self.workers.get(uid)
            if worker and worker['process'].poll() is None:
                (self.store.directory(uid) / 'worker.lease').touch()
                return worker
            directory = self.store.provision(uid)
            ready = directory / 'worker-ready.json'
            if ready.exists():
                # Shut down an orphan from an earlier gateway before creating another bot process.
                try:
                    previous = json.loads(ready.read_text())
                    client = requests.Session()
                    client.trust_env = False
                    try:
                        client.post(f"http://127.0.0.1:{int(previous['port'])}/_internal/shutdown",
                                    headers={'X-Yulee-Worker': previous['secret']}, timeout=10)
                        deadline = time.monotonic() + 12
                        while ready.exists() and time.monotonic() < deadline:
                            time.sleep(0.1)
                        if ready.exists():
                            raise RuntimeError('Worker cũ chưa dừng. Hãy thử lại.')
                    finally:
                        client.close()
                except (requests.ConnectionError, ValueError, KeyError):
                    pass
            ready.unlink(missing_ok=True)
            (directory / 'worker.lease').touch()
            secret = secrets.token_urlsafe(48)
            env = dict(os.environ, YULEESELF_TENANT_DIR=str(directory),
                       YULEESELF_WORKER_SECRET=secret, PYTHONUNBUFFERED='1')
            process = subprocess.Popen(
                [sys.executable, str(self.store.source / 'service/worker.py')],
                cwd=directory, env=env,
                stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                text=True, encoding='utf-8', errors='replace', bufsize=1,
            )
            log_thread = threading.Thread(
                target=collect_worker_logs,
                args=(process.stdout, directory / 'data/worker.log'),
                daemon=True,
            )
            log_thread.start()
            worker = {
                'process': process, 'secret': secret, 'port': None,
                'last_request': time.monotonic(), 'log_thread': log_thread,
            }
            self.workers[uid] = worker
            deadline = time.monotonic() + 15
            while time.monotonic() < deadline:
                if process.poll() is not None:
                    raise RuntimeError('Không khởi động được bot worker. Kiểm tra dependencies và worker.log.')
                if ready.exists():
                    try:
                        info = json.loads(ready.read_text())
                        if info['pid'] == process.pid:
                            worker['port'] = int(info['port'])
                            return worker
                    except (ValueError, KeyError):
                        pass
                time.sleep(0.05)
            self.stop(uid)
            raise RuntimeError('Worker khởi động quá thời gian cho phép.')

    def request(self, uid, method, path, query=b'', payload=None):
        with self.user_lock(uid):
            worker = self.ensure(uid)
            worker['last_request'] = time.monotonic()
            # URL and headers are constructed here, never supplied by the browser.
            url = f"http://127.0.0.1:{worker['port']}/{path}"
            client = requests.Session()
            client.trust_env = False
            try:
                return client.request(method, url, params=query, json=payload,
                                      headers={'X-Yulee-Worker': worker['secret']},
                                      timeout=(3, 120), allow_redirects=False)
            finally:
                client.close()

    def stop(self, uid):
        with self.user_lock(uid):
            worker = self.workers.pop(uid, None)
            if not worker:
                return
            process = worker['process']
            if process.poll() is not None:
                worker['log_thread'].join(timeout=5)
                return
            if worker.get('port'):
                client = requests.Session()
                client.trust_env = False
                try:
                    client.post(f"http://127.0.0.1:{worker['port']}/_internal/shutdown",
                                headers={'X-Yulee-Worker': worker['secret']}, timeout=10)
                except requests.RequestException:
                    pass
                finally:
                    client.close()
            try:
                process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                process.terminate()
                try:
                    process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait()
            worker['log_thread'].join(timeout=5)

    def close(self):
        self.closing = True
        for uid in list(self.workers):
            self.stop(uid)

    def monitor(self):
        from service.users import is_active
        while not self.closing:
            for user in self.store.all():
                if self.closing:
                    break
                if not is_active(user):
                    self.stop(user['id'])
                    continue
                try:
                    path = self.store.directory(user['id']) / 'config/accounts.json'
                    accounts = json.loads(path.read_text()).get('accounts', []) if path.exists() else []
                    uid = user['id']
                    if any(a.get('enabled', True) for a in accounts):
                        self.ensure(uid)
                    else:
                        with self.user_lock(uid):
                            worker = self.workers.get(uid)
                            if worker and time.monotonic() - worker['last_request'] >= 300:
                                self.stop(uid)
                except (RuntimeError, ValueError, OSError):
                    pass
            for uid, worker in list(self.workers.items()):
                if worker['process'].poll() is None:
                    (self.store.directory(uid) / 'worker.lease').touch()
            for _ in range(10):
                if self.closing:
                    return
                time.sleep(0.5)
