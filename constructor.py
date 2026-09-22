from goygram.schema_manager import init_schema
import goygram.ext as rx

init_schema(rx)

import json
import logging
import secrets
import time
from pathlib import Path

BASE = Path(__file__).parent
ENV_PATH = BASE / ".env"
ENT = BASE / "mt_entities.json"
PHOTOS_DIR = BASE / "photos"
PHOTOS_DIR.mkdir(exist_ok=True)

LOG = logging.getLogger("mgimo")
EMO = {
    "server": 5375099322666859339,  # 🖥
    "players": 5453957997418004470,  # 👥
    "gamepad": 5453921696354419743,  # 🕹
    "sword": 5454014806950429357,  # ⚔️
    "shield": 5465154440287757794,  # 🛡
    "disk": 5462956611033117422,  # 📀
    "back": 5253997076169115797,  # 🔙
    "loop": 5226702984204797593,  # 🔄
    "no": 5454350746407419714,  # ❌
    "ok": 5465465194056525619,  # 👍
    "crown": 5229011542011299168,  # 👑
    "fire": 5256047523620995497,  # 🔥
    "deny": 5462882007451185227,  # 🚫
    "money": 5375312095346704820,  # 💰
    "alien": 5226893221191237996,  # 👾
    "box": 5463172695132745432,  # 📦
    "skull": 5463250708918711044,  # 💀
    "heart": 5226829990682707583,  # 💔
    "star": 5226928895189598791,  # ⭐️
    "sun": 5373021138316186413,  # ☀️
    "moon": 5226662903569989373,  # 🌜
    "clock": 5373236586760651455,  # ⏱
    "book": 5454113432284446338,  # ✉️
    "medal": 5229045747130843073,  # 🎖
    "trophy": 5226431245918942763,  # 🏆
    "tool": 5462921117423384478,  # 🛠
    "fish": 5463406036410969564,  # 🎣
    "brain": 5226639745106330551,  # 🧠
    "watch": 5228822494730797152,  # 👁
    "up": 5463122435425448565,  # ⬆️
    "top": 5463071033256848094,  # 🔝
    "quest": 5463139580934892960,  # ❓
    "cool": 5372965329511139384,  # 😎
    "wave": 5462910521739063094,  # 👋
    "point": 5463392464314315076,  # 👉
    "chest": 5463046637842608206,  # 🪙
    "flag": 5373304760776541441,  # 🚩
    "bomb": 5226813248900187912,  # 💣
    "gun": 5454177848203951217,  # 🔫
    "knife": 5373239082136650704,  # 🔪
    "sick": 5463156928307801722,  # 🤕
    "pill": 5463081281048818043,  # 💊
    "temp": 5463054218459884779,  # 🌡
    "dead": 5463274047771000031,  # 😵
    "sleep": 5462990652943904884,  # 😴
    "dizzy": 5463274047771000031,  # 😵
    "angry": 5373261050894370026,  # 😡
    "cry": 5463137996091962323,  # 😭
    "grin": 5463121572137022242,  # 😂
    "shock": 5454182632797521992,  # 😱
    "mage": 5454136337345037322,  # 🧙‍♀️
    "armor": 5454168390685965478,  # 🪖
    "shop": 5226656353744862682,  # 🛒
    "battery": 5454125707300978880,  # 🔋
    "console": 5453921696354419743,  # 🕹
    "world": 5463092727136661235,
    "ninja": 5463345378587849154,
    "handshake": 5463256910851546817,  # 🤝
    "thumb": 5465465194056525619,      # 👍
}


def ser(name, body):
    if isinstance(body, str):
        try:
            body = json.loads(body)
        except Exception:
            pass
    if isinstance(body, dict):
        body = {k: (json.loads(v) if isinstance(v, str) and v.startswith("{") and v.endswith("}") else v)
                for k, v in body.items()}
    return bytes(rx.serialize_constructor(name, body)).hex()


def rt(t):
    return ser("textPlain", {"text": t})


def concat(parts):
    return ser("textConcat", {"texts": parts})


def bold(t):
    return ser("textBold", {"text": rt(t)})


