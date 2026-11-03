#!/usr/bin/env python3
"""Give service/gateway.py sole ownership of the web server port.

Run once from the YULEESELF project root: python apply_one_port.py
Keeps all other local gateway changes (including backup/delete features).
"""
from pathlib import Path
from datetime import datetime
import ast
import re
import shutil
import sys

ROOT = Path(__file__).resolve().parent
YULEE = ROOT / 'yulee.py'
GATEWAY = ROOT / 'service' / 'gateway.py'


def patched_yulee(source):
    if 'def configure_host():' in source:
        # Remove only the known port configuration function.
        start = source.index('def configure_host():')
        end = source.find('def main():', start)
        if end == -1:
            raise RuntimeError('Cannot locate main() after configure_host() in yulee.py')
        method = source[start:end]
        if 'SERVER_PORT' not in method or "os.environ['PORT']" not in method:
            raise RuntimeError('Unknown configure_host() implementation. Please review yulee.py manually.')
        source = source[:start] + source[end:]
        if source.count('    configure_host()\n') != 1:
            raise RuntimeError('Expected exactly one call to configure_host() in yulee.py')
        source = source.replace('    configure_host()\n', '', 1)
        source = source.replace('    # Import only after setting environment values: gateway.serve() reads PORT.\n', '')
        source = source.replace(
            '"""Start the YULEESELF web gateway, using the port supplied by the host."""',
            '"""Start YULEESELF. Gateway is the single source of host/port settings."""'
        )
    # Do not silently leave behind a second port setting elsewhere in this file.
    if re.search(r'(os\.environ\s*\[\s*[\'"](?:PORT|SERVER_PORT|YULEESELF_PORT)[\'"]\s*\]\s*=)|\b9235\b', source):
        raise RuntimeError('yulee.py still defines a web port; remove it manually before using this patch.')
    if 'from service.gateway import serve' not in source:
        raise RuntimeError('Cannot find the gateway entry point in yulee.py.')
    return source


def patched_gateway(source):
    # Existing version may already be configured this way; do not touch it then.
    intended = "port = int(os.environ.get('SERVER_PORT') or os.environ.get('PORT') or os.environ.get('YULEESELF_PORT') or '9235')"
    if intended in source:
        return source
    pattern = r"(?m)^([ \t]*)port\s*=\s*int\(os\.environ\.get\(['\"]PORT['\"],\s*os\.environ\.get\(['\"]YULEESELF_PORT['\"],\s*['\"]\d+['\"]\)\)\)\s*$"
    found=list(re.finditer(pattern,source))
    if len(found)!=1:
        raise RuntimeError('Cannot identify exactly one existing gateway port declaration. Nothing changed.')
    m=found[0]
    return source[:m.start()] + m.group(1) + intended + source[m.end():]


def main():
    if not YULEE.is_file() or not GATEWAY.is_file():
        print('Run this script in the project root containing yulee.py and service/gateway.py.')
        return 1
    old={YULEE:YULEE.read_text(encoding='utf-8'),GATEWAY:GATEWAY.read_text(encoding='utf-8')}
    try:
        updated={YULEE:patched_yulee(old[YULEE]),GATEWAY:patched_gateway(old[GATEWAY])}
        for path,content in updated.items():
            ast.parse(content,filename=str(path))
    except Exception as exc:
        print(f'Patch refused (no files changed): {exc}')
        return 1
    changed=[p for p in old if old[p]!=updated[p]]
    if not changed:
        print('Both files already use gateway.py as the single port configuration.')
        return 0
    backup = ROOT / 'code_backup' / ('one_port_' + datetime.now().strftime('%Y%m%d_%H%M%S_%f'))
    for path in changed:
        dest=backup/path.relative_to(ROOT)
        dest.parent.mkdir(parents=True,exist_ok=True)
        shutil.copy2(path,dest)
    try:
        for path in changed:
            path.write_text(updated[path],encoding='utf-8')
    except Exception:
        for path in changed:
            shutil.copy2(backup/path.relative_to(ROOT),path)
        raise
    print('Updated: ' + ', '.join(str(p.relative_to(ROOT)) for p in changed))
    print(f'Originals saved: {backup}')
    print('Restart Wispbyte without changing its Bash startup command.')
    return 0

if __name__=='__main__':
    sys.exit(main())
