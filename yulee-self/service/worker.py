"""Private tenant runtime. Never bind this API to a public interface."""
from pathlib import Path
import asyncio
import json
import os
import signal
import sys
import threading
import time

SOURCE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SOURCE))


def main():
    tenant = Path(os.environ['YULEESELF_TENANT_DIR']).resolve()
    if not os.environ.get('YULEESELF_WORKER_SECRET'):
        raise RuntimeError('Missing worker authentication')
    os.chdir(tenant)
    from flask import jsonify
    from werkzeug.serving import make_server
    import core.state as state
    from dashboard.app import app
    from utils import history_tracker, proxy_manager

    from service.accounts import ensure_ids
    configured = proxy_manager.load_accounts()
    if ensure_ids(configured):
        proxy_manager.save_accounts(configured)
    history_tracker.init_db()
    state.load_account_stats()
    history_tracker.start_session()
    loop = asyncio.new_event_loop()
    thread = threading.Thread(target=loop.run_forever, daemon=True)
    thread.start()
    state.runtime_status = {}

    async def start_bots():
        if os.environ.get('YULEESELF_TEST_NO_BOTS') == '1':
            return
        for account in proxy_manager.load_accounts():
            if not account.get('enabled', True):
                continue
            key = account.get('config_id', account.get('name', ''))
            state.runtime_status[key] = 'Đang kết nối'
            try:
                from core.bot import YuleeBot
                url, auth, label = proxy_manager.resolve_account_proxy(account)
                bot = YuleeBot(token=account['token'], channels=account['channels'],
                              proxy_url=url, proxy_auth=auth, proxy_label=label)
                bot.config_id = key
                state.bot_instances.append(bot)

                async def run(bot, key):
                    try:
                        await bot.run_bot()
                    except Exception:
                        # Raw exceptions can include credentials or request headers.
                        state.runtime_status[key] = 'Không kết nối được. Kiểm tra token, channel và proxy.'
                        bot.is_ready = False
                    finally:
                        await bot.close()
                        if bot.session and not bot.session.closed:
                            await bot.session.close()
                asyncio.create_task(run(bot, key))
            except Exception:
                state.runtime_status[key] = 'Không khởi tạo được. Kiểm tra dependencies, token và proxy.'
            await asyncio.sleep(0.5)

    async def shutdown_bots():
        for bot in list(state.bot_instances):
            bot.active = False
            await bot.close()
            if bot.session and not bot.session.closed:
                await bot.session.close()
        current = asyncio.current_task()
        tasks = [task for task in asyncio.all_tasks() if task is not current]
        for task in tasks:
            task.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)

    server = make_server('127.0.0.1', 0, app, threaded=False)
    stopped = threading.Event()

    def stop():
        if stopped.is_set():
            return
        stopped.set()
        server.shutdown()

    @app.route('/_internal/shutdown', methods=['POST'])
    def shutdown():
        threading.Thread(target=stop, daemon=True).start()
        return jsonify(success=True)

    def signal_stop(*_):
        threading.Thread(target=stop, daemon=True).start()

    signal.signal(signal.SIGTERM, signal_stop)
    signal.signal(signal.SIGINT, signal_stop)
    def lease_watchdog():
        lease = tenant / 'worker.lease'
        while not stopped.wait(5):
            if not lease.exists() or time.time() - lease.stat().st_mtime > 45:
                stop()
                return

    threading.Thread(target=lease_watchdog, daemon=True).start()
    asyncio.run_coroutine_threadsafe(start_bots(), loop)
    ready = tenant / 'worker-ready.json'
    temporary = ready.with_suffix('.tmp')
    temporary.write_text(json.dumps({'pid': os.getpid(), 'port': server.server_port, 'secret': os.environ['YULEESELF_WORKER_SECRET']}))
    temporary.chmod(0o600)
    temporary.replace(ready)
    try:
        server.serve_forever()
    finally:
        try:
            asyncio.run_coroutine_threadsafe(shutdown_bots(), loop).result(timeout=8)
        finally:
            state.save_account_stats()
            history_tracker.end_session()
            loop.call_soon_threadsafe(loop.stop)
            server.server_close()
            ready.unlink(missing_ok=True)


if __name__ == '__main__':
    main()
