"""Minegram — power: вкл/выкл/рестарт MC-сервера + диагностика состояния."""
import asyncio

from constructor import (ser, rt, concat, h1, h2, h3, h4, h5, p, emoj,
                         page_btn, btn_row, blockquote, log, logx, EMO)
import i18n
import mc
from kernel import kernel


def _svc_state():
    import subprocess
    r = subprocess.run(["systemctl", "is-active", "minegram-mc"],
                       capture_output=True, text=True)
    return r.stdout.strip()


async def status_blocks(uid):
    S = i18n.S(uid)
    state = _svc_state()
    rows = [h2(concat([emoj(EMO["battery"], "🔋"), rt(" " + S.PW_TITLE)]))]
    if state == "active":
        st = await mc.status()
        if st:
            v = st.get("version", {}).get("name", "?")
            pl = st.get("players", {})
            rows.append(p(S.PW_ONLINE.format(version=v,
                                              online=pl.get("online", 0),
                                              max=pl.get("max", 0))))
        else:
            rows.append(p(S.PW_ACTIVE_NO_PING))
        rows.append(p(S.PW_STATE.format(state=state)))
    elif state in ("activating", "reloading", "restarting"):
        rows.append(p(S.PW_STARTING.format(state=state)))
    else:
        rows.append(p(S.PW_OFFLINE.format(state=state)))
    rows.append(btn_row([
        page_btn(S.PW_BTN_ON, "mc:pwon", emo=(EMO["ok"], "✅")),
        page_btn(S.PW_BTN_RESTART, "mc:pwrestart", emo=(EMO["loop"], "🔄")),
    ]))
    rows.append(btn_row([
        page_btn(S.PW_BTN_OFF, "mc:pwoff", emo=(EMO["no"], "⏻")),
        page_btn(S.BTN_BACK_MENU, "mc:menu"),
    ]))
    return rows


async def handle_power(cb, uid, action):
    S = i18n.S(uid)
    if action in ("pwon", "pwrestart", "pwoff"):
        cmd = {"pwon": "start", "pwrestart": "restart", "pwoff": "stop"}[action]
        await kernel.answer_cb(cb.query_id, S.PW_WAITING)
        ok, err = await asyncio.to_thread(mc.mc_service, cmd)
        if not ok:
            blocks = [h2(S.PW_FAIL), p((err or "")[:300]),
                      btn_row([page_btn(S.BTN_BACK_MENU, "mc:menu")])]
            await kernel.edit_rich(blocks, uid, kernel.panels.get(uid))
            return
        if action in ("pwon", "pwrestart"):
            import dynmap
            asyncio.create_task(dynmap.on_server_up())  # ждёт MC + шлёт ссылки в топики, не блокируя
    await kernel.answer_cb(cb.query_id)
    await kernel.edit_rich(await status_blocks(uid), uid, kernel.panels.get(uid))
