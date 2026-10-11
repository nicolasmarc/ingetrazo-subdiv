# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 IngeTrazo contributors.
"""Toolbar icons for the subdivision-modelling tools.

Same house style as :mod:`views.icons` — drawn with QPainter, ink follows the
theme, orange accent for what the tool acts on — so they need no image files.
Every icon is a small isometric cage (the shape being edited) plus the one
mark that says what the tool does. Self-contained on purpose: it only needs
Qt, so the extension ships its own icons and needs nothing from ``views.icons``
(``tool_icon`` below renders them the same way the host does).
"""
from __future__ import annotations

import math

from PySide6.QtCore import QPointF, Qt
from PySide6.QtGui import (QBrush, QColor, QIcon, QPainter, QPainterPath, QPen,
                           QPixmap, QPolygonF)

_ACCENT = (243, 115, 41)          # IngeTrazo orange (same as views.icons)

# The isometric cube every icon is built on (48 x 48 canvas, 8 px margin).
_TOP = ((24, 12), (36, 19), (24, 26), (12, 19))
_LEFT = ((12, 19), (24, 26), (24, 40), (12, 33))
_RIGHT = ((24, 26), (36, 19), (36, 33), (24, 40))


# ---- helpers ------------------------------------------------------------------------
def _acc(alpha: int = 255) -> QColor:
    return QColor(_ACCENT[0], _ACCENT[1], _ACCENT[2], alpha)


def _pts(points) -> QPolygonF:
    return QPolygonF([QPointF(x, y) for x, y in points])


def _pen(color, width: float = 3.0, style=Qt.SolidLine) -> QPen:
    pen = QPen(color, width, style)
    pen.setCapStyle(Qt.RoundCap)
    pen.setJoinStyle(Qt.RoundJoin)
    return pen


def _outline(p, points, ink, width: float = 3.0, style=Qt.SolidLine) -> None:
    p.save()
    p.setPen(_pen(ink, width, style))
    p.setBrush(Qt.NoBrush)
    p.drawPolygon(_pts(points))
    p.restore()


def _tint(p, points, alpha: int = 140) -> None:
    """A face filled with the accent (no outline)."""
    p.save()
    p.setPen(Qt.NoPen)
    p.setBrush(QBrush(_acc(alpha)))
    p.drawPolygon(_pts(points))
    p.restore()


def _seg(p, a, b, color, width: float = 3.0, style=Qt.SolidLine) -> None:
    p.save()
    p.setPen(_pen(color, width, style))
    p.drawLine(QPointF(a[0], a[1]), QPointF(b[0], b[1]))
    p.restore()


def _node(p, x: float, y: float, r: float = 3.2) -> None:
    p.save()
    p.setPen(Qt.NoPen)
    p.setBrush(QBrush(_acc()))
    p.drawEllipse(QPointF(x, y), r, r)
    p.restore()


def _arrow(p, a, b, color, width: float = 2.6, head: float = 6.0) -> None:
    """A line from ``a`` to ``b`` with a filled head at ``b``."""
    dx, dy = b[0] - a[0], b[1] - a[1]
    n = math.hypot(dx, dy) or 1.0
    ux, uy = dx / n, dy / n
    base = (b[0] - ux * head, b[1] - uy * head)
    _seg(p, a, base, color, width)
    p.save()
    p.setPen(Qt.NoPen)
    p.setBrush(QBrush(color))
    p.drawPolygon(_pts([b, (base[0] - uy * head * 0.7, base[1] + ux * head * 0.7),
                        (base[0] + uy * head * 0.7, base[1] - ux * head * 0.7)]))
    p.restore()


def _cube(p, ink, width: float = 3.0, style=Qt.SolidLine) -> None:
    """The cage: the cube's silhouette and its three inner edges."""
    _outline(p, ((24, 12), (36, 19), (36, 33), (24, 40), (12, 33), (12, 19)),
             ink, width, style)
    for a, b in (((12, 19), (24, 26)), ((36, 19), (24, 26)), ((24, 26), (24, 40))):
        _seg(p, a, b, ink, width, style)


