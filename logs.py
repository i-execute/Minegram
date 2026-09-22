"""Minegram — logs: хвост MC-лога и лога бота, страницы в риче."""
import subprocess
from pathlib import Path

from constructor import (ser, rt, concat, h1, h2, h3, h4, h5, p, emoj,
                         page_btn, btn_row, blockquote, log, logx, EMO)
import i18n

MC_LOG = Path(__file__).parent / "server" / "logs" / "latest.log"
BOT_LOG = Path(__file__).parent / "bot.log"


def tail(path, n=30):
    try:
        r = subprocess.run(["tail", "-n", str(n), str(path)],
                           capture_output=True, text=True, timeout=10)
        return r.stdout.strip()
    except Exception:
        return None


async def logs_blocks(uid, kind="mc"):
    S = i18n.S(uid)
    path = MC_LOG if kind == "mc" else BOT_LOG
    rows = [h2(concat([emoj(EMO["server"] if kind == "mc" else EMO["ninja"],
                            "🖥" if kind == "mc" else "🙈"),
                       rt(" " + (S.LOGS_MC_TITLE if kind == "mc" else S.LOGS_BOT_TITLE))]))]
    import asyncio
    data = await asyncio.to_thread(tail, path, 30)
    rows.append(blockquote(data or S.LOGS_EMPTY, ""))
    rows.append(btn_row([
        page_btn(S.BTN_REFRESH, f"mc:logs_{kind}", emo=(EMO["loop"], "🔄")),
        page_btn(S.BTN_BACK_MENU, "mc:menu"),
    ]))
    return rows