def as_rich(t):
    if isinstance(t, str):
        try:
            raw = bytes.fromhex(t)
            if len(raw) >= 4:
                rx.deserialize_constructor(raw)
                return t
        except Exception:
            pass
    return rt(t)


def h1(text):
    return ser("pageBlockHeading1", {"text": as_rich(text)})


def h2(text):
    return ser("pageBlockHeading2", {"text": as_rich(text)})


def h3(text):
    return ser("pageBlockHeading3", {"text": as_rich(text)})


def h4(text):
    return ser("pageBlockHeading4", {"text": as_rich(text)})


def h5(text):
    return ser("pageBlockHeading5", {"text": as_rich(text)})


def mention(text, uid):
    return ser("textMentionName", {"text": rt(text), "user_id": uid})


def p(text):
    return ser("pageBlockParagraph", {"text": rt(text)})


def emoj(doc_id, fallback):
    return ser("textCustomEmoji", {"document_id": doc_id, "alt": fallback})


def cap(text_hex):
    return ser("pageCaption", {"text": text_hex, "credit": ser("textEmpty", {})})


def page_btn(label, data, style=None, emo=None):
    text = rt(label) if emo is None else concat([emoj(emo[0], emo[1]), rt(" " + label)])
    body = {"type": ser("inlineButtonTypeCallback", {"data": data.encode().hex()}),
            "text": text}
    if style:
        body["style"] = ser("richButtonStyle", {style: True})
    return ser("pageButton", body)


def btn_row(buttons):
    return ser("pageBlockButtonRow", {"align_center": True, "buttons": buttons})


def inline_btn(label, data, style=None, emo=None):
    text = rt(label) if emo is None else concat([emoj(emo[0], emo[1]), rt(" " + label)])
    body = {"type": ser("inlineButtonTypeCallback", {"data": data.encode().hex()}),
            "text": text}
    if style:
        body["style"] = ser("richButtonStyle", {style: True})
    return ser("textButton", body)


def blockquote(text, caption):
    return ser("pageBlockBlockquote", {"collapsed": False,
                                       "text": as_rich(text),
                                       "caption": as_rich(caption)})


def log(msg):
    LOG.info(msg)


def logx(e):
    LOG.exception("EXC %s", e)


def parse_msg_id(res):
    if isinstance(res, dict):
        res = res.get("result", res)
    if isinstance(res, dict) and res.get("id"):
        return res["id"]
    raw_hex = res.get("raw") if isinstance(res, dict) else None
    if not raw_hex:
        return None
    try:
        upd = json.loads(rx.deserialize_constructor(bytes.fromhex(raw_hex)))
    except Exception:
        return None
    obj = deep_find(upd, lambda d: d.get("_") == "updateMessageID")
    return obj.get("id") if obj else None


def media_type_name(media):
    try:
        decoded = media
        if isinstance(media, dict) and isinstance(media.get("raw"), str):
            decoded = json.loads(rx.deserialize_constructor(bytes.fromhex(media["raw"])))
        obj = decoded if isinstance(decoded, dict) else {}
        t = obj.get("_", "?")
        if t == "messageMediaDocument":
            doc = deep_find(obj, lambda o: isinstance(o, dict) and o.get("_") == "document")
            if doc:
                attrs = [a.get("_") for a in doc.get("attributes", []) if isinstance(a, dict)]
                if "documentAttributeSticker" in attrs:
                    stick = next((a for a in doc["attributes"] if a.get("_") == "documentAttributeSticker"), {})
                    return f"sticker alt={stick.get('alt')!r}"
                if "documentAttributeAnimated" in attrs:
                    return "gif/animation"
                if "documentAttributeVideo" in attrs:
                    return "video"
                if "documentAttributeAudio" in attrs:
                    return "audio/voice"
                return f"document:{doc.get('mime_type', '?')}"
        if t == "messageMediaPhoto":
            return "photo"
        return t
    except Exception:
        return "?"


def find_photo(obj):
    if isinstance(obj, dict):
        if obj.get("_") == "photo":
            return obj
        for v in obj.values():
            r = find_photo(v)
            if r:
                return r
    elif isinstance(obj, list):
        for v in obj:
            r = find_photo(v)
            if r:
                return r
    return None


