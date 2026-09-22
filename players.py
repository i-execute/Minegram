"""Minegram — players: whitelist/ban/op/op-list через RCON."""
from constructor import (ser, rt, concat, h2, h4, p, emoj,
                         page_btn, btn_row, blockquote, log, logx, EMO)
import i18n
import mc


def _split(raw):
    return [n for n in (raw or "").replace(",", " ").split() if n and ":" not in n]


async def blocks(uid, section="main"):
    S = i18n.S(uid)
    rows = [h2(concat([emoj(EMO["crown"], "👑"), rt(" " + S.PL_MGMT_TITLE)]))]
    if section == "whitelist":
        try:
            wl = _split((await mc.cmd("whitelist list")).split(":", 1)[-1])
        except Exception:
            wl = []
        rows.append(p(S.PM_WL.format(count=len(wl))))
        if wl:
            rows.append(blockquote("\n".join(wl[:50]), ""))
        rows.append(p(S.PM_HINT))
        rows.append(btn_row([
            page_btn(S.PM_WL_ON, "mc:wl_on", emo=(EMO["ok"], "✅")),
            page_btn(S.PM_WL_OFF, "mc:wl_off", emo=(EMO["no"], "❌")),
        ]))
    elif section == "ops":
        try:
            ops = _split((await mc.cmd("oplist")).split(":", 1)[-1])
        except Exception:
            ops = []
        rows.append(p(S.PM_OPS.format(count=len(ops))))
        if ops:
            rows.append(blockquote("\n".join(ops[:50]), ""))
    else:
        rows.append(p(S.PM_MAIN_HINT))
    rows.append(btn_row([
        page_btn(S.PM_BTN_WHITELIST, "mc:pm_wl", emo=(EMO["shield"], "🛡")),
        page_btn(S.PM_BTN_OPS, "mc:pm_ops", emo=(EMO["crown"], "👑")),
    ]))
    rows.append(btn_row([page_btn(S.BTN_BACK_MENU, "mc:menu")]))
    return rows


INPUT_MODE = {}  # uid -> "kick"|"ban"|"pardon"|"op"|"deop"


async def handle(uid, section):
    """Кнопки страницы. Активные действия — через ввод ника (INPUT_MODE)."""
    S = i18n.S(uid)
    if section in ("wl_on", "wl_off"):
        await mc.cmd("whitelist on" if section == "wl_on" else "whitelist off")
    return await blocks(uid, "main")


async def start_input(uid, action):
    INPUT_MODE[uid] = action


async def run_action(uid, nick):
    """RCON-действие с ником. Возвращает текст результата."""
    S = i18n.S(uid)
    act = INPUT_MODE.pop(uid, None)
    if not act:
        return None, None
    cmds = {"kick": f'kick {nick}', "ban": f'ban {nick}',
            "pardon": f'pardon {nick}', "op": f'op {nick}', "deop": f'deop {nick}'}
    try:
        out = await mc.cmd(cmds[act])
    except Exception as e:
        return h2(S.PM_FAIL), str(e)[:300]
    title = {"kick": S.PM_KICKED, "ban": S.PM_BANNED, "pardon": S.PM_PARDONED,
             "op": S.PM_OPPED, "deop": S.PM_DEOPPED}[act]
    return h2(title), (out or "").strip()[:300]


async def action_blocks(uid, action):
    """Страница «введи ник» для конкретного действия."""
    S = i18n.S(uid)
    prompts = {"kick": S.PM_ASK_KICK, "ban": S.PM_ASK_BAN, "pardon": S.PM_ASK_PARDON,
               "op": S.PM_ASK_OP, "deop": S.PM_ASK_DEOP}
    return [h2(concat([emoj(EMO["sword"], "⚔️"), rt(" " + prompts[action])])),
            p(S.PM_SEND_NICK.format(cmd="/" + action)),
            btn_row([page_btn(S.BTN_BACK_MENU, "mc:pm")])]


async def watch_players():
    """Хук: уведы в топик Общение при входе/выходе игроков (поллинг RCON list)."""
    import asyncio
    import kernel as K
    k = K.kernel
    tid = (k.cfg.get("topics") or {}).get("chat")
    if not tid:
        return
    prev = set()
    while True:
        await asyncio.sleep(15)
        cur_list = await mc.players()
        if cur_list is None:
            continue
        cur = set(cur_list)
        joined = cur - prev
        left = prev - cur
        prev = cur
        for nick in joined:
            await _notify(k, tid, nick, True)
        for nick in left:
            await _notify(k, tid, nick, False)


async def _notify(k, tid, nick, joined):
    import resolver as R
    S = i18n.S(k.cfg.get("owner_id"))
    txt = S.PL_JOIN.format(nick=nick) if joined else S.PL_LEAVE.format(nick=nick)
    blocks = [h2(concat([emoj(EMO["cool"], "😎"), rt(" " + txt)]))]
    try:
        peer = await R.resolve(k.core, k.cfg.get("backup_group"))
        await k.core.mt.call("messages.sendMessage", peer=peer, message="",
                             rich_message={"_": "inputRichMessage", "blocks": blocks},
                             random_id=__import__("secrets").randbits(63),
                             reply_to={"_": "inputReplyToMessage", "reply_to_msg_id": tid})
    except Exception as e:
        logx(e)
