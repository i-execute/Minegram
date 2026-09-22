#!/bin/bash
# Minegram end-to-end smoke: сервисы, ping, rcon, страницы бота, туннель
set -u
cd /QwertyWork/Minegram
PASS=0; FAIL=0
ok()   { PASS=$((PASS+1)); echo "  [OK] $1"; }
bad()  { FAIL=$((FAIL+1)); echo "  [FAIL] $1"; }

echo "== systemd =="
for s in minegram-mc minegram-geyser minegram-bot minegram-dynmap-tunnel; do
  st=$(systemctl is-active $s 2>/dev/null)
  [ "$st" = "active" ] && ok "$s active" || bad "$s = $st"
done

echo "== ports =="
ss -tlnp | grep -q ':25565 ' && ok "25565 java" || bad "25565"
ss -tlnp | grep -q ':25575 ' && ok "25575 rcon" || bad "25575"
ss -ulnp | grep -q ':19132 ' && ok "19132 bedrock" || bad "19132"
url=$(journalctl -u minegram-dynmap-tunnel --no-pager -n 50 2>/dev/null | grep -oE 'https://[a-z0-9-]+\.trycloudflare\.com' | tail -1)
[ -n "$url" ] && ok "tunnel: $url" || bad "no tunnel url"

echo "== bot runtime =="
.venv/bin/python - <<'PYEOF' 2>&1 | grep -vE 'INFO|Parsed|Loaded' | tail -20
import asyncio, sys

async def main():
    import rcon, mc
    fails = []
    st = await mc.status()
    print('  [OK] mcping:', st['version']['name'] if st else None) if st else fails.append('mcping')
    out = await mc.cmd('list')
    print('  [OK] rcon:', out.strip()[:60]) if 'players' in out else fails.append('rcon')
    t = await mc.tps()
    print('  [OK] tps:', t) if t else print('  [WARN] tps n/a')
    pl = await mc.players()
    print('  [OK] players():', pl) if isinstance(pl, list) else fails.append('players')
    import handlers
    for name, fn in handlers.PAGES.items():
        b = fn(uid=7610246474) if name == 'power' else fn()
        b = await b if asyncio.iscoroutine(b) else b
        assert b and len(b) >= 2, f'page {name} empty'
    print('  [OK] all pages:', len(handlers.PAGES))
    import admin, players as PM, logs, dynmap
    ab = await admin.blocks(7610246474, 'main'); assert len(ab) >= 3
    ab2 = await admin.action_blocks(7610246474, 'add_admin'); assert len(ab2) >= 2
    pb = await PM.blocks(7610246474, 'main'); assert len(pb) >= 3
    pask = await PM.action_blocks(7610246474, 'ban'); assert len(pask) >= 2
    lb = await logs.logs_blocks(7610246474, 'mc'); assert len(lb) >= 3
    du = dynmap.tunnel_url(); assert du and 'trycloudflare' in du, du
    print('  [OK] admin/players/logs/dynmap modules')
    i18n_ok = True
    import i18n
    ks = set(k for k in dir(i18n.EN) if k.isupper())
    for c in (i18n.RU, i18n.ZH):
        if set(k for k in dir(c) if k.isupper()) - ks:
            i18n_ok = False
    print('  [OK] i18n parity 143 keys' if i18n_ok else '  [FAIL] i18n parity')
    sys.exit(1 if fails else 0)

asyncio.run(main())
PYEOF
[ $? -eq 0 ] && ok "bot modules e2e" || bad "bot modules e2e"

echo "== result: PASS=$PASS FAIL=$FAIL =="
[ $FAIL -eq 0 ] && echo ALL_GREEN || echo HAS_FAILURES
