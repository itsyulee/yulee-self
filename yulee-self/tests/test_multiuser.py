import json
import time
from pathlib import Path

import pytest

from service.gateway import create_app
from service.users import UserStore


@pytest.fixture
def system(tmp_path, monkeypatch):
    monkeypatch.setenv('YULEESELF_TEST_NO_BOTS', '1')
    monkeypatch.setattr(UserStore, 'migrate_admin', lambda self: None)
    app = create_app(tmp_path / 'service')
    app.config['TESTING'] = True
    store = app.extensions['user_store']
    admin = store.create('admin', 'admin-password', role='admin')
    alice = store.create('alice', 'alice-password')
    bob = store.create('bob', 'bob-password')
    yield app, store, admin, alice, bob
    app.extensions['worker_manager'].close()


def login(app, name, password):
    client = app.test_client()
    response = client.post('/login', json={'username': name, 'password': password})
    assert response.status_code == 200, response.data
    csrf = client.get('/api/me').json['csrf_token']
    return client, {'X-CSRF-Token': csrf}


def test_process_isolation_accounts_proxies_settings_history(system):
    app, store, admin, alice, bob = system
    a, ah = login(app, 'alice', 'alice-password')
    b, bh = login(app, 'bob', 'bob-password')
    admin_client, _ = login(app, 'admin', 'admin-password')
    assert a.get('/').status_code == 200
    assert 'Quản lý người dùng'.encode() not in a.get('/').data
    assert 'Quản lý người dùng'.encode() in admin_client.get('/').data
    assert a.get('/api/accounts/config').json == {'accounts': []}
    assert b.get('/api/accounts/config').json == {'accounts': []}
    imported = a.post('/api/proxies/bulk', headers=ah, json={'text': 'socks5://proxy.example:1080'})
    assert imported.status_code == 200, imported.data
    proxy_id = imported.json['proxies'][0]['id']
    payload = {'accounts': [{'name': 'Alice Discord', 'token': 'alice-token-should-not-be-returned',
                             'channels': ['123456789'], 'proxy_id': proxy_id, 'enabled': False}]}
    response = a.post('/api/accounts/config', headers=ah, json=payload)
    assert response.status_code == 200, response.data
    saved = a.get('/api/accounts/config').json['accounts'][0]
    assert 'token' not in saved
    assert saved['config_id']
    assert b.get('/api/accounts/config').json['accounts'] == []
    assert b.get('/api/accounts').json['accounts'] == []
    assert admin_client.get('/api/accounts').json['accounts'] == []
    assert b.get('/api/proxies').json['proxies'] == []
    # An edited account keeps its saved token without sending it to the browser.
    saved['name'] = 'Renamed'
    assert a.post('/api/accounts/config', headers=ah, json={'accounts': [saved]}).status_code == 200
    account_file = store.directory(alice['id']) / 'config/accounts.json'
    assert json.loads(account_file.read_text())['accounts'][0]['token'] == payload['accounts'][0]['token']
    # Foreign stable IDs and foreign proxy IDs cannot be used by Bob.
    assert b.post('/api/accounts/config', headers=bh, json={'accounts': [saved]}).status_code == 400
    injected = dict(payload['accounts'][0], name='Bob')
    assert b.post('/api/accounts/config', headers=bh, json={'accounts': [injected]}).status_code == 400
    assert a.post('/api/settings?all=true', headers=ah, json={'private_marker': 'alice'}).status_code == 200
    assert a.get('/api/settings').json == {'private_marker': 'alice'}
    assert 'private_marker' not in b.get('/api/settings').json
    assert a.get('/api/settings?id=../../auth').status_code == 400
    assert b.get('/api/stats?id=123456789').status_code == 404
    assert a.get('/api/history').json != []
    assert b.get('/api/history').json == []
    assert b.get('/api/captcha/pending').json == {'pending': []}
    manager = app.extensions['worker_manager']
    aw, bw = manager.ensure(alice['id']), manager.ensure(bob['id'])
    assert aw['process'].pid != bw['process'].pid
    import requests
    assert requests.get(f"http://127.0.0.1:{aw['port']}/api/accounts", timeout=3).status_code == 403
    assert requests.get(f"http://127.0.0.1:{aw['port']}/api/accounts", headers={'X-Yulee-Worker': bw['secret']}, timeout=3).status_code == 403
    assert b.get('/api/history/analytics').status_code == 200


