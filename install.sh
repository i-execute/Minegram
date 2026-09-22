#!/usr/bin/env bash
# Minegram — one-shot install: Paper + Geyser + Floodgate + ViaVersion + bot
set -euo pipefail

BASE="$(cd "$(dirname "$0")" && pwd)"
MC_DIR="${MC_DIR:-$BASE/server}"
RAM="${RAM:-2G}"
MC_VER="${MC_VER:-1.21.11}"

mkdir -p "$MC_DIR/plugins" "$MC_DIR/logs"

echo "== Paper $MC_VER =="
PAPER_URL=$(curl -s "https://fill.papermc.io/v3/projects/paper/versions/$MC_VER/builds/latest" \
  | python3 -c "import json,sys; print(json.load(sys.stdin)['downloads']['server:default']['url'])")
curl -sL "$PAPER_URL" -o "$MC_DIR/paper.jar"

echo "== Geyser + Floodgate + ViaVersion =="
curl -sL "https://download.geysermc.org/v2/projects/geyser/versions/latest/builds/latest/downloads/spigot" -o "$MC_DIR/plugins/Geyser-Spigot.jar"
curl -sL "https://download.geysermc.org/v2/projects/floodgate/versions/latest/builds/latest/downloads/spigot" -o "$MC_DIR/plugins/floodgate-spigot.jar"
curl -sL "https://ci.viaversion.com/job/ViaVersion/lastSuccessfulBuild/artifact/build/libs/$(curl -s 'https://ci.viaversion.com/job/ViaVersion/lastSuccessfulBuild/api/json' | python3 -c "import json,sys; print(json.load(sys.stdin)['artifacts'][0]['relativePath'].split('/')[-1])")" -o "$MC_DIR/plugins/ViaVersion.jar"


echo "== Purpur ${MC_VER:-26.3} =="
CHUNKER_TAG="${CHUNKER_TAG:-$(curl -s https://api.github.com/repos/HiveGamesOSS/Chunker/releases/latest | python3 -c "import json,sys; print(json.load(sys.stdin)['tag_name'])" || echo "")}"
if [ -n "$CHUNKER_TAG" ]; then
  CHUNKER_URL=$(curl -s "https://api.github.com/repos/HiveGamesOSS/Chunker/releases/tags/$CHUNKER_TAG" | python3 -c "
import json,sys
d = json.load(sys.stdin)
for a in d.get('assets', []):
    if a['name'].startswith('chunker-cli') and a['name'].endswith('.jar'):
        print(a['browser_download_url']); break")
  [ -n "$CHUNKER_URL" ] && curl -sL "$CHUNKER_URL" -o "$BASE/chunker-cli.jar" && echo "chunker: $CHUNKER_TAG"
else
  echo "chunker: SKIP (api fail)"
fi


echo "== cloudflared =="
CF_ARCH=$(dpkg --print-architecture 2>/dev/null || echo amd64)
CF_TAG=$(curl -s https://api.github.com/repos/cloudflare/cloudflared/releases/latest | python3 -c "import json,sys; print(json.load(sys.stdin)['tag_name'])" || echo "")
if [ -n "$CF_TAG" ]; then
  curl -sL "https://github.com/cloudflare/cloudflared/releases/download/${CF_TAG}/cloudflared-linux-${CF_ARCH}" -o /usr/local/bin/cloudflared \
    && chmod +x /usr/local/bin/cloudflared && echo "cloudflared: $CF_TAG"
else
  echo "cloudflared: SKIP (api fail)"
fi

echo "== Dynmap =="
DYNMAP_URL=$(curl -s https://api.github.com/repos/webbukkit/dynmap/releases | python3 -c "
import json,sys
for r in json.load(sys.stdin):
    if any(a['name'].endswith('.jar') for a in r.get('assets', [])):
        for a in r['assets']:
            if a['name'].endswith('.jar'):
                print(a['browser_download_url']); break
        break" || true)
[ -n "$DYNMAP_URL" ] && curl -sL "$DYNMAP_URL" -o "$MC_DIR/plugins/dynmap.jar" && echo "dynmap: ok" || echo "dynmap: SKIP"

echo "== eula =="
grep -q "^eula=true" "$MC_DIR/eula.txt" 2>/dev/null || echo "eula=true" > "$MC_DIR/eula.txt"

echo "== first boot (generates configs) =="
cd "$MC_DIR"
java -Xms512M -Xmx"$RAM" -jar purpur.jar --nogui || true

echo "== rcon + settings =="
sed -i 's/^rcon\.password=.*/rcon.password=minegram_rcon/; s/^enable-rcon=.*/enable-rcon=true/; s/^rcon\.port=.*/rcon.port=25575/' server.properties 2>/dev/null || {
  printf 'enable-rcon=true\nrcon.port=25575\nrcon.password=minegram_rcon\n' >> server.properties
}
sed -i 's/^online-mode=.*/online-mode=true/' server.properties 2>/dev/null || echo "online-mode=true" >> server.properties

echo "== python deps =="
python3 -m venv "$BASE/.venv" 2>/dev/null || true
"$BASE/.venv/bin/pip" install -q goygram python-dotenv 2>/dev/null || pip3 install --user goygram python-dotenv

echo "== systemd (minegram-mc + minegram-bot) =="
cat > /etc/systemd/system/minegram-mc.service <<EOF2
[Unit]
Description=Minegram Minecraft (Paper+Geyser)
After=network.target

[Service]
Type=simple
WorkingDirectory=$MC_DIR
ExecStart=java -Xms512M -Xmx$RAM -jar paper.jar --nogui
Restart=on-failure
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF2

cat > /etc/systemd/system/minegram-bot.service <<EOF2
[Unit]
Description=Minegram TG bot
After=network.target minegram-mc.service

[Service]
Type=simple
WorkingDirectory=$BASE
ExecStart=$BASE/.venv/bin/python3 $BASE/main.py
Restart=on-failure
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF2

systemctl daemon-reload
echo "== DONE: systemctl start minegram-mc minegram-bot =="
