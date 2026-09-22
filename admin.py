"""Minegram — admin: админы/бан-лист бота/язык (owner-only)."""
from constructor import (ser, rt, concat, h2, h4, p, emoj,
                         page_btn, btn_row, blockquote, log, logx, EMO)
import i18n
from kernel import kernel as k

INPUT_MODE = {}  # uid -> "add_admin"|"del_admin"|"ban"|"unban"|"lang"


def _cfg():
    return k.cfg


async def blocks(uid, section="main"):
    S = i18n.S(uid)
    cfg = _cfg()
    rows = [h2(concat([emoj(EMO["crown"], "👑"), rt(" " + S.ADM_TITLE)]))]
    if section == "admins":
        admins = sorted(cfg.get("admins", []))
        rows.append(p(S.ADM_ADMINS.format(count=len(admins))))
        if admins:
            rows.append(blockquote("\n".join(str(a) for a in admins[:30]), ""))
    elif section == "banned":
        banned = sorted(cfg.get("banned", []))
        rows.append(p(S.ADM_BANNED.format(count=len(banned))))
        if banned:
            rows.append(blockquote("\n".join(str(b) for b in banned[:30]), ""))
    elif section == "lang":
        lang = i18n.detect_lang(uid)
        rows.append(p(S.ADM_LANG_CUR.format(lang=lang)))
        rows.append(btn_row([
            page_btn("EN", "mc:lang:en", emo=(EMO["flag"], "🚩")),
            page_btn("RU", "mc:lang:ru", emo=(EMO["flag"], "🚩")),
        ]))
        rows.append(btn_row([
            page_btn("ZH 中文", "mc:lang:zh", emo=(EMO["flag"], "🚩")),
        ]))
    else:
        rows.append(p(S.ADM_HINT))
    rows.append(btn_row([
        page_btn(S.ADM_BTN_ADMINS, "mc:adm_admins", emo=(EMO["crown"], "👑")),
        page_btn(S.ADM_BTN_BANNED, "mc:adm_banned", emo=(EMO["deny"], "🚫")),
    ]))
    rows.append(btn_row([
        page_btn(S.ADM_BTN_LANG, "mc:adm_lang", emo=(EMO["book"], "✉️")),
    ]))
    rows.append(btn_row([page_btn(S.BTN_BACK_MENU, "mc:menu")]))
    return rows


async def action_blocks(uid, action):
    """Страница «отправь id»."""
    S = i18n.S(uid)
    prompts = {"add_admin": S.ADM_ASK_ADD, "del_admin": S.ADM_ASK_DEL,
               "ban": S.ADM_ASK_BAN, "unban": S.ADM_ASK_UNBAN}
    return [h2(concat([emoj(EMO["quest"], "❓"), rt(" " + prompts[action])])),
            p(S.ADM_SEND_ID.format(cmd="/" + action)),
            btn_row([page_btn(S.BTN_BACK_MENU, "mc:adm")])]


async def start_input(uid, action):
    INPUT_MODE[uid] = action


async def set_lang(uid, lang):
    i18n.set_lang(uid, lang)


async def run_action(uid, text):
    """Ввод id/номера из INPUT_MODE. Возвращает (title, out)."""
    S = i18n.S(uid)
    act = INPUT_MODE.pop(uid, None)
    if not act:
        return None, None
    cfg = _cfg()
    try:
        target = int(text.split()[0])
    except ValueError:
        return h2(S.ADM_BAD_ID), None
    if target == cfg.get("owner_id") and act in ("del_admin", "ban"):
        return h2(S.ADM_OWNER_PROTECTED), None
    admins = cfg.setdefault("admins", set())
    banned = cfg.setdefault("banned", [])
    if act == "add_admin":
        admins.add(target)
        banned = [b for b in banned if b != target]
    elif act == "del_admin":
        admins.discard(target)
    elif act == "ban":
        if target not in banned:
            banned.append(target)
        admins.discard(target)
    elif act == "unban":
        cfg["banned"] = [b for b in banned if b != target]
    cfg["banned"] = banned
    k.save_config()
    title = {"add_admin": S.ADM_ADDED, "del_admin": S.ADM_REMOVED,
            "ban": S.ADM_BANNED, "unban": S.ADM_UNBANNED}[act]
    return h2(title), str(target)
