from pathlib import Path


BASE = Path(__file__).parent


def purge_logs():
    removed = []
    for path in BASE.glob("bot.log*"):
        if path.is_file():
            path.unlink(missing_ok=True)
            removed.append(path.name)
    return removed
