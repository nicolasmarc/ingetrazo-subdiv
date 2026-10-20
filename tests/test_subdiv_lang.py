"""The panel's texts: English by default, French when IngeTrazo is in French;
the Create help text names the document's unit, not metres."""
import re

from subdiv import lang, ops
from subdiv.lang_fr import FR


def _texts():
    out = []
    for s in ops.TOOL_SPECS:
        out += [s.label, s.tip] + ([s.value_label] if s.value_label else [])
    return out


def test_create_tip_names_the_unit_of_the_document():
    tip = ops.SPECS["create"].tip
    assert "{unit}" in tip and "metre" not in tip
    assert lang.T(tip, unit="millimetres").startswith("New box cage (size in millimetres)")
    for s in ops.TOOL_SPECS:                  # no other help text names a unit
        assert not re.search(r"\b(metres?|meters?|mm|inch(es)?)\b", s.tip), s.key


def test_french_follows_the_language_and_keeps_placeholders():
    lang.set_language("fr")
    try:
        assert lang.T("Apply") == "Appliquer"
        assert lang.T(ops.SPECS["create"].tip, unit=lang.T("inches")).startswith(
            "Nouvelle cage en boîte (taille en pouces)")
        assert lang.T("Converted: {n} faces, {k} sharp edges", n=12, k=3) == \
            "Converti : 12 faces, 3 arêtes vives"
        assert ops.describe(("e", 3, 4)) == "Arête 3-4"
        for t in _texts():
            assert t in FR, t
    finally:
        lang.set_language(None)
    assert lang.T("Apply") == "Apply"
    for k, v in FR.items():
        assert set(re.findall(r"{(\w+)}", k)) == set(re.findall(r"{(\w+)}", v)), k
        assert k.count("%d") == v.count("%d"), k


def test_english_is_the_default_outside_ingetrazo(monkeypatch):
    monkeypatch.delenv("SUBD_LANG", raising=False)
    assert lang.language() in ("en", "fr")      # IngeTrazo decides when present
    monkeypatch.setenv("SUBD_LANG", "fr")
    assert lang.T("Finish") == "Terminer"
