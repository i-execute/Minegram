"""
Minegram — Handlers: callback router + message router (owner-only)
"""
import asyncio

from constructor import (ser, rt, concat, h1, h2, h3, p, emoj, page_btn, btn_row,
                         blockquote, log, logx, EMO)
import i18n
from i18n import EN as S
import resolver as R
import mc
from kernel import kernel


def is_allowed(uid):
    return kernel.is_admin(uid) and uid not in kernel.cfg.get("banned", [])


def menu_blocks():
    return [
        h2(concat([emoj(EMO["server"], "🖥"), rt(" " + S.MENU_TITLE)])),
        p(S.MENU_SUB),
        btn_row([
            page_btn(S.BTN_STATUS, "mc:status", emo=(EMO["loop"], "🔄")),
            page_btn(S.BTN_PLAYERS, "mc:players", emo=(EMO["players"], "👥")),
        ]),
        btn_row([
            page_btn(S.BTN_CONSOLE, "mc:console", emo=(EMO["console"], "🕹")),
            page_btn(S.BTN_WORLDS, "mc:worlds", emo=(EMO["world"], "🔮")),
        ]),
        btn_row([
            page_btn(i18n.S().PL_MGMT_TITLE, "mc:pm", emo=(EMO["sword"], "⚔️")),
            page_btn(i18n.S().ADM_TITLE, "mc:adm", emo=(EMO["crown"], "👑")),
        ]),
        btn_row([
            page_btn(S.BTN_BACKUPS, "mc:backups", emo=(EMO["disk"], "💿")),
            page_btn(S.BTN_UPDATER, "mc:upd", emo=(EMO["loop"], "🔄")),
        ]),
        btn_row([
            page_btn(i18n.S().PW_TITLE, "mc:power", emo=(EMO["battery"], "🔋")),
            page_btn(i18n.S().BTN_LOGS, "mc:logs_mc", emo=(EMO["ninja"], "🙈")),
        ]),
        btn_row([
            page_btn(i18n.S().DYNMAP_TITLE, "mc:dynmap", emo=(EMO["cool"], "😎")),
        ]),
    ]


async def status_blocks():
    st = await mc.status()
    if not st:
        return [h2(S.ST_TITLE), p(S.ST_OFFLINE),
                btn_row([page_btn(S.BTN_BACK_MENU, "mc:menu")])]
    ver = st.get("version", {}).get("name", "?")
    desc = st.get("description", {})
    if isinstance(desc, dict):
        desc = desc.get("text", "")
    players = st.get("players", {})
    online, mx = players.get("online", 0), players.get("max", 0)
    lines = [
        h2(S.ST_TITLE),
        p(f"{S.ST_ONLINE}\n{S.ST_VERSION}: {ver}\nS.ST_PLAYERS.format(online=online, max=mx)+"),
    ]
    t = await mc.tps()
    if t:
        lines.append(p(f"{S.ST_TPS}: {' / '.join(t)}"))
    lines.append(btn_row([
        page_btn(S.BTN_REFRESH, "mc:status", emo=(EMO["loop"], "🔄")),
        page_btn(S.BTN_BACK_MENU, "mc:menu"),
    ]))
    return lines


async def players_blocks():
    pl = await mc.players()
    if pl is None:
        return [h2(S.PL_TITLE), p(S.ST_OFFLINE), btn_row([page_btn(S.BTN_BACK_MENU, "mc:menu")])]
    if not pl:
        return [h2(S.PL_TITLE), p(S.PL_NONE), btn_row([page_btn(S.BTN_BACK_MENU, "mc:menu")])]
    rows = [h2(S.PL_TITLE), p(S.PL_LIST.format(count=len(pl)))]
    rows.append(p("\n".join("• " + n for n in pl[:40])))
    rows.append(btn_row([page_btn(S.BTN_BACK_MENU, "mc:menu")]))
    return rows


def console_blocks():
    return [
        h2(S.CON_TITLE),
        p(S.CON_HINT),
        btn_row([page_btn(S.BTN_BACK_MENU, "mc:menu")]),
    ]


def worlds_blocks():
    import worlds as W
    return W.worlds_blocks()


def backups_blocks():
    import i18n as _i18n
    from pathlib import Path
    S = _i18n.EN
    zips = sorted(Path(__file__).parent.glob("mc-*.zip"), key=lambda f: f.stat().st_mtime, reverse=True)
    rows = [h2(S.BK_TITLE)]
    if zips:
        lines = "\n".join(f"{f.name} ({f.stat().st_size // 1024 // 1024} MB)" for f in zips[:15])
        rows.append(p(lines))
    else:
        rows.append(p(S.BK_NONE))
    rows.append(btn_row([page_btn(S.BTN_BACK_MENU, "mc:menu")]))
    return rows


async def dynmap_blocks():
    import dynmap as D
    import i18n
    S = i18n.S()
    url = await asyncio.to_thread(D.tunnel_url)
    rows = [h2(concat([emoj(EMO["cool"], "😎"), rt(" " + S.DYNMAP_TITLE)]))]
    if url:
        rows.append(p(S.DYNMAP_URL.format(url=url)))
    else:
        rows.append(p(S.DYNMAP_OFFLINE))
    rows.append(btn_row([
        page_btn(S.BTN_REFRESH, "mc:dynmap", emo=(EMO["loop"], "🔄")),
        page_btn(S.BTN_BACK_MENU, "mc:menu"),
    ]))
    return rows


async def power_blocks(uid=0):
    import power as PW
    return await PW.status_blocks(uid)


def upd_blocks():
    import updater as U
    return U.status_blocks()


