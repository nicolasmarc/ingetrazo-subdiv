"""The panel's words in English, French or Spanish.

Texts are written in English in the code; ``T`` gives them in French or
Spanish when IngeTrazo is set to that language (Window ▸ Language), or when
the ``SUBD_LANG`` environment variable says ``fr`` or ``es`` (``en`` forces
English). Any other language, or a text missing from a table, stays in
English.

    T("Apply")                                   -> "Appliquer" / "Aplicar"
    T("Converted: {n} faces", n=12)              -> "Converti : 12 faces"
"""
from __future__ import annotations

import os

_forced = None


LANGUAGES = ("en", "fr", "es")


def set_language(code):
    """Force ``"en"``, ``"fr"`` or ``"es"`` (None: follow IngeTrazo again)."""
    global _forced
    _forced = code


def language() -> str:
    if _forced:
        return _forced
    env = os.environ.get("SUBD_LANG", "").strip().lower()
    if env in LANGUAGES:
        return env
    try:
        from core.i18n import current_language
        code = str(current_language() or "en")
    except Exception:                                    # noqa: BLE001
        return "en"
    code = code.lower().replace("_", "-")
    for lg in ("fr", "es"):
        if code == lg or code.startswith(lg + "-"):      # fr, fr-CA, es, es-MX...
            return lg
    return "en"


def T(text: str, **kw) -> str:
    out = TABLES.get(language(), {}).get(text, text)
    return out.format(**kw) if kw else out


FR: dict[str, str] = {}
ES: dict[str, str] = {}
try:
    from .lang_fr import FR as _FR
    FR.update(_FR)
except Exception:                                        # noqa: BLE001
    pass
try:
    from .lang_es import ES as _ES
    ES.update(_ES)
except Exception:                                        # noqa: BLE001
    pass
TABLES = {"fr": FR, "es": ES}
