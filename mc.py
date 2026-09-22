"""Minegram — MC bridge: RCON + ping + systemd control."""
import asyncio
import os
import subprocess
import time
from pathlib import Path

from dotenv import load_dotenv
from rcon import rcon, mcping

load_dotenv(Path(__file__).parent / ".env")

RCON_HOST = os.environ.get("RCON_HOST", "127.0.0.1")
RCON_PORT = int(os.environ.get("RCON_PORT", "25575"))
RCON_PASSWORD = os.environ.get("RCON_PASSWORD", "minegram_rcon")
MC_HOST = os.environ.get("MC_HOST", "127.0.0.1")
MC_PORT = int(os.environ.get("MC_PORT", "25565"))
MC_DIR = Path(__file__).parent / os.environ.get("MC_DIR", "server")


async def cmd(command):
    """RCON command -> response text."""
    return await rcon(RCON_HOST, RCON_PORT, RCON_PASSWORD, command)


async def status():
    """Server list ping -> dict, or None if down."""
    try:
        return await mcping(MC_HOST, MC_PORT)
    except Exception:
        return None


def mc_service(action):
    """systemctl start/stop/restart minegram-mc."""
    r = subprocess.run(["systemctl", action, "minegram-mc"],
                       capture_output=True, text=True, timeout=30)
    return r.returncode == 0, (r.stderr or r.stdout).strip()


async def tps():
    """Paper TPS via RCON debug. Returns list or None."""
    try:
        raw = await cmd("tps")
        # paper: TPS from last 1m, 5m, 15m: 20.0, 20.0, 20.0
        import re
        m = re.findall(r"(\d+\.?\d*), (\d+\.?\d*), (\d+\.?\d*)", raw or "")
        if not m:
            return raw and [raw.strip()] or None
        return list(m[0])
    except Exception:
        return None


async def players():
    """['list'] RCON -> list of nicknames."""
    try:
        raw = await cmd("list")
        if ":" not in raw:
            return []
        raw = raw.split(":", 1)[1]
        return [p.strip() for p in raw.split(",") if p.strip()]
    except Exception:
        return None


def worlds():
    """World dirs in server/ (world, world_nether, world_the_end)."""
    if not MC_DIR.exists():
        return []
    return [d.name for d in MC_DIR.iterdir()
            if d.is_dir() and (d / "level.dat").exists()]


async def say(text):
    return await cmd(f"say {text}")
