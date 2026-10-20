"""The panel's words in English or French.

Texts are written in English in the code; ``T`` gives them in French when
IngeTrazo is set to French (Window ▸ Language), or when the ``SUBD_LANG``
environment variable says ``fr`` (``en`` forces English). Any other
language, or a text missing from the table, stays in English.

    T("Apply")                                   -> "Appliquer"
    T("Converted: {n} faces", n=12)              -> "Converti : 12 faces"
"""
from __future__ import annotations

import os

_forced = None


def set_language(code):
    """Force ``"fr"`` or ``"en"`` (None: follow IngeTrazo again)."""
    global _forced
    _forced = code


def language() -> str:
    if _forced:
        return _forced
    env = os.environ.get("SUBD_LANG", "").strip().lower()
    if env in ("fr", "en"):
        return env
    try:
        from core.i18n import current_language
        code = str(current_language() or "en")
    except Exception:                                    # noqa: BLE001
        return "en"
    return "fr" if code.lower().startswith("fr") else "en"


def T(text: str, **kw) -> str:
    out = FR.get(text, text) if language() == "fr" else text
    return out.format(**kw) if kw else out


FR: dict[str, str] = {}
try:
    from .lang_fr import FR as _FR
    FR.update(_FR)
except Exception:                                        # noqa: BLE001
    pass
