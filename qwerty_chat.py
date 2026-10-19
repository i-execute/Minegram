"""Minegram — qwerty bridge: 'q <msg>' → чат MC ('Qwerty' публично / 'qs' приватно)."""
import asyncio
import re

INBOX = "/QwertyWork/Minegram/qwerty_inbox.txt"
LOG = "/QwertyWork/Minegram/server/logs/latest.log"
OWNER_NICK = ".Forget_2796"
PAT_CHAT = re.compile(r"<(\.?[\w\d_]+)>\s+(q[sS]?)[\s:]+(.*)")
PAT_CMD = re.compile(r"<(\.?[\w\d_]+)>\s*/(q[sS]?)[\s:]+(.*)")
_seen = -1


def _init_seen():
    global _seen
    if _seen < 0:
        try:
            with open(LOG, errors="ignore") as f:
                _seen = sum(1 for _ in f)
        except FileNotFoundError:
            _seen = 0


def _tail_new(path, seen):
    try:
        with open(path, errors="ignore") as f:
            return f.readlines()[seen:]
    except FileNotFoundError:
        return []


async def _reply(text, private):
    import mc
    msg = f'{{"text":"{text}","color":"aqua"}}' if not private else (
        f'{{"text":"{text}","color":"dark_gray","italic":true}}')
    try:
        await mc.cmd(f"tellraw @a {msg}")
    except Exception as e:
        with open("/QwertyWork/Minegram/bot.log", "a") as f:
            f.write(f"reply fail: {type(e).__name__} {e}\n")


async def watch_qwerty():
    global _seen
    _init_seen()
    while True:
        await asyncio.sleep(3)
        lines = _tail_new(LOG, _seen)
        if not lines:
            continue
        _seen += len(lines)
        for l in lines:
            m = PAT_CHAT.search(l) or PAT_CMD.search(l)
            if not m:
                continue
            nick, mode, msg = m.groups()
            if nick != OWNER_NICK:
                continue
            private = mode.lower() == "qs"
            with open(INBOX, "a") as f:
                f.write(f"{'[приватно] ' if private else ''}{msg}\n")
            tag = "Qwerty" if not private else "Qwerty (шёпот)"
            await _reply(f"[{tag}] услышал: {msg}", private)
