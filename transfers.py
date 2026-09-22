"""Minegram — transfers: потоковая загрузка/выгрузка файлов (upload/download с прогрессом в TG)."""
import asyncio
import time

from constructor import log, logx, ser, rt, h2, p, emoj, concat, EMO
import kernel as K


async def _render_loop(state, done, k, peer_id, msg_id, title):
    """Редактирует сообщение прогресса раз в 2с; ошибки глотаем (MGIMO-паттерн)."""
    last = -1
    while not done.is_set():
        try:
            await asyncio.sleep(0.5)
            if done.is_set():
                break
            cur, total, t0 = state["cur"], state["total"], state["t0"]
            pct = int(cur * 100 / total) if total else 0
            if pct == last:
                continue
            last = pct
            speed = cur / (time.time() - t0) if time.time() > t0 else 0
            blocks = [h2(concat([emoj(EMO["loop"], "🔄"), rt(f" {title}")])),
                      p(f"{cur/1048576:.1f} / {total/1048576:.1f} MB ({pct}%, {speed/1048576:.1f} MB/s)")]
            await k.edit_rich(blocks, peer_id, msg_id)
        except asyncio.CancelledError:
            raise
        except Exception:
            pass  # edit-фейлы не роняют передачу
    # финальный кадр 100%
    try:
        cur, total = state["cur"], state["total"] or 1
        blocks = [h2(concat([emoj(EMO["ok"], "✅"), rt(f" {title} — 100%")])),
                  p(f"{cur/1048576:.1f} MB")]
        await k.edit_rich(blocks, peer_id, msg_id)
    except Exception:
        pass


def _make_cb(state):
    def cb(cur, total):
        state["cur"] = cur
        state["total"] = total
    return cb


async def upload(path, peer_id, title=None):
    import strings as S
    title = title or S.TR_UP
    """charged_upload с прогрессом; возвращает dict inputFile (id/parts/name/md5)."""
    k = K.kernel
    state = {"cur": 0, "total": 0, "t0": time.time()}
    done = asyncio.Event()
    msg_id = await k.send_rich([h2(title), p("0%")], peer_id, key=None)
    render = asyncio.create_task(_render_loop(state, done, k, peer_id, msg_id, title))
    try:
        up = await k.core.charged_upload(str(path), progress=_make_cb(state))
        return up
    finally:
        done.set()
        render.cancel()
        try:
            await render
        except asyncio.CancelledError:
            pass


async def download(msg, dest_path):
    """Скачивает документ из msg через goygram download_media с прогрессом в ЛС владельцу."""
    k = K.kernel
    uid = k.cfg["owner_id"]
    state = {"cur": 0, "total": 0, "t0": time.time()}
    done = asyncio.Event()
    import strings as S
    msg_id = await k.send_rich([h2(S.TR_DOWN), p("0%")], uid, key=None)
    render = asyncio.create_task(_render_loop(state, done, k, uid, msg_id, "Скачивание"))
    try:
        await k.core.download_media(msg, str(dest_path), progress=_make_cb(state))
        return dest_path
    finally:
        done.set()
        render.cancel()
        try:
            await render
        except asyncio.CancelledError:
            pass