def test_admin_password_revocation_and_expiry(system):
    app, store, admin, alice, bob = system
    adm, hdr = login(app, 'admin', 'admin-password')
    a, ah = login(app, 'alice', 'alice-password')
    old_session, _ = login(app, 'alice', 'alice-password')
    assert a.get('/api/admin/users').status_code == 403
    assert a.post('/api/admin/users', headers=ah, json={'username': 'intruder', 'password': 'password123'}).status_code == 403
    response = adm.post('/api/admin/users', headers=hdr, json={'username': 'customer', 'password': 'customer-password'})
    assert response.status_code == 201
    assert response.json['user']['role'] == 'user'
    assert 'password_hash' not in adm.get('/api/admin/users').get_data(as_text=True)
    assert a.post('/api/me/password', headers=ah, json={'current_password': 'wrong', 'new_password': 'new-password'}).status_code == 400
    response = a.post('/api/me/password', headers=ah, json={'current_password': 'alice-password', 'new_password': 'new-password'})
    assert response.status_code == 200
    assert old_session.get('/api/me').status_code == 401
    assert a.get('/api/me').status_code == 200
    fresh, _ = login(app, 'alice', 'new-password')
    assert fresh.get('/api/accounts/config').status_code == 200
    manager = app.extensions['worker_manager']
    process = manager.ensure(alice['id'])['process']
    assert adm.patch('/api/admin/users/' + alice['id'], headers=hdr, json={'enabled': False}).status_code == 200
    assert process.poll() is not None
    assert fresh.get('/api/me').status_code == 401
    assert adm.patch('/api/admin/users/' + bob['id'], headers=hdr, json={'expires_at': time.time() - 1}).status_code == 200
    assert app.test_client().post('/login', json={'username': 'bob', 'password': 'bob-password'}).status_code == 401
    assert adm.patch('/api/admin/users/' + admin['id'], headers=hdr, json={'enabled': False}).status_code == 400


def test_csrf_and_login_limit(system):
    app, store, *_ = system
    a, ah = login(app, 'alice', 'alice-password')
    assert a.post('/api/settings', json={}).status_code == 403
    assert a.post('/api/settings', headers={**ah, 'Origin': 'https://evil.example'}, json={}).status_code == 403
    assert app.test_client().get('/api/debug_status').status_code == 401
    c = app.test_client()
    for _ in range(5):
        assert c.post('/login', json={'username': 'alice', 'password': 'wrong'}).status_code == 401
    assert c.post('/login', json={'username': 'alice', 'password': 'alice-password'}).status_code == 401


def test_auto_proxy_assignment():
    from service.accounts import prepare_accounts
    proxies = [{'id': 'one', 'status': 'ok'}, {'id': 'two', 'status': 'ok'}]
    accounts = [{'name': str(i), 'token': 'test-token-' + str(i), 'channels': ['123'], 'proxy_id': '__auto__'} for i in range(2)]
    saved = prepare_accounts(accounts, [], proxies)
    assert [a['proxy_id'] for a in saved] == ['one', 'two']
    with pytest.raises(ValueError):
        prepare_accounts(accounts, [], proxies[:1])


def test_legacy_migration_once_and_empty_new_user(tmp_path):
    source = tmp_path / 'source'
    (source / 'config').mkdir(parents=True)
    (source / 'data').mkdir()
    (source / 'defaults').mkdir()
    (source / 'config/auth.json').write_text(json.dumps({'username': 'oldadmin', 'password': 'old-password'}))
    (source / 'config/accounts.json').write_text(json.dumps({'accounts': [{'name': 'private', 'token': 'private-secret'}]}))
    (source / 'config/settings.json').write_text(json.dumps({'secret': 'admin-only'}))
    (source / 'defaults/settings.json').write_text(json.dumps({'core': {}}))
    (source / 'data/stats.json').write_text('{"legacy": 42}')
    store = UserStore(tmp_path / 'service', source)
    store.migrate_admin()
    store.migrate_admin()
    assert len(store.all()) == 1
    old = store.find('oldadmin')
    assert old['role'] == 'admin'
    assert 'old-password' not in old['password_hash']
    assert json.loads((store.directory(old['id']) / 'data/stats.json').read_text()) == {'legacy': 42}
    new = store.create('newuser', 'new-password')
    assert json.loads((store.directory(new['id']) / 'config/accounts.json').read_text()) == {'accounts': []}
    assert json.loads((store.directory(new['id']) / 'config/settings.json').read_text()) == {'core': {}}
