#!/usr/bin/env python3
"""MCP server: RCON bridge для Minecraft (stdio transport)."""
import asyncio
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, "/QwertyWork/Minegram")
from dotenv import dotenv_values

ENV = dotenv_values("/QwertyWork/Minegram/.env")

PROTOCOL = "2024-11-05"
TOOLS = [
    {"name": "mc_cmd", "description": "Выполнить RCON-команду на Minecraft-сервере (give, tp, gamerule, say, list...)", "inputSchema": {"type": "object", "properties": {"command": {"type": "string", "description": "RCON команда"}}, "required": ["command"]}},
    {"name": "mc_say", "description": "Отправить сообщение в игровой чат Minecraft (видно всем игрокам)", "inputSchema": {"type": "object", "properties": {"text": {"type": "string"}}, "required": ["text"]}},
    {"name": "mc_players", "description": "Список игроков онлайн", "inputSchema": {"type": "object", "properties": {}}},
    {"name": "mc_inbox", "description": "Прочитать новые q-сообщения игрока из инбокса (и очистить)", "inputSchema": {"type": "object", "properties": {}}},
]


async def rcon_exec(cmd):
    sys.path.insert(0, "/QwertyWork/Minegram")
    from rcon import rcon
    return await rcon(ENV["RCON_HOST"], int(ENV["RCON_PORT"]), ENV["RCON_PASSWORD"], cmd)


def send(obj):
    sys.stdout.write(json.dumps(obj) + "\n")
    sys.stdout.flush()


def run_cmd_sync(cmd):
    return asyncio.run(rcon_exec(cmd))


async def handle(name, args):
    if name == "mc_cmd":
        out = await rcon_exec(args["command"])
        return {"content": [{"type": "text", "text": out or "(пусто)"}]}
    if name == "mc_say":
        await rcon_exec(f"say {args['text']}")
        return {"content": [{"type": "text", "text": "доставлено"}]}
    if name == "mc_players":
        out = await rcon_exec("list")
        return {"content": [{"type": "text", "text": out}]}
    if name == "mc_inbox":
        p = Path("/QwertyWork/Minegram/qwerty_inbox.txt")
        if not p.exists():
            return {"content": [{"type": "text", "text": "(пусто)"}]}
        data = p.read_text().strip()
        if data:
            p.write_text("")
        return {"content": [{"type": "text", "text": data or "(пусто)"}]}
    raise ValueError(f"unknown tool {name}")


def main():
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            req = json.loads(line)
        except json.JSONDecodeError:
            continue
        method = req.get("method")
        rid = req.get("id")
        if method == "initialize":
            send({"jsonrpc": "2.0", "id": rid, "result": {"protocolVersion": PROTOCOL, "capabilities": {"tools": {}}, "serverInfo": {"name": "minegram-mcp", "version": "1.0"}}})
        elif method == "notifications/initialized":
            pass
        elif method == "tools/list":
            send({"jsonrpc": "2.0", "id": rid, "result": {"tools": TOOLS}})
        elif method == "tools/call":
            try:
                res = asyncio.run(handle(req["params"]["name"], req["params"].get("arguments", {})))
                send({"jsonrpc": "2.0", "id": rid, "result": res})
            except Exception as e:
                send({"jsonrpc": "2.0", "id": rid, "result": {"content": [{"type": "text", "text": f"error: {e}"}]}})
        elif method == "ping":
            send({"jsonrpc": "2.0", "id": rid, "result": {}})
        elif rid is not None:
            send({"jsonrpc": "2.0", "id": rid, "error": {"code": -32601, "message": "method not found"}})


if __name__ == "__main__":
    main()
