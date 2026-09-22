import json
import time
from pathlib import Path
import os
from dotenv import load_dotenv

from constructor import log, logx

# Load .env from project root
load_dotenv(Path(__file__).parent / ".env")

CONFIG_PATH = Path(__file__).parent / "config.json"

class C:
    @staticmethod
    def load_env():
        api_id = int(os.environ.get("TELEGRAM_API_ID", 0))
        api_hash = os.environ.get("TELEGRAM_API_HASH", "")
        token = os.environ.get("BOT_TOKEN", "")
        return api_id, api_hash, token

CFG = None

_CFG_MTIME = [0.0]

def get_cfg():
    global CFG
    try:
        m = CONFIG_PATH.stat().st_mtime
        if CFG is None or m != _CFG_MTIME[0]:
            CFG = load_config()
            _CFG_MTIME[0] = m
    except Exception:
        CFG = CFG or load_config()
    return CFG

def load_config():
    default = {"owner_id": 0, "admins": [], "feedback_group": 0, "banned": [], "topics": {}}
    try:
        default["owner_id"] = int(os.environ.get("OWNER_ID", 0) or 0)
    except ValueError:
        pass
    try:
        if CONFIG_PATH.exists():
            cfg = json.loads(CONFIG_PATH.read_text())
            default.update(cfg)
    except Exception as e:
        logx(e)
    default["admins"] = set(default.get("admins", []))
    return default


def save_config(cfg):
    try:
        data = dict(cfg)
        data["admins"] = sorted(data["admins"])
        CONFIG_PATH.write_text(json.dumps(data, ensure_ascii=False, indent=2))
        log(f"[CFG] saved {data}")
    except Exception as e:
        logx(e)