# ---- the icons ----------------------------------------------------------------------
def _create(p, ink):
    """Create: the smooth shape (solid) inside its dashed cage."""
    _cube(p, ink, 1.8, Qt.DashLine)
    path = QPainterPath()
    path.moveTo(24, 14)
    path.cubicTo(36, 14, 38, 24, 36, 31)
    path.cubicTo(34, 38, 28, 40, 24, 40)
    path.cubicTo(18, 40, 12, 38, 12, 30)
    path.cubicTo(12, 20, 16, 14, 24, 14)
    p.save()
    p.setPen(_pen(ink, 3.0))
    p.setBrush(QBrush(_acc(70)))
    p.drawPath(path)
    p.restore()
    for x, y in ((24, 12), (36, 33), (12, 33)):
        _node(p, x, y)


def _edit(p, ink):
    """Edit cage: the cage with one corner picked and dragged."""
    _cube(p, ink)
    _node(p, 36, 19, 4.0)
    _arrow(p, (36, 19), (42, 10), _acc(), 2.4, 5.0)


def _crease(p, ink):
    """Crease: one edge drawn heavy — the edge that stays sharp."""
    _cube(p, ink, 2.2)
    _seg(p, (24, 26), (24, 40), _acc(), 5.0)
    _node(p, 24, 26, 3.4)
    _node(p, 24, 40, 3.4)


def _grow_face(p, ink):
    """Grow F: the top face lifted off the cage, arrow up."""
    _outline(p, _LEFT, ink)
    _outline(p, _RIGHT, ink)
    top = tuple((x, y - 7) for x, y in _TOP)
    _tint(p, top)
    _outline(p, top, ink)
    _arrow(p, (24, 12), (24, 3), ink, 2.6, 5.0)


def _grow_edge(p, ink):
    """Grow E: an open sheet with one border edge pulled out into a new strip."""
    sheet = ((8, 24), (22, 17), (36, 24), (22, 31))
    _outline(p, sheet, ink)
    strip = ((22, 31), (36, 24), (42, 31), (28, 38))
    _tint(p, strip)
    _outline(p, strip, ink, 2.2)
    _seg(p, (22, 31), (36, 24), _acc(), 4.0)


def _stretch(p, ink):
    """Stretch: the cage scaled along one axis — ghost cage and the longer one."""
    ghost = ((24, 22), (34, 27), (34, 36), (24, 41), (14, 36), (14, 27))
    _outline(p, ghost, ink, 1.6, Qt.DashLine)
    tall = ((24, 9), (34, 14), (34, 36), (24, 41), (14, 36), (14, 14))
    _outline(p, tall, ink, 3.0)
    _seg(p, (14, 14), (24, 19), ink)
    _seg(p, (34, 14), (24, 19), ink)
    _seg(p, (24, 19), (24, 41), ink)
    _arrow(p, (24, 14), (24, 4), _acc(), 2.4, 5.0)


def _inset_face(p, ink):
    """Offset F: a smaller copy of the top face, inside it."""
    _outline(p, _LEFT, ink)
    _outline(p, _RIGHT, ink)
    _outline(p, _TOP, ink)
    inner = ((24, 16), (31, 19.5), (24, 23), (17, 19.5))
    _tint(p, inner, 170)
    _outline(p, inner, _acc(), 2.4)


def _offset_edge(p, ink):
    """Offset E: a loop of edges run round the cage, half way up."""
    _cube(p, ink, 2.4)
    loop = ((12, 26), (24, 33), (36, 26), (24, 19))
    _outline(p, loop, _acc(), 3.4)
    for x, y in loop:
        _node(p, x, y, 2.6)


def _squeeze(p, ink):
    """Squeeze: a vase pinched in at the waist by a ring."""
    for x0, x1 in ((12, 12), (36, 36)):
        path = QPainterPath()
        path.moveTo(x0, 10)
        path.quadTo(24 + (24 - x0) * 0.2, 24, x1, 38)
        p.save()
        p.setPen(_pen(ink, 3.0))
        p.setBrush(Qt.NoBrush)
        p.drawPath(path)
        p.restore()
    _seg(p, (12, 10), (36, 10), ink)
    _seg(p, (12, 38), (36, 38), ink)
    _seg(p, (17, 24), (31, 24), _acc(), 4.0)
    _arrow(p, (6, 24), (14, 24), _acc(), 2.2, 4.5)
    _arrow(p, (42, 24), (34, 24), _acc(), 2.2, 4.5)