def deep_find(obj, pred):
    if isinstance(obj, dict):
        if pred(obj):
            return obj
        for v in obj.values():
            r = deep_find(v, pred)
            if r is not None:
                return r
    elif isinstance(obj, list):
        for v in obj:
            r = deep_find(v, pred)
            if r is not None:
                return r
    return None


def photo_ref_from_media(media):
    if not isinstance(media, dict):
        return None
    raw = media.get("raw")
    if not raw:
        return None
    try:
        decoded = json.loads(rx.deserialize_constructor(bytes.fromhex(raw)))
    except Exception:
        return None
    ph = find_photo(decoded)
    if not ph:
        return None
    return {"id": ph.get("id"), "access_hash": ph.get("access_hash"),
            "file_reference": ph.get("file_reference", "")}


def media_ref_from_media(media, allow_sticker=True):
    if not isinstance(media, dict):
        return None
    raw = media.get("raw")
    if not raw:
        return None
    try:
        decoded = json.loads(rx.deserialize_constructor(bytes.fromhex(raw)))
    except Exception:
        return None
    sticker = deep_find(decoded, lambda o: isinstance(o, dict) and o.get("_") == "documentAttributeSticker")
    if sticker:
        doc = deep_find(decoded, lambda o: isinstance(o, dict) and o.get("_") == "document")
        if doc:
            return {"kind": "sticker", "id": doc.get("id"), "access_hash": doc.get("access_hash"),
                    "file_reference": doc.get("file_reference", "")}
    if sticker and not allow_sticker:
        return None
    ph = find_photo(decoded)
    if ph:
        return {"kind": "photo", "id": ph.get("id"), "access_hash": ph.get("access_hash"),
                "file_reference": ph.get("file_reference", "")}
    doc = deep_find(decoded, lambda o: isinstance(o, dict) and o.get("_") == "document")
    if doc:
        attrs = [a.get("_") for a in doc.get("attributes", []) if isinstance(a, dict)]
        is_video = "documentAttributeVideo" in attrs and "documentAttributeSticker" not in attrs
        return {"kind": "video" if is_video else "document", "id": doc.get("id"), "access_hash": doc.get("access_hash"),
                "file_reference": doc.get("file_reference", "")}
    return None


def input_media_from_ref(ref):
    if ref["kind"] == "photo":
        return ser("inputMediaPhoto", {"id": ser("inputPhoto", {"id": ref["id"], "access_hash": ref["access_hash"],
                                                                "file_reference": ref["file_reference"]})})
    return ser("inputMediaDocument", {"id": ser("inputDocument", {"id": ref["id"], "access_hash": ref["access_hash"],
                                                                 "file_reference": ref["file_reference"]})})


def photos_vec(photo_refs):
    return [ser("inputPhoto", {"id": p["id"], "access_hash": p["access_hash"],
                              "file_reference": p["file_reference"]})
            for p in photo_refs]


MODULES = {}


def register_module(name, mod):
    MODULES[name] = mod
    log(f"[REG] module {name}")


def load_env():
    import re
    local = BASE / ".env"
    if local.exists():
        env = local.read_text()
    else:
        env = Path(ENV_PATH).read_text()
    api_id = int(re.search(r"TELEGRAM_API_ID=(\d+)", env).group(1))
    api_hash = re.search(r"TELEGRAM_API_HASH=([0-9a-f]+)", env).group(1)
    token = None
    m = re.search(r"BOT_TOKEN=(\S+)", env)
    if m:
        token = m.group(1)
    return api_id, api_hash, token


def load_entities(core):
    if ENT.exists():
        try:
            for uid, ent in json.loads(ENT.read_text()).items():
                if ":" in uid:
                    kind, eid = uid.split(":", 1)
                    core.mt.entities[(kind, int(eid))] = ent
                else:
                    core.mt.entities[("user", int(uid))] = ent
        except Exception as e:
            logx(e)


def save_entities_snapshot(core):
    try:
        data = {}
        for (kind, eid), ent in core.mt.entities.items():
            data[f"{kind}:{eid}"] = ent
        ENT.write_text(json.dumps(data, ensure_ascii=False))
    except Exception as e:
        logx(e)


