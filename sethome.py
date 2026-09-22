"""Minegram — /sethome: задаёт группу-дом, создаёт все топики."""
import secrets

from constructor import log, logx, h2, h4, p, rt, concat, emoj, btn_row, page_btn
import i18n
import kernel as K
import resolver as R


# дефолтные анимированные эмодзи (без премиума, как MGIMO TOPIC_EMOJI)
TOPIC_ICONS = {
    "chat": 5417915203100613993,     # 💬 speech bubble
    "backups": 5357315181649076022,  # 📁 folder
    "worlds": 5350367161514732241,   # 🔮 crystal ball
    "logs": 5309965701241379366,     # 🔍 search
    "mclogs": 5350554349074391003,   # 💻 laptop
    "dynmap": 5350424168615649565,   # ☁️ cloud
    "power": 5312016608254762256,    # ⚡ bolt
    "updater": 5312241539987020022,  # 🔥 fire
}

TOPICS = [
    # key, title, icon doc_id
    ("chat",      "Общение",        TOPIC_ICONS["chat"]),
    ("backups",   "Backups",        TOPIC_ICONS["backups"]),
    ("worlds",    "Миры",           TOPIC_ICONS["worlds"]),
    ("logs",      "Logs",           TOPIC_ICONS["logs"]),
    ("mclogs",    "MC Logs",        TOPIC_ICONS["mclogs"]),
    ("dynmap",    "Dynmap",         TOPIC_ICONS["dynmap"]),
    ("power",     "Power",          TOPIC_ICONS["power"]),
    ("updater",   "Updater",        TOPIC_ICONS["updater"]),
]

# приветствия в топики (MGIMO-паттерн: create -> hello rich)
# дефолтные анимированные эмодзи MGIMO-пака для приветствий
DEMO = {"chat": 5417915203100613993, "backups": 5357315181649076022,
        "worlds": 5350367161514732241, "logs": 5309965701241379366,
        "mclogs": 5350554349074391003, "dynmap": 5350424168615649565,
        "power": 5312016608254762256, "updater": 5312241539987020022}

HELLOS = {
    "chat": lambda S: [h2(concat([emoj(DEMO["chat"], "💬"), rt(" " + S.TOPIC_CHAT_HELLO)])),
                       h4(S.TOPIC_CHAT_SUB)],
    "backups": lambda S: [h2(concat([emoj(DEMO["backups"], "📁"), rt(" " + S.TOPIC_BACKUPS_HELLO)])),
                          h4(S.TOPIC_BACKUPS_SUB)],
    "worlds": lambda S: [h2(concat([emoj(DEMO["worlds"], "🔮"), rt(" " + S.TOPIC_WORLDS_HELLO)])),
                         h4(S.TOPIC_WORLDS_SUB)],
    "logs": lambda S: [h2(concat([emoj(DEMO["logs"], "🔍"), rt(" " + S.TOPIC_LOGS_HELLO)])),
                       h4(S.TOPIC_LOGS_SUB)],
    "mclogs": lambda S: [h2(concat([emoj(DEMO["mclogs"], "💻"), rt(" " + S.TOPIC_MCLOGS_HELLO)])),
                         h4(S.TOPIC_MCLOGS_SUB)],
    "dynmap": lambda S: [h2(concat([emoj(DEMO["dynmap"], "☁️"), rt(" " + S.TOPIC_DYNMAP_HELLO)])),
                         h4(S.DYNMAP_HELLO)],
    "power": lambda S: [h2(concat([emoj(DEMO["power"], "⚡"), rt(" " + S.TOPIC_POWER_HELLO)])),
                        h4(S.TOPIC_POWER_SUB)],
    "updater": lambda S: [h2(concat([emoj(DEMO["updater"], "🔥"), rt(" " + S.TOPIC_UPDATER_HELLO)])),
                          h4(S.TOPIC_UPDATER_SUB)],
}


def topic_id_from_update(res):
    """id топика из updates-ответа createForumTopic (MGIMO-паттерн)."""
    if not isinstance(res, dict):
        return None
    if isinstance(res.get("result"), dict):
        res = res["result"]
    for u in res.get("updates", []):
        if isinstance(u, dict) and u.get("_") == "updateNewChannelMessage":
            m = u.get("message", {})
            if m.get("action", {}).get("_") == "messageActionTopicCreate":
                return m.get("id")
    for u in res.get("updates", []):
        if isinstance(u, dict) and u.get("_") == "updateMessageID":
            return u.get("id")
    return None


async def ensure_topic(k, peer, key, title, icon, existing):
    if existing.get(key):
        return existing[key]
    for ic in (icon, None):  # премиум-иконка может дать 403 -> ретрай без неё
        try:
            kw = {"peer": peer, "title": title, "random_id": secrets.randbits(63)}
            if ic:
                kw["icon_emoji_id"] = ic
            res = await k.core.mt.call("messages.createForumTopic", **kw)
            tid = topic_id_from_update(res)
            log(f"[SETHOME] topic {key}={tid} icon={bool(ic)}")
            return tid
        except Exception as e:
            logx(e)
            if ic is None:
                return None


async def handle_sethome(msg):
    k = K.kernel
    group_id = int(msg.chat_id)
    peer = await R.resolve(k.core, group_id)
    k.cfg["backup_group"] = group_id
    topics = dict(k.cfg.get("topics") or {})
    k.save_config()

    made = {}
    S = i18n.S(K.kernel.cfg.get("owner_id"))
    for key, title, icon in TOPICS:
        made[key] = await ensure_topic(k, peer, key, title, icon, topics)
        if made[key] and key in HELLOS:
            try:
                await k.core.mt.call("messages.sendMessage", peer=peer, message="",
                                     rich_message={"_": "inputRichMessage",
                                                   "blocks": HELLOS[key](S)},
                                     random_id=secrets.randbits(63),
                                     reply_to={"_": "inputReplyToMessage",
                                               "reply_to_msg_id": made[key]})
            except Exception as e:
                logx(e)

    k.cfg["topics"] = made
    k.cfg["backup_topic_id"] = made.get("backups")
    k.save_config()

    ok = [t for t, v in made.items() if v]
    if not ok:
        blocks = [h2(S.SETHOME_NO_RIGHTS)]
    else:
        lines = "\n".join(f"• {t}: {'✅' if made.get(kk) else '—'}" for kk, t, _ in TOPICS)
        blocks = [h2(concat([emoj(5229045747130843073, "🏅"), rt(" " + S.SETHOME_SET)])),
                  p(S.SETHOME_TOPICS.format(list=lines))]
    try:
        await k.core.mt.call("messages.sendMessage", peer=peer, message="",
                             rich_message={"_": "inputRichMessage", "blocks": blocks},
                             random_id=secrets.randbits(63),
                             reply_to={"_": "inputReplyToMessage",
                                       "reply_to_msg_id": getattr(msg, "id", None)})
    except Exception as e:
        logx(e)
    log(f"[SETHOME] group={group_id} topics={made}")