def _divide(p, ink):
    """Divide: the top face cut into four by two lines through its midpoints."""
    _cube(p, ink, 2.6)
    _seg(p, (30, 15.5), (18, 22.5), _acc(), 3.2)
    _seg(p, (18, 15.5), (30, 22.5), _acc(), 3.2)
    _node(p, 24, 19, 3.0)


def _delete_face(p, ink):
    """Delete F: the top face is gone — a cross where it used to be."""
    _outline(p, _LEFT, ink)
    _outline(p, _RIGHT, ink)
    _seg(p, (19, 13), (29, 25), _acc(), 3.6)
    _seg(p, (29, 13), (19, 25), _acc(), 3.6)


def _close(p, ink):
    """Close: an open cage whose empty top is filled in."""
    _outline(p, _LEFT, ink)
    _outline(p, _RIGHT, ink)
    _tint(p, _TOP, 150)
    _outline(p, _TOP, ink, 2.2, Qt.DashLine)


def _bridge(p, ink):
    """Bridge: two separate openings joined by a band."""
    for x in (8, 30):
        _outline(p, ((x, 18), (x + 10, 18), (x + 10, 34), (x, 34)), ink)
    tube = QPainterPath()
    tube.moveTo(18, 18)
    tube.quadTo(24, 9, 30, 18)
    tube.lineTo(30, 34)
    tube.quadTo(24, 25, 18, 34)
    tube.closeSubpath()
    p.save()
    p.setPen(_pen(_acc(), 3.0))
    p.setBrush(QBrush(_acc(90)))
    p.drawPath(tube)
    p.restore()


def _shell(p, ink):
    """Shell: a box whose top is hollowed out — the wall shows as a ring."""
    _outline(p, _LEFT, ink)
    _outline(p, _RIGHT, ink)
    _outline(p, _TOP, ink)
    cavity = ((17, 20), (24, 24), (31, 20), (31, 28), (24, 32), (17, 28))
    p.save()
    p.setPen(_pen(_acc(), 2.4))
    p.setBrush(QBrush(_acc(90)))
    p.drawPolygon(_pts(cavity))
    p.drawPolygon(_pts(((24, 16), (31, 20), (24, 24), (17, 20))))
    p.restore()


#: ``tool_icon`` key -> draw function(painter, ink).
SUBD_ICONS = {
    "subd_create": _create,
    "subd_edit": _edit,
    "subd_crease": _crease,
    "subd_grow_face": _grow_face,
    "subd_grow_edge": _grow_edge,
    "subd_stretch": _stretch,
    "subd_inset_face": _inset_face,
    "subd_offset_edge": _offset_edge,
    "subd_squeeze": _squeeze,
    "subd_divide": _divide,
    "subd_delete_face": _delete_face,
    "subd_close": _close,
    "subd_bridge": _bridge,
    "subd_shell": _shell,
}


# ---- rendering -----------------------------------------------------------------------
_PX = 48          # render size (QIcon scales down; big = crisp on HiDPI)


def _ink() -> QColor:
    """The theme's text colour, so the icons read on light and dark themes."""
    from PySide6.QtWidgets import QApplication
    app = QApplication.instance()
    if app is not None:
        c = app.palette().windowText().color()
        return QColor(c.red(), c.green(), c.blue())
    return QColor(40, 44, 52)


def tool_icon(key: str) -> QIcon:
    """The :class:`QIcon` of a SubD tool (null if ``key`` is unknown)."""
    draw = SUBD_ICONS.get(key)
    if draw is None:
        return QIcon()
    pm = QPixmap(_PX, _PX)
    pm.fill(Qt.transparent)
    p = QPainter(pm)
    p.setRenderHint(QPainter.Antialiasing, True)
    ink = _ink()
    p.setPen(_pen(ink, 3.0))
    draw(p, ink)
    p.end()
    return QIcon(pm)
