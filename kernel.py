"""
Minegram — Kernel
Core init, state, rich send/edit (модель MGIMOMedBot)
"""
import asyncio
import json
import logging
import logging.handlers
import os
import secrets
import time
from pathlib import Path

from goygram import GoyGram
from goygram.security import bootstrap_session
from constructor import log, logx
from config import load_config, save_config, get_cfg, C
from resolver import R

SESSION = "minegram_bot"
DRAFT_SHOW = 1.0
BASE = Path(__file__).parent
DB_PATH = BASE / "db.json"


def parse_msg_id(res):
    if isinstance(res, dict):
        res = res.get("result", res)
    if isinstance(res, dict) and res.get("id"):
        return res["id"]
    raw_hex = res.get("raw") if isinstance(res, dict) else None
    if not raw_hex:
        return None
    try:
        import goygram.ext as rx
        upd = json.loads(rx.deserialize_constructor(bytes.fromhex(raw_hex)))
    except Exception:
        return None
    from constructor import deep_find
    obj = deep_find(upd, lambda d: d.get("_") == "updateMessageID")
    return obj.get("id") if obj else None


def load_db():
    if DB_PATH.exists():
        try:
            return json.loads(DB_PATH.read_text())
        except Exception:
            pass
    return {}


class Kernel:
    def __init__(self):
        self.core = None
        self.app = None
        self.db = {}
        self.cfg = None
        self.panels = {}        # uid -> main menu msg_id
        self.console_mode = set()
        self.answered_callbacks = set()

    async def init(self):
        lvl = os.environ.get("BOT_LOG_LEVEL", "DEBUG")
        log(f"=== minegram init pid={os.getpid()} ===")
        api_id, api_hash, token = C.load_env()
        if not token:
            raise SystemExit("BOT_TOKEN не найден в .env")
        self.app = GoyGram(bot_token=token, api_id=api_id, api_hash=api_hash,
                           default_transport="mtproto", session_name=SESSION)
        self.core = self.app.core
        await bootstrap_session(self.core, api_id=api_id, api_hash=api_hash,
                                session_name=SESSION, bot_token=token)
        await self.core.mt.start()
        R.load(self.core)
        try:
            state = await self.core.mt.call("updates.getState", api_id=self.core.api_id)
            pts = state.get("pts", 1) if isinstance(state, dict) else 1
            await self.core.mt.call("updates.getDifference", api_id=self.core.api_id,
                                    pts=max(1, pts - 100), date=int(time.time()) - 7200, qts=0)
            log(f"[INIT] state synced pts={pts}")
        except Exception as e:
            log(f"[INIT] state sync skip: {str(e)[:80]}")
        self.db = load_db()
        self.cfg = get_cfg()
        if self.cfg.get("admins") is None:
            self.cfg["admins"] = set()
        return self

    def persist_db(self):
        tmp = DB_PATH.with_suffix(".tmp")
        tmp.write_text(json.dumps(self.db, ensure_ascii=False, indent=2))
        tmp.replace(DB_PATH)  # atomic

    def save_config(self):
        save_config(self.cfg)

    def is_admin(self, uid):
        return uid == self.cfg.get("owner_id") or uid in self.cfg.get("admins", set())

    async def run(self):
        from handlers import handle_callback, handle_message
        from backups import backup_loop
        from purger import purge_logs

        def configure_logging():
            fmt = logging.Formatter("%(asctime)s | %(levelname)s | %(name)s | %(message)s")
            root = logging.getLogger()
            for handler in list(root.handlers):
                root.removeHandler(handler)
                handler.close()
            fh = logging.handlers.RotatingFileHandler("bot.log", maxBytes=5*1024*1024, backupCount=3)
            fh.setFormatter(fmt)
            sh = logging.StreamHandler()
            sh.setFormatter(fmt)
            root.setLevel(os.environ.get("BOT_LOG_LEVEL", "DEBUG"))
            root.addHandler(fh)
            root.addHandler(sh)

        configure_logging()
        log("=== minegram start ===")
        self.core.cb_hook.append(handle_callback)
        self.core.hook.append(handle_message)
        self.core.update_hook.append(R.on_update_hook)

        async def after_backup():
            configure_logging()  # закрыть handlers ДО unlink
            removed = purge_logs()
            log(f"[BACKUP] logs purged: {len(removed)}")

        backup_task = asyncio.create_task(
            backup_loop(self.core, self.cfg.get("backup_group"), self.cfg,
                        self.save_config, after_backup))
        await asyncio.sleep(0.5)
        log(f"[FLOW] ready owner={self.cfg.get('owner_id')}")
        try:
            import dynmap
            import players
            if (self.cfg.get("topics") or {}).get("dynmap"):
                asyncio.create_task(dynmap.on_server_up())  # свежие ссылки в топики при старте бота
                asyncio.create_task(dynmap.watch_tunnel())  # авто-пост при смене/смерти URL туннеля
                asyncio.create_task(players.watch_players())  # уведы о входе/выходе игроков
        except Exception as e:
            log(f"[INIT] dynmap post skip: {str(e)[:80]}")

        disp_task = asyncio.create_task(self.core.disp.consume())
        try:
            await disp_task
        except asyncio.CancelledError:
            pass
        finally:
            backup_task.cancel()
            await self.core.close()

    # --- rich send/edit ---
    async def send_rich(self, blocks, peer_id, key="main"):
        peer = await R.resolve(self.core, peer_id)
        if not peer:
            return None
        rich = {"_": "inputRichMessage", "blocks": blocks}
        rid = secrets.randbits(63)
        try:
            action = {"_": "inputSendMessageRichMessageDraftAction",
                      "random_id": rid, "rich_message": rich}
            await self.core.mt.call("messages.setTyping", peer=peer, action=action)
            await asyncio.sleep(DRAFT_SHOW)
        except Exception as e:
            log(f"[DRAFT] skip: {str(e)[:80]}")
        try:
            res = await self.core.mt.call("messages.sendMessage", peer=peer, message="",
                                          random_id=rid, rich_message=rich,
                                          no_webpage=True, no_mention=True)
            mid = parse_msg_id(res)
            if key:
                self.panels[key] = mid
            log(f"[SEND] OK key={key} mid={mid}")
            return mid
        except Exception as e:
            logx(e)
            return None

    async def edit_rich(self, blocks, peer_id, msg_id):
        peer = await R.resolve(self.core, peer_id)
        if not peer or not msg_id:
            return False
        rich = {"_": "inputRichMessage", "blocks": blocks}
        try:
            await self.core.mt.call("messages.editRichMessage", peer=peer, id=msg_id,
                                    rich_message=rich)
            return True
        except Exception as e:
            logx(e)
            return False

    async def answer_cb(self, query_id, text=None):
        try:
            await self.core.mt.call("messages.setBotCallbackAnswer",
                                    query_id=query_id, message=text, cache_time=1)
        except Exception as e:
            log(f"[CB-ANS] {str(e)[:80]}")


kernel = Kernel()
