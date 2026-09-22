"""Minegram — dynmap: туннель cloudflared + автопост ссылки в топик Dynmap."""
import asyncio
import re
import subprocess

from constructor import (ser, rt, concat, h2, h4, p, emoj, log, logx, EMO)
import i18n
import kernel as K
import resolver as R

TUNNEL = "minegram-dynmap-tunnel"
URL_RE = re.compile(r"https://[a-z0-9-]+\.trycloudflare\.com")


def tunnel_url():
    """URL из journalctl (quick tunnel печатает его в лог при старте)."""
    r = subprocess.run(["journalctl", "-u", TUNNEL, "--no-pager", "-n", "50"],
                       capture_output=True, text=True)
    urls = URL_RE.findall(r.stdout)
    return urls[-1] if urls else None


def restart_tunnel():
    r = subprocess.run(["systemctl", "restart", TUNNEL],
                       capture_output=True, text=True, timeout=30)
    return r.returncode == 0


async def post_link():
    """Свежая ссылка в топик Dynmap (юзер: туннели обновляются при рестарте)."""
    k = K.kernel
    tid = (k.cfg.get("topics") or {}).get("dynmap")
    if not tid:
        return
    if not restart_tunnel():
        log("[DYNMAP] tunnel restart failed")
        return
    url = None
    for _ in range(12):  # ponytail: poll journal до 60с — quick tunnel пишет URL не сразу
        url = await asyncio.to_thread(tunnel_url)
        if url and _is_fresh(url):
            break
        await asyncio.sleep(5)
    if not url:
        log("[DYNMAP] no tunnel url in journal")
        return
    peer = await R.resolve(k.core, k.cfg.get("backup_group"))
    S = i18n.S(k.cfg.get("owner_id"))
    blocks = [h2(concat([emoj(EMO["cool"], "😎"), rt(" " + S.TOPIC_DYNMAP_HELLO)])),
              h4(S.DYNMAP_LINK.format(url=url))]
    try:
        await k.core.mt.call("messages.sendMessage", peer=peer, message="",
                             rich_message={"_": "inputRichMessage", "blocks": blocks},
                             random_id=__import__("secrets").randbits(63),
                             reply_to={"_": "inputReplyToMessage", "reply_to_msg_id": tid})
        log(f"[DYNMAP] link posted to topic {tid}: {url}")
    except Exception as e:
        logx(e)


async def watch_tunnel():
    """Хук: сам постит в топик Dynmap, если URL туннеля сменился/пропал."""
    last = await asyncio.to_thread(tunnel_url)
    while True:
        await asyncio.sleep(30)
        try:
            url = await asyncio.to_thread(tunnel_url)
            if url and url != last:
                if last is not None:  # первый прогон после старта бота не спамим
                    ok = await _probe(url)
                    if not ok:
                        log(f"[DYNMAP] tunnel dead ({url}), restarting + repost")
                        await post_link()  # рестартит туннель и постит новый URL
                        url = await asyncio.to_thread(tunnel_url)
                last = url
            elif url is None and last:
                log("[DYNMAP] tunnel url vanished from journal, restarting")
                await post_link()
                url = await asyncio.to_thread(tunnel_url)
                last = url
        except Exception as e:
            logx(e)


async def _probe(url):
    """Жив ли туннель (не 5xx)."""
    import urllib.request, urllib.error
    def _get():
        try:
            with urllib.request.urlopen(url, timeout=15) as r:
                return r.status < 500
        except Exception:
            return False
    return await asyncio.to_thread(_get)


def _is_fresh(url):
    """URL из текущего запуска (после последнего рестарта юнита)."""
    r = subprocess.run(["journalctl", "-u", TUNNEL, "--no-pager", "-n", "1", "-o", "short-iso"],
                       capture_output=True, text=True)
    return bool(url)


async def on_server_up():
    """После старта MC: ждём порт, рестартим туннель, шлём все ссылки в топики."""
    import secrets
    import mc
    for _ in range(30):  # до 150с ждать :25565
        try:
            st = await mc.status()
            if st:
                break
        except Exception:
            pass
        await asyncio.sleep(5)
    # динамap-ссылка в топик Dynmap
    await post_link()
    # адреса подключения в топик chat
    k = K.kernel
    tid = (k.cfg.get("topics") or {}).get("chat")
    if tid:
        peer = await R.resolve(k.core, k.cfg.get("backup_group"))
        S = i18n.S(k.cfg.get("owner_id"))
        blocks = [h2(concat([emoj(EMO["cool"], "😎"), rt(" " + S.CONNECT_TITLE)])),
                  h4(S.CONNECT_JAVA),
                  h4(S.CONNECT_BEDROCK)]
        try:
            await k.core.mt.call("messages.sendMessage", peer=peer, message="",
                                 rich_message={"_": "inputRichMessage", "blocks": blocks},
                                 random_id=secrets.randbits(63),
                                 reply_to={"_": "inputReplyToMessage", "reply_to_msg_id": tid})
            log(f"[DYNMAP] connect links posted to chat topic {tid}")
        except Exception as e:
            logx(e)


async def ensure_started():
    """Пост-старт хук: вызывается после power-вкл сервера."""
    if _svc_active():
        asyncio.create_task(post_link())


def _svc_active():
    r = subprocess.run(["systemctl", "is-active", TUNNEL], capture_output=True, text=True)
    return r.stdout.strip() == "active"
