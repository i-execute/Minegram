"""Minegram — watch q-сообщений из чата MC → пуш в webhook Qwerty (как Telegram)."""
import asyncio
import hashlib
import hmac
import json
import re
import time
import urllib.request

LOG = "/QwertyWork/Minegram/server/logs/latest.log"
OWNER_NICK = ".Forget_2796"
HOOK_URL = "http://89.125.48.221:8644/webhooks/minegram-chat"
SECRET = b"minegram_jarvis_hook"
PAT_CHAT = re.compile(r"<(\.?[\w\d_]+)>\s+(q[sS]?)[\s:]+(.*)")

_seen = -1


def _init_seen():
    global _seen
    if _seen < 0:
        try:
            with open(LOG, errors="ignore") as f:
                _seen = sum(1 for _ in f)
        except FileNotFoundError:
            _seen = 0


def _tail_new(seen):
    try:
        with open(LOG, errors="ignore") as f:
            lines = f.readlines()
    except FileNotFoundError:
        return []
    if len(lines) < seen:
        _reset(0)
        return lines
    return lines[seen:]


def _reset(n):
    global _seen
    _seen = n


def _push(nick, msg):
    body = json.dumps({"event": "mc.chat", "nick": nick, "msg": msg}).encode()
    sig = hmac.new(SECRET, body, hashlib.sha256).hexdigest()
    req = urllib.request.Request(HOOK_URL, data=body, headers={
        "Content-Type": "application/json",
        "X-Hub-Signature-256": f"sha256={sig}"})
    try:
        urllib.request.urlopen(req, timeout=15)
        return True
    except Exception:
        return False


async def watch():
    global _seen
    _init_seen()
    while True:
        await asyncio.sleep(3)
        lines = _tail_new(_seen)
        if not lines:
            continue
        _seen += len(lines)
        for l in lines:
            m = PAT_CHAT.search(l)
            if not m:
                continue
            nick, _, msg = m.groups()
            if nick != OWNER_NICK:
                continue
            _push(nick, msg)


if __name__ == "__main__":
    asyncio.run(watch())
