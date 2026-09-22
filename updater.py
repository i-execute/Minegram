"""Minegram — Updater: обновление Chunker CLI / cloudflared / dynmap, логи в топик Updater."""
import asyncio
import json
import subprocess
from pathlib import Path

from constructor import log, logx, h2, p, rt, concat, emoj, btn_row, page_btn, EMO
import strings as S
import kernel as K
import resolver as R

BASE = Path(__file__).parent
CHUNKER_JAR = BASE / "chunker-cli.jar"
CF_BIN = Path("/usr/local/bin/cloudflared")

SOURCES = [
    # key, repo, getter(tag)->url, dest, версия сейчас
    ("chunker", "HiveGamesOSS/Chunker",
     lambda tag, arch: next(
         (a["browser_download_url"] for a in _rel_assets("HiveGamesOSS/Chunker", tag)
          if a["name"].startswith("chunker-cli") and a["name"].endswith(".jar")), None),
     CHUNKER_JAR,
     lambda: K.kernel.db.get("chunker_version") or ("installed" if CHUNKER_JAR.is_file() else "not installed")),
    ("cloudflared", "cloudflare/cloudflared",
     lambda tag, arch: f"https://github.com/cloudflare/cloudflared/releases/download/{tag}/cloudflared-linux-{arch}",
     CF_BIN,
     lambda: _ver("/usr/local/bin/cloudflared --version")),
    ("dynmap", "webbukkit/dynmap",
     lambda tag, arch: next(
         (a["browser_download_url"] for a in _rel_assets("webbukkit/dynmap", tag)
          if a["name"].endswith("-spigot.jar")), None),
     BASE / "server/plugins/dynmap.jar",
     lambda: _ver("unzip -p server/plugins/dynmap.jar META-INF/MANIFEST.MF 2>/dev/null | grep -i implementation", cwd=BASE)),
]


def _ver(cmd, cwd=None):
    try:
        out = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=15, cwd=cwd).stdout
        return out.strip()[:60] or "installed"
    except Exception:
        return "not installed"


async def gh_latest(repo):
    proc = await asyncio.create_subprocess_exec(
        "curl", "-s", f"https://api.github.com/repos/{repo}/releases/latest",
        stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
    out, _ = await proc.communicate()
    return json.loads(out).get("tag_name")


def _rel_assets_sync(repo, tag):
    import urllib.request
    with urllib.request.urlopen(f"https://api.github.com/repos/{repo}/releases/tags/{tag}", timeout=15) as r:
        return json.load(r).get("assets", [])


def _rel_assets(repo, tag):
    return _rel_assets_sync(repo, tag)


async def notify(text_blocks):
    k = K.kernel
    tid = (k.cfg.get("topics") or {}).get("updater")
    grp = k.cfg.get("backup_group")
    if not (tid and grp):
        return
    try:
        peer = await R.resolve(k.core, int(grp))
        await k.core.mt.call("messages.sendMessage", peer=peer, message="",
                             rich_message={"_": "inputRichMessage", "blocks": text_blocks},
                             random_id=secrets.randbits(63),
                             reply_to={"_": "inputReplyToMessage", "reply_to_top_id": tid})
    except Exception as e:
        logx(e)


async def status_blocks():
    rows = [h2(concat([emoj(EMO["loop"], "🔄"), rt(" " + S.UPD_TITLE)]))]
    for key, repo, _, dest, ver_fn in SOURCES:
        try:
            cur = await asyncio.to_thread(ver_fn) if dest.is_file() else "not installed"
        except Exception:
            cur = "?"
        rows.append(p(f"{key}: {cur}"))
    rows.append(btn_row([page_btn(S.BTN_CHECK_UPD, "mc:upd:check", emo=(EMO["quest"], "❓"))]))
    rows.append(btn_row([page_btn(S.BTN_BACK_MENU, "mc:menu")]))
    return rows


async def handle_upd(cb, uid, action):
    k = K.kernel
    if action == "check":
        await k.answer_cb(cb.query_id, "Проверяю...")
        rows = [h2(concat([emoj(EMO["loop"], "🔄"), rt(" Обновления")]))]
        for key, repo, getter, dest, _ in SOURCES:
            try:
                tag = await gh_latest(repo)
                rows.append(p(f"{key}: latest = {tag}"))
            except Exception as e:
                rows.append(p(f"{key}: {str(e)[:80]}"))
        rows.append(btn_row([page_btn(S.BTN_UPD_ALL, "mc:upd:all", emo=(EMO["fire"], "🔥"))]))
        rows.append(btn_row([page_btn(S.BTN_BACK_MENU, "mc:menu")]))
        await k.edit_rich(rows, uid, k.panels.get(uid))
        return
    if action == "all":
        await k.answer_cb(cb.query_id, "Обновляю...")
        for key, repo, getter, dest, _ in SOURCES:
            try:
                tag = await gh_latest(repo)
                arch = (await asyncio.to_thread(subprocess.run, ["dpkg", "--print-architecture"], capture_output=True, text=True)).stdout.strip() or "amd64"
                url = await asyncio.to_thread(getter, tag, arch)
                if not url:
                    continue
                proc = await asyncio.create_subprocess_exec(
                    "curl", "-sL", url, "-o", str(dest))
                await proc.wait()
                if dest == CF_BIN:
                    await asyncio.create_subprocess_exec("chmod", "+x", str(dest)).wait()
                if key == "chunker":
                    k.db["chunker_version"] = tag
                    k.persist_db()
                await notify([h2(S.UPD_TITLE), p(S.UPD_TO.format(name=key, tag=tag))])
            except Exception as e:
                logx(e)
                await notify([h2(S.UPD_TITLE), p(S.UPD_FAIL.format(name=key, err=str(e)[:100]))])
        await k.edit_rich(await status_blocks(), uid, k.panels.get(uid))
        return
