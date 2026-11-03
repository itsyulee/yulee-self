"""Validate private Discord accounts without returning full saved tokens."""
import re
import uuid


def prepare_accounts(incoming, existing, proxies):
    if not isinstance(incoming, list) or len(incoming) > 100:
        raise ValueError('Danh sách tài khoản không hợp lệ (tối đa 100).')
    old = {a['config_id']: a for a in existing}
    proxy_ids = {p['id'] for p in proxies if p.get('enabled', True)}
    reserved = {a.get('proxy_id') for a in incoming if isinstance(a, dict) and a.get('proxy_id') != '__auto__'}
    seen_ids, seen_tokens, result = set(), set(), []
    for account in incoming:
        if not isinstance(account, dict):
            raise ValueError('Tài khoản không hợp lệ.')
        cid = account.get('config_id')
        if cid and cid not in old:
            raise ValueError('Tài khoản không thuộc danh sách của bạn. Hãy tải lại trang.')
        cid = cid or uuid.uuid4().hex
        previous = old.get(cid, {})
        token = account.get('token') or previous.get('token')
        name = account.get('name', '')
        channels = account.get('channels', [])
        if not isinstance(name, str) or not 1 <= len(name.strip()) <= 80:
            raise ValueError('Tên tài khoản phải có từ 1 đến 80 ký tự.')
        if not isinstance(token, str) or not 10 <= len(token.strip()) <= 512:
            raise ValueError('Cần nhập token cho tài khoản mới.')
        token = token.strip()
        if not isinstance(channels, list) or not channels or any(
                not re.fullmatch(r'[0-9]{1,22}', str(ch)) for ch in channels):
            raise ValueError('Cần ít nhất một Channel ID hợp lệ.')
        if cid in seen_ids or token in seen_tokens:
            raise ValueError('Danh sách chứa tài khoản/token trùng lặp.')
        pid = account.get('proxy_id') or None
        if pid == '__auto__':
            pid = next((p['id'] for p in proxies if p['id'] in proxy_ids and p['id'] not in reserved and p.get('status') == 'ok'), None)
            if pid is None:
                raise ValueError('Chưa có proxy trống đã Test OK. Thêm/test proxy hoặc chọn Direct.')
            reserved.add(pid)
        if pid is not None and pid not in proxy_ids:
            raise ValueError('Proxy không tồn tại hoặc đang bị tắt trong tài khoản của bạn.')
        enabled = account.get('enabled', True)
        if not isinstance(enabled, bool):
            raise ValueError('Enabled phải là true/false.')
        result.append(dict(config_id=cid, name=name.strip(), token=token,
                           channels=[str(ch) for ch in channels], enabled=enabled, proxy_id=pid))
        seen_ids.add(cid)
        seen_tokens.add(token)
    return result


def ensure_ids(accounts):
    changed = False
    for account in accounts:
        if not account.get('config_id'):
            account['config_id'] = uuid.uuid4().hex
            changed = True
    return changed


def public_accounts(accounts, statuses, bots):
    online = {getattr(bot, 'config_id', '') for bot in bots if bot.is_ready}
    output = []
    for account in accounts:
        item = {k: v for k, v in account.items() if k != 'token'}
        item['token_masked'] = '••••••' + account.get('token', '')[-4:]
        item['runtime_status'] = ('Đã tắt' if not account.get('enabled', True) else
                                  'Đang chạy' if account['config_id'] in online else
                                  statuses.get(account['config_id'], 'Đang kết nối'))
        output.append(item)
    return output
