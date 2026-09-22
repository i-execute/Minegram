"""Minegram — strings: legacy-шейп S.BTN_* (дефолт EN). Новый код — i18n.S(uid)."""
from i18n import S as _S, detect_lang, set_lang, topic_emoji


def __getattr__(name):
    return getattr(_S(lang="en"), name)
