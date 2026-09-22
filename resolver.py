import json
from pathlib import Path

from constructor import log, logx

CACHE = Path(__file__).parent / "mt_entities.json"

class _R:
    @staticmethod
    def load(core):
        if CACHE.exists():
            try:
                for key, ent in json.loads(CACHE.read_text()).items():
                    kind, eid = key.split(":", 1)
                    core.mt.entities[(kind, int(eid))] = ent
                log(f"[RES] loaded {len(core.mt.entities)} entities")
            except Exception as e:
                logx(e)

    @staticmethod
    def snapshot(core):
        try:
            data = {f"{k[0]}:{k[1]}": v for k, v in core.mt.entities.items()}
            CACHE.write_text(json.dumps(data, ensure_ascii=False))
            log(f"[RES] cached {len(data)} entities")
        except Exception as e:
            logx(e)

    @staticmethod
    async def resolve(core, chat_id):
        try:
            return await core.mt.resolve_peer(chat_id)
        except Exception as e:
            logx(e)
            return None

    @staticmethod
    def display_name(core, uid):
        ent = core.mt.entities.get(("user", int(uid))) or {}
        return " ".join(x for x in [ent.get("first_name"), ent.get("last_name")] if x) or "user{uid}".format(uid=uid)

    @staticmethod
    def username(core, uid):
        ent = core.mt.entities.get(("user", int(uid))) or {}
        return ent.get("username") or ""

    @staticmethod
    async def on_update_hook(upd):
        # Called by goygram update_hook with single argument
        pass  # Snapshot logic removed — R.snapshot() not needed


R = _R  # класс
resolve = _R.resolve
load = _R.load
snapshot = _R.snapshot
