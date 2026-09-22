"""Minegram — Backups: world zips + TG topic (модель MGIMOMedBot)."""
import asyncio
import json
import secrets
import time
import zipfile
from pathlib import Path

from constructor import log, logx, ser, rt, h1, h2, h4, blockquote
import strings as S
import mc

BASE = Path(__file__).parent
BACKUP_HOUR = 4
KEEP_LOCAL = 3


def make_backup():
    stamp = time.strftime("%Y%m%d-%H%M")
    zpath = BASE / f"mc-{stamp}.zip"
    try:
        with zipfile.ZipFile(zpath, "w", zipfile.ZIP_DEFLATED) as z:
            for wdir in mc.worlds():
                for f in mc.MC_DIR.joinpath(wdir).rglob("*"):
                    if f.is_file() and "session.lock" not in f.name:
                        z.write(f, f"{wdir}/{f.relative_to(mc.MC_DIR.joinpath(wdir))}")
            props = mc.MC_DIR / "server.properties"
            if props.exists():
                z.write(props, "server.properties")
        log(f"[BACKUP] {zpath.name} ({zpath.stat().st_size} bytes)")
        return zpath
    except Exception as e:
        logx(e)
        return None


async def seconds_until_backup():
    now = time.localtime()
    target = time.mktime((now.tm_year, now.tm_mon, now.tm_mday, BACKUP_HOUR, 0, 0, 0, 0, -1))
    if time.time() >= target:
        target += 86400
    return max(60.0, target - time.time())


async def ensure_backup_topic(core, peer, cached_id):
    if cached_id:
        return cached_id
    try:
        res = await core.mt.call("messages.createForumTopic", peer=peer,
                                 title=S.TOPIC_BACKUPS_TITLE,
                                 icon_emoji_id=S.topic_emoji("folder"),
                                 random_id=secrets.randbits(63))
        tid = res.get("id") if isinstance(res, dict) else None
        if not tid and isinstance(res, dict):
            for v in [res.get("result", {})]:
                tid = v.get("id") if isinstance(v, dict) else None
        log(f"[BACKUP] topic id={tid}")
        return tid
    except Exception as e:
        logx(e)
        return None


async def send_backup_rich(core, peer, topic_id, zpath):
    ts = time.strftime("%d.%m.%Y %H:%M")
    up = await core.charged_upload(str(zpath))
    media_res = await core.mt.call("messages.uploadMedia", peer=peer,
        media={"_": "inputMediaUploadedDocument",
               "file": {"_": "inputFile", "id": up["id"], "parts": up["parts"],
                        "name": up["name"], "md5_checksum": up["md5"]},
               "mime_type": "application/zip",
               "attributes": [{"_": "documentAttributeFilename",
                               "file_name": zpath.name}]})
    doc = media_res.get("document") or (media_res.get("result", {}) or {}).get("document")
    if not doc:
        raise RuntimeError(f"uploadMedia no doc: {json.dumps(media_res)[:200]}")
    rich = ser("inputRichMessage", {
        "blocks": [
            h1(f"Бэкап миров {ts}"),
            ser("pageBlockDocument", {"document_id": doc["id"],
                "caption": ser("pageCaption", {"text": rt(zpath.name), "credit": rt("")})}),
        ],
        "documents": [ser("inputDocument", {"id": doc["id"], "access_hash": doc["access_hash"],
                                            "file_reference": doc.get("file_reference", "")})],
    })
    await core.mt.call("messages.sendMessage", peer=peer,
                       reply_to={"_": "inputReplyToMessage", "reply_to_msg_id": topic_id},
                       message="", rich_message=rich,
                       random_id=secrets.randbits(63))


def prune_local():
    zips = sorted(BASE.glob("mc-*.zip"))
    for old in zips[:-KEEP_LOCAL]:
        old.unlink(missing_ok=True)


async def backup_loop(core, group_id, cfg, persist=None, after_backup=None):
    topic_id = cfg.get("backup_topic_id")
    while True:
        try:
            wait = await seconds_until_backup()
            log(f"[BACKUP] next in {int(wait//60)} min")
            await asyncio.sleep(wait)
            zpath = await asyncio.to_thread(make_backup)
            gid = cfg.get("backup_group") or group_id
            if not zpath or not gid:
                prune_local()
                continue
            peer = await core.mt.resolve_peer(gid)
            if topic_id is None:
                topic_id = await ensure_backup_topic(core, peer, cfg.get("backup_topic_id"))
                if topic_id:
                    cfg["backup_topic_id"] = topic_id
                    if persist:
                        persist()
            if not topic_id:
                prune_local()
                continue
            try:
                await send_backup_rich(core, peer, topic_id, zpath)
                log("[BACKUP] rich sent")
                zpath.unlink(missing_ok=True)
            except Exception as e:
                logx(e)
                log("[BACKUP] rich failed, keep local zip")
            prune_local()
            if after_backup:
                await after_backup()
        except asyncio.CancelledError:
            return
        except Exception as e:
            logx(e)
            await asyncio.sleep(3600)
