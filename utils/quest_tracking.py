"""Read OwO quest/checklist text without depending on component layout."""
import re

HEADERS = {'weekly': 'weekly checklist', 'daily': 'daily checklist', 'quest': 'quest log'}
PROGRESS = re.compile(r'(?<!\d)(\d[\d,]*)\s*/\s*(\d[\d,]*)(?!\d)')


def message_text(data):
    parts = [data.get('content') or '']
    def walk(nodes):
        for node in nodes:
            if node.get('type') == 10:
                parts.append(node.get('content') or '')
            walk(node.get('components') or [])
    walk(data.get('components') or [])
    for embed in data.get('embeds') or []:
        parts.extend([embed.get('title', ''), embed.get('author', {}).get('name', ''), embed.get('description', '')])
        for field in embed.get('fields', []):
            parts.extend([field.get('name', ''), field.get('value', '')])
    return '\n'.join(parts)


def parse_tracking(text):
    kind = next((key for key, header in HEADERS.items() if header in text.lower()), None)
    if kind is None:
        return None
    items, candidate, timer = [], None, None
    for raw in text.splitlines():
        line = re.sub(r'<a?:\w+:\d+>', '', raw)
        line = re.sub(r'[*~`]', '', line).strip()
        if not line:
            continue
        lower = line.lower()
        if 'next quest' in lower or 'checklist resets' in lower:
            timestamp = re.search(r'<t:(\d+)(?::[a-zA-Z])?>', line)
            timer = {'timestamp': int(timestamp.group(1))} if timestamp else re.split(r'next quest\s*(?:in)?\s*:?|(?:daily|weekly) checklist resets\s*', line, flags=re.I)[-1].strip()
            candidate = None
            continue
        if 'reward:' in lower:
            description = re.split(r'reward:', line, flags=re.I)[0].strip()
            description = re.sub(r'^\W*\d+[.)]\s*|^[^\w]+', '', description).strip()
            if description:
                candidate = description
            continue
        if any(marker in lower for marker in ('quest log', 'checklist', 'balance:', 'complete ', 'rewards', 'reward:', 'daily progress', 'weekly progress', 'quests belong')):
            candidate = None
            continue
        match = PROGRESS.search(line)
        title = PROGRESS.sub('', line).strip(' []:|-')
        title = re.sub(r'^\s*(?:\d+[.)]\s*)', '', title)
        title = re.sub(r'^[^\w]+', '', title).strip()
        if match:
            description = title if title and title.lower() != 'progress' else candidate
            if description:
                current, total = (int(value.replace(',', '')) for value in match.groups())
                if total > 0:
                    items.append(dict(description=description, current=current, total=total, completed=current >= total))
            candidate = None
        elif title and re.search(r'[a-zA-Z]', title):
            candidate = title
    return kind, items, timer


def belongs_to_user(text, user_id, names):
    header = next((line for line in text.splitlines() if any(h in line.lower() for h in HEADERS.values())), '')
    mentions = re.findall(r'<@!?(\d+)>', header)
    if mentions:
        return str(user_id) in mentions
    header = re.sub(r'[*~`]', '', header).casefold()
    return any(name and re.search(r'(?<!\w)' + re.escape(str(name).casefold()) + r"(?:'s|’s)?(?!\w)", header) for name in names)


def tracking_images(data):
    """Use current-message Discord media URLs; never guess an attachment URL."""
    from urllib.parse import urlparse
    images = []
    def walk(nodes):
        for node in nodes or []:
            if node.get('type') == 12:
                for item in node.get('items', []):
                    media = item.get('media') or {}
                    url = media.get('proxy_url') or media.get('url') or ''
                    parsed = urlparse(url)
                    if parsed.scheme == 'https' and parsed.hostname in ('media.discordapp.net', 'cdn.discordapp.com'):
                        if url not in images:
                            images.append(url)
            walk(node.get('components'))
    walk(data.get('components'))
    return images
