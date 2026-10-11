# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 IngeTrazo contributors.
import pytest

KEYS = ["subd_create", "subd_edit", "subd_crease", "subd_grow_face",
        "subd_grow_edge", "subd_stretch", "subd_inset_face", "subd_offset_edge",
        "subd_squeeze", "subd_divide", "subd_delete_face", "subd_close",
        "subd_bridge", "subd_shell"]


@pytest.fixture(scope="module")
def app():
    from PySide6.QtWidgets import QApplication
    return QApplication.instance() or QApplication([])


def _pixels(icon):
    img = icon.pixmap(48, 48).toImage()
    return bytes(img.constBits())[: img.sizeInBytes()]


def test_subd_icons_are_registered_and_draw(app):
    from subdiv import icons

    for key in KEYS:
        icon = icons.tool_icon(key)
        assert not icon.isNull(), key
        assert any(_pixels(icon)), f"{key} draws nothing"


def test_subd_icons_are_all_different(app):
    from subdiv import icons

    drawn = {key: _pixels(icons.tool_icon(key)) for key in KEYS}
    assert len(set(drawn.values())) == len(KEYS)
