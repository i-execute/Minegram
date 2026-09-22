# Minegram

Telegram-бот для управления Minecraft-сервером (Paper + Geyser + Floodgate + ViaVersion — Java **и** Bedrock на одном сервере). Модульная структура в стиле MGIMOMedBot, MTProto через [GoyGram](https://pypi.org/project/goygram/), Rich-сообщения через `pageBlock*` конструкторы, premium-эмодзи из пака [GameEmoji](https://t.me/addemoji/GameEmoji).

## Возможности

- **Меню** (rich + premium-emoji кнопки): Статус / Игроки / Консоль / Миры / Бэкапы / Updater
- **Статус** — server-list-ping, версия, TPS, аптайм; **Игроки** — список онлайна, кик/бан; **Консоль** — RCON, любой командой сообщением
- **Миры**: бэкап (zip миров), конвертация **Bedrock ↔ Java** через Chunker CLI (кнопочный выбор направления и версии, пагинация, потоковая отправка результата)
- **`/sethome`** — задаёт группу-дом и создаёт топики: Общение, Backups, Миры, Logs, MC Logs, Dynmap, Updater (иконки — premium-эмодзи)
- **Updater** — обновление Chunker CLI / cloudflared / dynmap кнопками, уведомления в топик
- **Автобэкапы** миров по расписанию → топик Backups (draft-then-send rich с документом)
- **Потоковая загрузка/выгрузка** файлов с прогрессом (`transfers.py`, charged_upload/download_media)
- **i18n**: EN (default) / RU / ZH, язык на юзера (`config.json → langs`)

## Установка (one-shot, SSH)

```bash
git clone https://github.com/i-execute/Minegram.git
cd Minegram
cp .env.example .env  # заполнить TELEGRAM_API_ID/HASH, BOT_TOKEN, OWNER_ID
bash install.sh       # Paper + Geyser + Floodgate + ViaVersion + dynmap + cloudflared + Chunker CLI + RCON + systemd
```

Юниты: `minegram-mc` (сервер), `minegram-bot` (бот). RAM: `MC_RAM=4G bash install.sh`.

## Структура

```
kernel.py      ядро: init/hooks/rich send+edit, draft-then-send
handlers.py    роутеры callback'ов (mc:*) и сообщений, owner-only
mc.py          RCON/ping/systemd-контроль сервера
rcon.py        async RCON + server-list-ping (чистый stdlib)
worlds.py      конвертация миров (Chunker CLI) + страница «Миры»
backups.py     бэкапы миров → zip → топик Backups
sethome.py     /sethome: группа-дом + топики
updater.py     обновления chunker/cloudflared/dynmap → топик Updater
transfers.py   потоковая upload/download с прогрессом
i18n.py        EN/RU/ZH строки (классы), detect/set lang
constructor.py TL-хелперы (ser/rt/h1-h6/p/btn_row/page_btn) + EMO (GameEmoji)
resolver.py    кэш пиров (mt_entities.json)
config.py      .env + config.json
main.py        asyncio entry
```

## Конфиг

`.env`: `TELEGRAM_API_ID`, `TELEGRAM_API_HASH`, `BOT_TOKEN`, `RCON_HOST/PORT/PASSWORD`, `OWNER_ID`.
`config.json`: `owner_id`, `admins`, `backup_group`, `topics`, `langs`.

## Лицензия

AGPLv3, как референсы-модули (Chunker/WebDeployer by i-execute).