PAGES = {
    "menu": menu_blocks,
    "status": status_blocks,
    "players": players_blocks,
    "console": console_blocks,
    "worlds": worlds_blocks,
    "backups": backups_blocks,
    "upd": upd_blocks,
    "power": power_blocks,
    "dynmap": dynmap_blocks,
}


async def show_page(uid, page, edit=True):
    b = PAGES[page](uid=uid) if page == "power" else PAGES[page]()
    blocks = await b if asyncio.iscoroutine(b) else b
    mid = kernel.panels.get(uid)
    if edit and mid and await kernel.edit_rich(blocks, uid, mid):
        return
    await kernel.send_rich(blocks, uid, key=uid)


async def handle_callback(cb):
    data = cb.data
    uid = cb.from_id
    log(f"[CB] data={data!r} uid={uid}")
    if not is_allowed(uid):
        await kernel.answer_cb(cb.query_id, S.CB_DENY)
        return
    if not data.startswith("mc:"):
        return
    page = data[3:]
    if page.startswith("conv"):
        import worlds as W
        await W.handle_conv(cb, uid, page)
        return
    if page.startswith("upd:"):
        import updater as U
        await U.handle_upd(cb, uid, page.split(":", 1)[1])
        return
    if page.startswith("adm") or page.startswith("lang"):
        import admin as A
        await kernel.answer_cb(cb.query_id)
        if page.startswith("lang"):
            await A.set_lang(uid, page.split(":")[-1])
            blocks = await A.blocks(uid, "lang")
        else:
            sub = page[4:] if len(page) > 4 else ""
            sub = sub.lstrip("_") if not sub else sub
            if sub in ("add_admin", "del_admin", "ban", "unban"):
                await A.start_input(uid, sub)
                blocks = await A.action_blocks(uid, sub)
            else:
                blocks = await A.blocks(uid, sub or "main")
        await kernel.edit_rich(blocks, uid, kernel.panels.get(uid))
        return
    if page.startswith("pm"):
        import players as PM
        await kernel.answer_cb(cb.query_id)
        sub = (page[2:].lstrip("_")) if len(page) > 2 else ""
        if sub in ("kick", "ban", "pardon", "op", "deop"):
            await PM.start_input(uid, sub)
            blocks = await PM.action_blocks(uid, sub)
        else:
            blocks = await PM.blocks(uid, sub.replace("pm_", "") or "main")
        await kernel.edit_rich(blocks, uid, kernel.panels.get(uid))
        return
    if page.startswith("logs"):
        import logs as L
        await kernel.answer_cb(cb.query_id)
        await kernel.edit_rich(await L.logs_blocks(uid, page.split("_")[-1]), uid, kernel.panels.get(uid))
        return
    if page.startswith("pw"):
        import power as PW
        await PW.handle_power(cb, uid, page)
        return
    if page == "console":
        kernel.console_mode.add(uid)
    elif page == "menu":
        kernel.console_mode.discard(uid)
    await kernel.answer_cb(cb.query_id)
    await show_page(uid, page)


async def handle_message(msg):
    uid = getattr(msg, "from_id", None) or (msg if isinstance(msg, dict) else {}).get("from_id")
    log(f"[MSG] uid={uid} console_mode={uid in kernel.console_mode if uid else '?'}")
    if not uid or not is_allowed(uid):
        return
    text = (getattr(msg, "text", None) or
            (msg.get("text") if isinstance(msg, dict) else "") or "").strip()
    if not text:
        return
    import admin as A
    if uid == kernel.cfg.get("owner_id") and uid in A.INPUT_MODE:
        t, out = await A.run_action(uid, text)
        if t:
            await kernel.send_rich([t, p(out or ""),
                                    btn_row([page_btn(i18n.S(uid).BTN_BACK_MENU, "mc:adm")])], uid, key=None)
            return
    import players as PM
    if uid in PM.INPUT_MODE:
        nick = text.split()[0]
        t, out = await PM.run_action(uid, nick)
        if t:
            await kernel.send_rich([t, p(out or ""),
                                    btn_row([page_btn(i18n.S(uid).BTN_BACK_MENU, "mc:pm")])], uid, key=None)
            return
    if uid in kernel.console_mode:
        if text.startswith("/"):
            page = text[1:].split("@")[0].lower()
            if page in PAGES:
                kernel.console_mode.discard(uid)
                await show_page(uid, page)
                return
        try:
            out = await mc.cmd(text)
            await kernel.send_rich([
                h2(S.CON_SENT),
                blockquote(out or S.CON_EMPTY, ""),
                btn_row([page_btn(S.BTN_BACK_MENU, "mc:menu")]),
            ], uid, key=None)
        except Exception as e:
            await kernel.send_rich([
                h2(S.CON_ERR),
                p(str(e)[:300]),
                btn_row([page_btn(S.BTN_BACK_MENU, "mc:menu")]),
            ], uid, key=None)
        return
    if text == "/start" or text == "/menu":
        await show_page(uid, "menu", edit=False)
        return
    if text == "/sethome" and uid == kernel.cfg["owner_id"]:
        import sethome
        await sethome.handle_sethome(msg)
        return
    if text == "/backup":
        import backups as BK
        zpath = await asyncio.to_thread(BK.make_backup)
        if zpath and not kernel.cfg.get("backup_topic_id"):
            from pathlib import Path
            Path(zpath).unlink(missing_ok=True)
        if zpath and kernel.cfg.get("backup_topic_id"):
            peer = await R.resolve(kernel.core, uid)
            await BK.send_backup_rich(kernel.core, peer,
                                      kernel.cfg["backup_topic_id"], zpath)
        return
