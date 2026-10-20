"""Minegram — Jarvis: авто-ответ на q/qs через LLM API + мгновенный пуш в ТГ."""
import asyncio
import json
import os
import re
import urllib.request

from dotenv import dotenv_values

INBOX = "/QwertyWork/Minegram/qwerty_inbox.txt"
ENV = dotenv_values("/QwertyWork/Minegram/.env")
OWNER_TG = "7610246474"


async def rcon_cmd(cmd):
    import rcon
    return await rcon.rcon(ENV["RCON_HOST"], int(ENV["RCON_PORT"]),
                            ENV["RCON_PASSWORD"], cmd)


def _tg_notify(text):
    try:
        tok = ENV["BOT_TOKEN"]
        url = f"https://api.telegram.org/bot{tok}/sendMessage"
        data = json.dumps({"chat_id": OWNER_TG, "text": text}).encode()
        req = urllib.request.Request(url, data=data,
                                     headers={"Content-Type": "application/json"})
        urllib.request.urlopen(req, timeout=10)
    except Exception:
        pass


def _llm_reply(user_msg):
    sys_prompt = ("Ты Джарвис — ассистент в Minecraft. Владелец пишет из игры. "
                  "Ответь ОДНОЙ короткой фразой по-русски, неформально. "
                  "Не выполняй команды сам — только отвечай текстом.")
    try:
        url = "https://api.deepseek.com/chat/completions"
        key = os.environ.get("DEEPSEEK_API_KEY", "")
        if not key:
            return None
        body = json.dumps({"model": "deepseek-chat",
                           "messages": [{"role": "system", "content": sys_prompt},
                                        {"role": "user", "content": user_msg}],
                           "max_tokens": 100}).encode()
        req = urllib.request.Request(url, data=body, headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {key}"})
        r = json.load(urllib.request.urlopen(req, timeout=20))
        return r["choices"][0]["message"]["content"].strip()
    except Exception:
        return None


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
            reply = _llm_reply(msg) or "Джарвис на связи"
            await rcon_cmd(f"say [Qwerty] {reply}")
            _tg_notify(f"🎮 {nick}: {msg}\n→ {reply}")


_seen = -1
LOG = "/QwertyWork/Minegram/server/logs/latest.log"
OWNER_NICK = ".Forget_2796"
PAT_CHAT = re.compile(r"<(\.?[\w\d_]+)>\s+(q[sS]?)[\s:]+(.*)")
PAT_CMD = re.compile(r"<(\.?[\w\d_]+)>\s*/(q[sS]?)[\s:]+(.*)")


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
