"""Minegram — Worlds: список миров, бэкап, конвертация Chunker (Bedrock<->Java)."""
import asyncio
import json
import re
import shutil
import subprocess
import secrets
import time
from pathlib import Path

from constructor import log, logx, ser, rt, concat, h1, h2, h4, p, emoj, blockquote, page_btn, btn_row, EMO
import strings as S
import mc
import kernel as K

BASE = Path(__file__).parent
CHUNKER_JAR = BASE / "chunker-cli.jar"
TMP = BASE / "tmp_conv"
FORMAT_ID_RE = re.compile(r"(?<![A-Z_])(JAVA|BEDROCK)((?:_R?\d+){1,4})(?![_\dR])")
PER_PAGE = 6


def chunker_ok():
    return CHUNKER_JAR.is_file()


def chunker_version():
    v = K.kernel.db.get("chunker_version")
    return v or ("installed" if chunker_ok() else "not installed")


async def chunker_formats():
    """Парсит версии из stderr chunker (TTL-кеш 10 мин)."""
    if _FMT_CACHE[0] and time.time() - _FMT_CACHE[1] < 600:
        return _FMT_CACHE[0], None
    proc = await asyncio.create_subprocess_exec(
        "java", "-jar", str(CHUNKER_JAR), "-f", "INVALID", "-i", "/tmp", "-o", "/tmp",
        stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
    try:
        out, err = await asyncio.wait_for(proc.communicate(), timeout=30)
    except asyncio.TimeoutError:
        proc.kill()
        await proc.wait()
        return None, "chunker timeout"
    combined = (out or b"").decode(errors="replace") + "\n" + (err or b"").decode(errors="replace")
    found = {}
    for m in FORMAT_ID_RE.finditer(combined):
        found[m.group(1) + m.group(2)] = m.group(0)
    if not found:
        return None, "no versions parsed"
    def key(k):
        nums = [n[1:] if n.startswith("R") else n for n in k.split("_")[1:]]
        return tuple(int(n) for n in nums)
    java = sorted([(k, v) for k, v in found.items() if k.startswith("JAVA")], key=lambda kv: key(kv[0]), reverse=True)
    bedrock = sorted([(k, v) for k, v in found.items() if k.startswith("BEDROCK")], key=lambda kv: key(kv[0]), reverse=True)
    res = {"java": java, "bedrock": bedrock}
    _FMT_CACHE[0] = res
    _FMT_CACHE[1] = time.time()
    return res, None


def fmt_label(ver_key):
    prefix, digits = ver_key.split("_", 1)
    nums = [n[1:] if n.startswith("R") else n for n in digits.split("_")]
    return ("Java " if prefix == "JAVA" else "Bedrock ") + ".".join(nums)


async def convert(world_dir, ver_key, out_dir):
    """Chunker CLI конвертация. Возвращает (rc, stderr)."""
    proc = await asyncio.create_subprocess_exec(
        "java", "-Xmx1536M", "-jar", str(CHUNKER_JAR),
        "-i", str(world_dir), "-f", ver_key, "-o", str(out_dir),
        stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
    try:
        _, err = await asyncio.wait_for(proc.communicate(), timeout=600)
    except asyncio.TimeoutError:
        proc.kill()
        await proc.wait()
        return -1, b"timeout"
    return proc.returncode, err


def worlds_blocks():
    ws = mc.worlds()
    rows = [h2(concat([emoj(EMO["world"], "🔮"), rt(" " + S.WORLDS_TITLE)]))]
    if ws:
        rows.append(p("\n".join("• " + w for w in ws)))
    else:
        rows.append(p(S.WORLDS_NONE))
    if chunker_ok():
        rows.append(btn_row([page_btn(S.BTN_CONVERT, "mc:conv", emo=(EMO["loop"], "🔄"))]))
    rows.append(btn_row([page_btn(S.BTN_BACK_MENU, "mc:menu")]))
    return rows


# --- Конвертация: сессии uid -> stage ---
CONV_SESSIONS = {}  # uid -> {"stage": ..., "dir": ..., "page": int, "world": str, "ts": float}
_FMT_CACHE = [None, 0.0]  # [formats, ts] — ponytail: TTL-кеш вместо парсинга CLI на каждый клик

def _conv_gc():
    now = time.time()
    stale = [u for u, s in CONV_SESSIONS.items() if now - s.get("ts", 0) > 1800]
    for u in stale:
        CONV_SESSIONS.pop(u, None)


async def handle_conv(cb, uid, page):
    k = K.kernel
    data = page  # "conv", "conv:java", "conv:bedrock", "conv:page:N", "conv:run:VERKEY"
    if data == "conv":
        # выбор мира
        ws = mc.worlds()
        if not ws:
            await k.answer_cb(cb.query_id, S.WORLDS_NONE)
            return
        rows = [h2(S.CONV_TITLE), p(S.CONV_PICK)]
        for w in ws:
            rows.append(btn_row([page_btn(w, f"mc:conv:world:{w}", emo=(EMO["world"], "🔮"))]))
        rows.append(btn_row([page_btn(S.BTN_BACK_MENU, "mc:menu")]))
        await k.answer_cb(cb.query_id)
        await k.edit_rich(rows, uid, k.panels.get(uid))
        return

    if data.startswith("conv:world:"):
        wname = data.split(":", 2)[2]
        CONV_SESSIONS[uid] = {"stage": "direction", "world": wname, "page": 0, "ts": time.time()}
        rows = [h2(f"Мир: {wname}"), p(S.CONV_DIR),
                btn_row([page_btn(S.CONV_TO_JAVA, "mc:conv:dir:java", emo=(EMO["cool"], "😎"))]),
                btn_row([page_btn(S.CONV_TO_BEDROCK, "mc:conv:dir:bedrock", emo=(EMO["alien"], "👾"))]),
                btn_row([page_btn(S.BTN_BACK_MENU, "mc:menu")])]
        await k.answer_cb(cb.query_id)
        await k.edit_rich(rows, uid, k.panels.get(uid))
        return

    if data.startswith("conv:dir:"):
        direction = data.split(":")[2]
        s = CONV_SESSIONS.get(uid)
        if not s:
            await k.answer_cb(cb.query_id, S.CONV_EXPIRED)
            return
        s["dir"] = direction
        s["page"] = 0
        await k.answer_cb(cb.query_id)
        await render_versions(uid, s)
        return

    if data.startswith("conv:page:"):
        pno = int(data.split(":")[2])
        s = CONV_SESSIONS.get(uid)
        if not s:
            await k.answer_cb(cb.query_id, S.CONV_EXPIRED)
            return
        s["page"] = pno
        await k.answer_cb(cb.query_id)
        await render_versions(uid, s)
        return

    if data.startswith("conv:run:"):
        ver_key = data.split(":", 2)[2]
        s = CONV_SESSIONS.pop(uid, None)
        if not s:
            await k.answer_cb(cb.query_id, S.CONV_EXPIRED)
            return
        await k.answer_cb(cb.query_id)
        await run_conversion(uid, s, ver_key)
        return


async def render_versions(uid, s):
    k = K.kernel
    fmts, err = await chunker_formats()
    if err:
        await k.edit_rich([h2(S.CB_ERR), p(err), btn_row([page_btn(S.BTN_BACK_MENU, "mc:menu")])],
                          uid, k.panels.get(uid))
        return
    vers = fmts[s["dir"]]
    total = max(1, (len(vers) + PER_PAGE - 1) // PER_PAGE)
    pno = max(0, min(s["page"], total - 1))
    chunk = vers[pno * PER_PAGE:(pno + 1) * PER_PAGE]
    dlabel = "Java" if s["dir"] == "java" else "Bedrock"
    rows = [h2(f"{s['world']} → {dlabel}"), p(S.CONV_PICK_VER)]
    for vk, _ in chunk:
        rows.append(btn_row([page_btn(fmt_label(vk), f"mc:conv:run:{vk}")]))
    nav = []
    if pno > 0:
        nav.append(page_btn("◀", f"mc:conv:page:{pno-1}"))
    nav.append(page_btn(f"{pno+1}/{total}", "mc:conv"))
    if pno < total - 1:
        nav.append(page_btn("▶", f"mc:conv:page:{pno+1}"))
    rows.append(btn_row(nav))
    rows.append(btn_row([page_btn(S.BTN_BACK_MENU, "mc:menu")]))
    await k.edit_rich(rows, uid, k.panels.get(uid))


async def run_conversion(uid, s, ver_key):
    k = K.kernel
    wdir = mc.MC_DIR / s["world"]
    out = TMP / f"{uid}_{int(time.time())}_{secrets.randbits(20)}"
    out.mkdir(parents=True, exist_ok=True)
    await k.send_rich([h2(S.CONV_RUNNING), p(f"{s['world']} → {fmt_label(ver_key)}")], uid, key=None)
    rc, err = await convert(wdir, ver_key, out)
    if rc != 0:
        await k.send_rich([h2(S.CONV_FAIL),
                           blockquote((err or b"?").decode(errors="replace")[:500], ""),
                           btn_row([page_btn(S.BTN_BACK_MENU, "mc:menu")])], uid, key=None)
        shutil.rmtree(out, ignore_errors=True)
        return
    # zip результата
    zpath = out.with_suffix(".zip")
    import zipfile

    def _zip():
        with zipfile.ZipFile(zpath, "w", zipfile.ZIP_DEFLATED) as z:
            for f in out.rglob("*"):
                if f.is_file():
                    z.write(f, f.relative_to(out))

    await asyncio.to_thread(_zip)
    shutil.rmtree(out, ignore_errors=True)
    # отправить файл в ЛС
    try:
        import transfers
        peer = await __import__("resolver").R.resolve(k.core, uid)
        up = await transfers.upload(zpath, uid)
        res = await k.core.mt.call("messages.uploadMedia", peer=peer,
            media={"_": "inputMediaUploadedDocument",
                   "file": {"_": "inputFile", "id": up["id"], "parts": up["parts"],
                            "name": up["name"], "md5_checksum": up["md5"]},
                   "mime_type": "application/zip",
                   "attributes": [{"_": "documentAttributeFilename",
                                   "file_name": zpath.name}]})
        doc = res.get("document") or (res.get("result", {}) or {}).get("document")
        rich = ser("inputRichMessage", {
            "blocks": [
                h2(S.CONV_DONE.format(ver=fmt_label(ver_key))),
                ser("pageBlockDocument", {"document_id": doc["id"],
                    "caption": ser("pageCaption", {"text": rt(zpath.name), "credit": rt("")})}),
            ],
            "documents": [ser("inputDocument", {"id": doc["id"], "access_hash": doc["access_hash"],
                                                "file_reference": doc.get("file_reference", "")})],
        })
        await k.core.mt.call("messages.sendMessage", peer=peer, message="",
                             rich_message=rich, random_id=secrets.randbits(63))
    except Exception as e:
        from constructor import logx
        logx(e)
        await k.send_rich([h2(S.CB_OK), p(f"{zpath}"), p(str(e)[:200])], uid, key=None)
    zpath.unlink(missing_ok=True)
