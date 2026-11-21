# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 IngeTrazo contributors.
"""SubD — subdivision modelling, as an IngeTrazo extension.

Model a smooth surface from a coarse control cage. The cage is a small mesh
you push, pinch, crease and divide; the smooth Catmull-Clark skin is rebuilt
from it after every step and lives in an ordinary group, so it saves, exports
and orbits like any other geometry. The cage travels with the group
(``group.ext["subdiv"]``) and is saved in the .igz.

The fourteen tools (see ``ops.py``):
  Create, Edit cage, Crease, Grow F, Grow E, Stretch, Offset F, Offset E,
  Squeeze, Divide, Delete F, Close, Bridge, Shell.

How to use: open the SubD tab, press Apply on "Create" for a box cage, click
a point, edge or face of the cage in the view (with the Select tool) and pick
a tool, set its value, press Apply. Or just DRAG the selected point, edge or
face with the mouse to move it freely (the axis choice constrains the drag;
Esc cancels). Every step is one undo step.

Symmetry: tick "Symmetry", set the plane (the centre of the piece along X, Y
or Z, or the plane of the selected face) and every edit on one side is
repeated on the other. To join two SubD pieces, choose the other one under
"Join with", press Join, delete a face on each piece and Bridge the two
openings. The cage follows the group when it is moved, rotated or scaled.

Groups made with other tools can be converted too: pick one under "Convert
group" and press "Convert to SubD". Its faces become the control cage (keep
it coarse), and edges sharper than the chosen angle are creased so a box
stays boxy.

The geometry and the tool logic live in the other modules of this package
(pure Python, tested without a window); this file is only the interface.
"""
from __future__ import annotations

import logging
import math

import numpy as np
from PySide6.QtCore import QEvent, QObject, QPoint, QPointF, QSize, Qt, QTimer
from PySide6.QtGui import QBrush, QColor, QPen, QPolygonF, QVector3D
from PySide6.QtWidgets import (
    QButtonGroup, QCheckBox, QComboBox, QDoubleSpinBox, QGridLayout,
    QHBoxLayout, QLabel, QPushButton, QScrollArea, QSpinBox, QToolButton,
    QVBoxLayout, QWidget,
)

from core import units
from . import group as subdiv_group
from . import ops as subdiv_ops
from .lang import T
from core.group import Group
from core.history import Command
from core.mesh import Mesh

from .edit import Cage, ekey
from . import modeling

ACCENT = QColor(243, 115, 41)
CAGE_LINE = QColor(243, 115, 41, 200)
CREASE_LINE = QColor(220, 40, 60, 230)
FINISH_BUDGET = 6000      # faces: what "Automatic" aims at when finishing a piece
AXIS_VEC = {"x": (1.0, 0.0, 0.0), "y": (0.0, 1.0, 0.0), "z": (0.0, 0.0, 1.0)}
AXIS_COLOR = {"x": QColor(228, 62, 62), "y": QColor(60, 175, 70), "z": QColor(55, 105, 230)}
GHOST_LINE = QColor(243, 115, 41, 90)
PLANE_FILL = QColor(60, 140, 255, 38)
PLANE_LINE = QColor(60, 140, 255, 170)
_SUFFIX = {"m": " m", "cm": " cm", "mm": " mm", "in": " in", "ft": " ft",
           "ft-in": " in", "in-frac": " in", "ft-in-frac": " in"}
log = logging.getLogger(__name__)


class _Swap(subdiv_group.SwapGroup, Command):
    """SwapGroup (do/undo) registered as an app Command."""


class _SetExt(subdiv_group.SetExt, Command):
    """Change a group's stored settings (e.g. the symmetry plane), undoably."""


class _Split(subdiv_group.SplitGroup, Command):
    """Split one SubD group into its separate pieces, undoably."""


class _Join(subdiv_group.JoinGroups, Command):
    """Merge two SubD groups into one, undoably."""


# ---- the cage a group carries, followed along with the group ---------------------------
_STATE = subdiv_group.StateCache()
_SCENE = None


def _state(group):
    """``(cage, levels, lines)`` for a SubD group, or None. The cage is carried
    along when the group has been moved, rotated or scaled (re-checked when the
    scene's version changes)."""
    return _STATE.get(group, getattr(_SCENE, "version", None))


class SubdPanel(QWidget):
    def __init__(self, app) -> None:
        super().__init__()
        self.app = app
        self.active_uid = None
        self.sel = None              # ("v", i) | ("e", a, b) | ("f", i)
        self.extra = []              # more items picked with Shift (moved together)
        self._swallow = False        # the release that follows a Shift press
        self.pending = None          # Bridge between its two clicks
        self._bridge_first = None    # Bridge: the end picked by the first click
        self._auto_bridged = False
        self._crease_auto = None     # the sharpness we filled in ourselves (see _follow_levels)
        self._click = None           # the last plain click, for repeated-click cycling
        self._drag = None            # a freestyle drag in progress
        self._unit = None            # the document's unit the value box shows
        self._scale = 1.0            # metres per displayed unit
        self.tool = "grow_face"
        self._last_value = {}
        self._building = True

        lay = QVBoxLayout(self)
        row = QHBoxLayout()
        row.addWidget(QLabel(T("SubD group")))
        self.groups = QComboBox()
        self.groups.currentIndexChanged.connect(self._on_group_chosen)
        row.addWidget(self.groups, 1)
        lay.addLayout(row)

        grid = QGridLayout()
        self.buttons = QButtonGroup(self)
        self.buttons.setExclusive(True)
        for n, spec in enumerate(subdiv_ops.TOOL_SPECS):
            b = QToolButton()
            b.setCheckable(True)
            b.setIcon(_icon(spec.icon))
            b.setIconSize(QSize(26, 26))
            b.setFixedSize(34, 34)
            b.setToolButtonStyle(Qt.ToolButtonIconOnly)
            b.setToolTip(f"{T(spec.label)} — {self._tip(spec)}")
            b.setAutoRaise(True)
            b.clicked.connect(lambda _c=False, k=spec.key: self._pick_tool(k))
            self.buttons.addButton(b)
            grid.addWidget(b, n // 8, n % 8)
            setattr(self, f"_btn_{spec.key}", b)
        grid.setSpacing(2)
        lay.addLayout(grid)

        self.hint = QLabel()
        self.hint.setWordWrap(True)
        self.hint.setTextFormat(Qt.RichText)
        lay.addWidget(self.hint)

        vrow = QHBoxLayout()
        self.value_label = QLabel()
        vrow.addWidget(self.value_label)
        self.value = QDoubleSpinBox()
        self.value.setDecimals(2)
        vrow.addWidget(self.value, 1)
        self.axis = QComboBox()
        for text, data in ((T("Auto"), "auto"), ("X", "x"), ("Y", "y"), ("Z", "z")):
            self.axis.addItem(text, data)
        self.axis.setToolTip(T("Direction for Edit, Stretch and Squeeze "
                             "(Auto: the face's normal / ring)"))
        vrow.addWidget(self.axis)
        self.axis.currentIndexChanged.connect(lambda *_: (self._refresh_auto_ghost(),
                                                          self.app.viewport.update()))
        self.value.valueChanged.connect(lambda *_: (self._refresh_auto_ghost(),
                                                    self.app.viewport.update()))
        self.side = QComboBox()
        for text, data in ((T("Outside"), "outside"), (T("Inside"), "inside"), (T("Centred"), "center")):
            self.side.addItem(text, data)
        self.side.setToolTip(T("Where the wall grows from the current surface"))
        vrow.addWidget(self.side)
        self.cut = QComboBox()
        for text, data in ((T("Whole loop"), "loop"), (T("Only this face"), "face")):
            self.cut.addItem(text, data)
        self.cut.setToolTip(T("Divide a face or an edge. Whole loop: the cut runs on round the "
                            "piece through the quads beyond (clean quads). Only this face: "
                            "just the face (or the faces touching the edge) is cut; the "
                            "neighbours get an extra point."))
        vrow.addWidget(self.cut)
        self.ends = QComboBox()
        for text, data in ((T("Closed ends"), "closed"), (T("Open ends"), "open")):
            self.ends.addItem(text, data)
        self.ends.setToolTip(T("Loft and Sweep: close the two ends with a face, or leave "
                             "the surface open."))
        vrow.addWidget(self.ends)
        self.twist = QDoubleSpinBox()
        self.twist.setDecimals(0)
        self.twist.setRange(-360.0, 360.0)
        self.twist.setSingleStep(15.0)
        self.twist.setSuffix(" °")
        self.twist.setPrefix(T("Twist") + " ")
        self.twist.setToolTip(T("Loft: turn each section against the one before, in steps of "
                              "one point of the section (a 4-point section turns by 90°)."))
        self.twist.valueChanged.connect(lambda *_: self._refresh_auto_ghost())
        self.ends.currentIndexChanged.connect(lambda *_: self._refresh_auto_ghost())
        vrow.addWidget(self.twist)
        lay.addLayout(vrow)

        self.selection_label = QLabel()
        lay.addWidget(self.selection_label)
        self.apply_btn = QPushButton(T("Apply"))
        self.apply_btn.clicked.connect(self.apply)
        lay.addWidget(self.apply_btn)
        self.status = QLabel()                     # right under Apply, so the answer is
        self.status.setWordWrap(True)              # always in view (no scrolling)
        lay.addWidget(self.status)

        prow = QHBoxLayout()
        self.skin_pick = QCheckBox(T("Pick on the skin"))
        self.skin_pick.setChecked(True)
        self.skin_pick.setToolTip(
            T("Click the smooth surface itself: the point, edge or face of the cage "
              "that shapes the spot you click is selected, even with the cage hidden."))
        self.skin_pick.toggled.connect(lambda _on: self._skin_mode_changed())
        prow.addWidget(self.skin_pick)
        self.show_cage = QCheckBox(T("Show cage"))
        self.show_cage.setChecked(True)
        self.show_cage.toggled.connect(lambda _on: self.app.viewport.update())
        prow.addWidget(self.show_cage)
        lay.addLayout(prow)

        sym = QHBoxLayout()
        self.sym_box = QCheckBox(T("Symmetry"))
        self.sym_box.setToolTip(T("Repeat every edit on the other side of the plane."))
        self.sym_box.toggled.connect(self._sym_toggled)
        sym.addWidget(self.sym_box)
        self.sym_axis = QComboBox()
        for text, data in (("X", (1.0, 0.0, 0.0)), ("Y", (0.0, 1.0, 0.0)),
                           ("Z", (0.0, 0.0, 1.0))):
            self.sym_axis.addItem(text, data)
        self.sym_axis.setToolTip(T("Axis the plane is perpendicular to."))
        sym.addWidget(self.sym_axis)
        centre = QPushButton(T("Centre"))
        centre.setToolTip(T("Put the plane through the middle of the piece."))
        centre.clicked.connect(self._sym_centre)
        sym.addWidget(centre)
        self.soft_box = QCheckBox(T("Soft"))
        self.soft_box.setToolTip(T("Soft selection: moving a point also drags the points "
                                 "around it, fading out at the radius."))
        sym.addWidget(self.soft_box)
        self.soft_radius = QDoubleSpinBox()
        self.soft_radius.setDecimals(2)
        self.soft_radius.setRange(0.01, 1000.0)
        self.soft_radius.setValue(0.5)
        self.soft_radius.setToolTip(T("Radius of the soft selection."))
        sym.addWidget(self.soft_radius)
        face = QPushButton(T("From face"))
        face.setToolTip(T("Use the plane of the selected face."))
        face.clicked.connect(self._sym_from_face)
        sym.addWidget(face)
        lay.addLayout(sym)

        main = lay
        lay = self._section(main, T("Join, split, convert"))
        join = QHBoxLayout()
        join.addWidget(QLabel(T("Join with")))
        self.join_with = QComboBox()
        self.join_with.setToolTip(T("Another SubD group to merge into this one, "
                                  "so Bridge can link their openings."))
        join.addWidget(self.join_with, 1)
        join_btn = QPushButton(T("Join"))
        join_btn.clicked.connect(self.join)
        join.addWidget(join_btn)
        split_btn = QPushButton(T("Split"))
        split_btn.setToolTip(T("Undo a Join: every separate piece of this group "
                             "becomes its own SubD group again."))
        split_btn.clicked.connect(self.split)
        join.addWidget(split_btn)
        lay.addLayout(join)

        conv = QHBoxLayout()
        conv.addWidget(QLabel(T("Convert group")))
        self.convertible = QComboBox()
        self.convertible.setToolTip(T("Groups not made by this plugin. Their faces become "
                                    "the cage, so use a coarse one (under 7000 faces; editing gets slow above a few hundred)."))
        conv.addWidget(self.convertible, 1)
        lay.addLayout(conv)
        conv2 = QHBoxLayout()
        conv2.addWidget(QLabel(T("Crease edges over")))
        self.angle = QDoubleSpinBox()
        self.angle.setRange(0.0, 180.0)
        self.angle.setDecimals(0)
        self.angle.setValue(30.0)
        self.angle.setSuffix("°")
        self.angle.setToolTip(T("Edges where two faces meet at more than this angle stay "
                              "sharp. 0 = no automatic creases (everything rounds)."))
        conv2.addWidget(self.angle)
        convert = QPushButton(T("Convert to SubD"))
        convert.setToolTip(T("Replace the chosen group by a SubD group built on its faces. "
                           "Ctrl+Z brings the original back."))
        convert.clicked.connect(self.convert)
        conv2.addWidget(convert, 1)
        lay.addLayout(conv2)
        self.sharp_create = QCheckBox(T("Create with sharp edges (angle above)"))
        self.sharp_create.setToolTip(
            T("Create then gives a crisp box instead of a rounded block: the edges of the "
            "new box stay sharp when the angle above is below 90 degrees (30 is fine). "
            "Stretch, Grow and Shell then work on a rectilinear piece."))
        lay.addWidget(self.sharp_create)

        lay = self._section(main, T("Smoothing, finish, handles"))
        self.menu_only = QCheckBox(T("Right-click: SubD tools only"))
        self.menu_only.setChecked(True)
        self.menu_only.setToolTip(T("Right-click on the SubD piece shows a menu of SubD tools "
                                    "only (smoothing 0 to 4, cage, copy, paste). Untick to get "
                                    "the model's usual menu with the SubD tools inside."))
        lay.addWidget(self.menu_only)
        self.fast_edit = QCheckBox(T("Light surface while editing"))
        self.fast_edit.setChecked(True)
        self.fast_edit.setToolTip(T("Each edit shows a lighter surface at once and finishes the "
                                    "full smoothing when you pause (about a second). Faster to "
                                    "model with; untick to always build the full surface."))
        lay.addWidget(self.fast_edit)
        self.live_box = QCheckBox(T("Right-click tools: adjust with the mouse"))
        self.live_box.setChecked(False)
        self.live_box.setToolTip(T("A tool chosen from the right-click menu follows the mouse: "
                                   "move to set the value and see the result, click to apply, "
                                   "Enter to type an exact value, Esc to cancel. Shift = finer, "
                                   "Ctrl = snap to steps. Untick to always get the value box."))
        lay.addWidget(self.live_box)
        look = QHBoxLayout()
        look.addWidget(QLabel(T("Smoothing")))
        self.levels = QSpinBox()
        self.levels.setRange(0, 4)
        self.levels.setValue(4)
        self.levels.setToolTip(T("Subdivision steps: 0 is the cage itself."))
        look.addWidget(self.levels)
        self.auto = QCheckBox(T("Auto"))
        self.auto.setChecked(True)
        self.auto.setToolTip(T("Smoothest level that keeps the surface under "
                             "about 25 000 triangles; uncheck to choose it yourself."))
        self.auto.toggled.connect(self._on_auto)
        look.addWidget(self.auto)
        self.lines = QComboBox()
        for text, data in ((T("Cage lines"), "cage"), (T("All edges"), "all"), (T("No lines"), "none")):
            self.lines.addItem(text, data)
        look.addWidget(self.lines, 1)
        lay.addLayout(look)
        upd = QPushButton(T("Update look"))
        upd.setToolTip(T("Rebuild the surface with this smoothing and these lines."))
        upd.clicked.connect(self.update_look)
        flip = QPushButton(T("Flip faces"))
        flip.setToolTip(T("Blue faces are seen from behind. Flip turns over the connected part that "
                        "holds the selected face; with nothing selected, the whole group."))
        flip.clicked.connect(self.flip)
        urow = QHBoxLayout()
        urow.addWidget(upd)
        urow.addWidget(flip)
        lay.addLayout(urow)
        frow = QHBoxLayout()
        frow.addWidget(QLabel(T("Finish detail")))
        self.finish_detail = QComboBox()
        self.finish_detail.addItem(T("Automatic (light)"), "auto")
        self.finish_detail.addItem(T("Same as the view"), None)
        self.finish_detail.addItem(T("Light (1)"), 1)
        self.finish_detail.addItem(T("Medium (2)"), 2)
        self.finish_detail.addItem(T("Fine (3)"), 3)
        self.finish_detail.setToolTip(
            T("How finely the curved parts are cut when the piece is finished."
            " Automatic keeps the result under about %d faces so ordinary tools "
            "stay fast (the smoothest level that fits). Each step up multiplies the "
            "triangles by four. Flat faces are always single polygons, whatever you "
            "choose.") % FINISH_BUDGET)
        frow.addWidget(self.finish_detail, 1)
        lay.addLayout(frow)
        fin = QPushButton(T("Finish"))
        fin.setToolTip(T("Finish (no longer SubD): keep the smooth surface as an ordinary "
                       "group and drop the cage. If the cage is closed and sound, the "
                       "result is a Solid Group (usable with Solid Tools) and its "
                       "volume is reported; if it is still open, you get the surface "
                       "and the reason. Undo brings the SubD group back."))
        fin.clicked.connect(self.finish)
        lay.addWidget(fin)
        hrow = QHBoxLayout()
        hrow.addWidget(QLabel(T("Handles")))
        self.handles = QComboBox()
        self.handles.addItem(T("Move + Rotate"), "both")
        self.handles.addItem(T("Move only"), "move")
        self.handles.addItem(T("Rotate only (protractor)"), "rotate")
        self.handles.setToolTip(
            T("Move: drag a coloured tip to slide the selection along that axis.\n"
            "Rotate: drag a coloured ring to turn the selection around that axis "
            "(hold Ctrl to snap to 15 degrees).\n"
            "Both are shown by default; pick one to keep the view clear."))
        self.handles.currentIndexChanged.connect(lambda _i: self.app.viewport.update())
        hrow.addWidget(self.handles, 1)
        lay.addLayout(hrow)
        self._skin = None                    # (key, Skin) cache for picking on the skin

        main.addStretch(1)

        self._building = False
        self.levels.setEnabled(not self.auto.isChecked())
        getattr(self, f"_btn_{self.tool}").setChecked(True)
        self._pick_tool(self.tool)
        self._built = True
        self.refresh()

    # ---- helpers ---------------------------------------------------------------------
    def _say(self, text: str) -> None:
        self.status.setText(text)
        flash = getattr(self.app.viewport, "flash_status", None)
        if callable(flash):
            flash(text, 3500)

    def _clear_sel(self) -> None:
        self.sel = None
        self.extra = []

    def _sels(self) -> list:
        """Everything selected: the Shift-picked items and the current one."""
        out = list(self.extra)
        if self.sel and self.sel not in out:
            out.append(self.sel)
        return out

    def active_group(self):
        for g in self.app.scene.groups:
            if g.uid == self.active_uid and _state(g) is not None:
                return g
        return None

    def _sync(self) -> None:
        spec = subdiv_ops.SPECS[self.tool]
        self.hint.setText(f"<b>{T(spec.label)}</b> — {self._tip(spec)}")
        has_value = bool(spec.value_label)
        self.value_label.setText(T(spec.value_label) if spec.value_label else "")
        self.value_label.setVisible(has_value)
        self.value.setVisible(has_value)
        self.axis.setVisible(spec.axis)
        self.side.setVisible(self.tool == "shell")
        self.cut.setVisible(self.tool == "divide")
        self.ends.setVisible(self.tool in ("loft", "sweep"))
        self.twist.setVisible(self.tool == "loft")
        suffix = T("  (waiting for the second opening)") if self.pending else ""
        self.selection_label.setText(subdiv_ops.describe_many(self._sels()) + suffix
                                     + self._loose_note())
        self._refresh_auto_ghost()

    PREVIEW_TOOLS = ("loft", "sweep", "revolve")
    _auto_ghost = None

    def _refresh_auto_ghost(self) -> None:
        """Loft, Sweep and Revolve show what they would make as soon as what they need is
        selected, before Apply, so you see at once whether it works."""
        ghost = None
        if not getattr(self, "_built", False):                  # the panel is still being made
            return
        if self.tool in self.PREVIEW_TOOLS and self._box_dlg is None and self._live is None:
            try:
                _g, cg, _lv, _ln, _res = self._compute()
                verts, faces = cg.smooth(1 if len(cg.faces) > 150 else 2)
                ghost = (verts, {(min(f[i], f[(i + 1) % len(f)]), max(f[i], f[(i + 1) % len(f)]))
                                 for f in faces for i in range(len(f))})
            except Exception:                                    # noqa: BLE001
                ghost = None
        if ghost is not None or self._auto_ghost is not None:
            self._auto_ghost = ghost
            self.app.viewport.update()

    def cancel_tool(self) -> bool:
        """Esc: leave the tool and make nothing (back to Edit cage, nothing selected)."""
        busy = (self.tool != "edit" or self.pending is not None or self._auto_ghost is not None
                or self._bridge_first is not None)
        if not busy:
            return False
        self.pending = None
        self._bridge_first = None
        self._auto_ghost = None
        if self.tool != "edit":
            btn = getattr(self, "_btn_edit", None)
            if btn is not None:
                btn.setChecked(True)
            self._pick_tool("edit")
        self._clear_sel()
        vp = self.app.viewport
        vp.clear_extension_pick()
        try:
            vp.scene.select([])
        except Exception:                                        # noqa: BLE001
            pass
        self._say(T("Cancelled — nothing made"))
        vp.update()
        return True

    def _loose_note(self) -> str:
        """What plain drawing Loft / Sweep / Revolve will use (so you see it was seen)."""
        if self.tool not in ("loft", "sweep", "revolve"):
            return ""
        try:
            loops, segments = self._loose()
        except Exception:                                    # noqa: BLE001
            return ""
        if not loops and not segments:
            return ""
        return "  |  " + T("Drawing: {f} face(s), {l} line(s)", f=len(loops), l=len(segments))

    def _unit_name(self) -> str:
        """The unit the value box shows, in words (the help texts use it)."""
        word = {"m": "metres", "cm": "centimetres", "mm": "millimetres", "ft": "feet"}.get(
            self._unit, "inches" if self._unit in _SUFFIX else "metres")
        return T(word)

    def _tip(self, spec) -> str:
        """A tool's help text, in the panel's language and the document's unit."""
        return T(spec.tip, unit=self._unit_name()) if "{unit}" in spec.tip else T(spec.tip)
        self.apply_btn.setEnabled(True)
        self.app.viewport.update()

    # ---- tool choice -----------------------------------------------------------------
    def _decimals(self) -> int:
        try:
            return max(0, min(4, int(units.model_precision())))
        except Exception:                                    # noqa: BLE001
            return 2

    def _configure_value(self, metres: float | None = None) -> None:
        """Set the value box for the current tool, in the document's unit."""
        spec = subdiv_ops.SPECS[self.tool]
        if not spec.value_label:
            return
        sc = self._scale if spec.length else 1.0
        self.value.blockSignals(True)
        self.value.setDecimals(self._decimals() if spec.length
                               else (0 if spec.step >= 1 else 2))
        self.value.setRange(spec.lo / sc, spec.hi / sc)
        self.value.setSingleStep(spec.step / sc)
        self.value.setSuffix(_SUFFIX.get(self._unit, " m") if spec.length else "")
        self.value.setValue((spec.default if metres is None else metres) / sc)
        self.value.blockSignals(False)
        if self.tool == "crease" and metres is None:
            self._crease_auto = None
            self._follow_levels()

    def _follow_levels(self) -> None:
        """Crease starts at the smoothing level, so the edge stays crisp unless the
        user picks a smaller value (which is then left alone)."""
        if self.tool != "crease" or not hasattr(self, "levels"):
            return
        lv = float(self.levels.value())
        if self._crease_auto is None or float(self.value.value()) == self._crease_auto:
            self.value.blockSignals(True)
            self.value.setValue(lv)
            self.value.blockSignals(False)
            self._crease_auto = lv

    def _metres(self) -> float:
        """The value box, converted to metres (lengths) or as is (factors)."""
        spec = subdiv_ops.SPECS[self.tool]
        v = float(self.value.value())
        return v * self._scale if spec.length else v

    def _soft(self) -> float:
        """The soft-selection radius in metres (0 when the box is unticked)."""
        if not self.soft_box.isChecked():
            return 0.0
        return float(self.soft_radius.value()) * self._scale

    def _refresh_tips(self) -> None:
        """Tool tips follow the document's unit (the hint line is set by _sync)."""
        for b, spec in zip(self.buttons.buttons(), subdiv_ops.TOOL_SPECS):
            b.setToolTip(f"{T(spec.label)} — {self._tip(spec)}")

    def _units_refresh(self) -> None:
        """Follow the document's unit (mm, cm, in…): the model itself is metres."""
        try:
            unit, scale = units.model_unit(), float(units.bare_number_scale())
        except Exception:                                    # noqa: BLE001
            unit, scale = "m", 1.0
        if unit != self._unit or abs(scale - self._scale) > 1e-12:
            keep = self._metres() if self._unit is not None else None
            soft_m = float(self.soft_radius.value()) * self._scale if self._unit is not None else 0.5
            self._unit, self._scale = unit, scale
            self._configure_value(keep)
            self.soft_radius.blockSignals(True)          # the soft radius is a length too
            self.soft_radius.setDecimals(self._decimals())
            self.soft_radius.setRange(0.0001 / scale, 1000.0 / scale)
            self.soft_radius.setSingleStep(0.05 / scale)
            self.soft_radius.setSuffix(_SUFFIX.get(unit, " m"))
            self.soft_radius.setValue(soft_m / scale)
            self.soft_radius.blockSignals(False)
            if not self._building:              # the help text names the unit
                self._refresh_tips()
                self._sync()

    def _pick_tool(self, key: str) -> None:
        if key != self.tool:
            self.pending = None
            self._bridge_first = None
        self.tool = key
        if key == "slice" and self.axis.currentData() not in AXIS_VEC:
            self.axis.setCurrentIndex(self.axis.findData("z"))     # so the plane shows at once
        self._units_refresh()
        self._configure_value()
        self._sync()

    # ---- plain drawing (faces and lines outside any SubD group) as input --------------------
    @staticmethod
    def _xyz_of(v):
        return (float(v.x()), float(v.y()), float(v.z()))

    def _loose(self):
        """``(loops, segments)`` of the plain faces and lines selected in the model:
        each face as its corner points, each line as two points."""
        loops, segments = [], []
        for it in list(self.app.scene.selection):
            if hasattr(it, "mesh") or hasattr(it, "groups"):
                continue                                  # a group, not drawing
            try:
                if hasattr(it, "vertices"):
                    loops.append([self._xyz_of(v) for v in it.vertices])
                elif hasattr(it, "a") and hasattr(it, "b"):
                    segments.append((self._xyz_of(it.a), self._xyz_of(it.b)))
            except Exception:                                    # noqa: BLE001
                continue
        return loops, segments

    def _loose_for_tool(self):
        """For Loft and Sweep: the plain drawing to use, or None when the SubD
        selection is already enough (or there is no usable drawing)."""
        if self.tool not in ("loft", "sweep", "revolve"):
            return None
        sels = self._sels()
        if self.tool == "revolve":
            if sels and sels[0][0] == "f":
                return None
            loops, segments = self._loose()
            return (loops, segments) if (loops or segments) else None
        nf = sum(1 for x in sels if x and x[0] == "f")
        ne = sum(1 for x in sels if x and x[0] == "e")
        if self.tool == "loft" and nf >= 2:
            return None
        if self.tool == "sweep" and nf == 1 and ne >= 1:
            return None
        loops, segments = self._loose()
        if self.tool == "loft":
            return (loops, []) if nf + len(loops) >= 2 else None
        if (nf + len(loops)) >= 1 and (segments or ne):
            return loops, segments
        return None

    # ---- right-click menu ---------------------------------------------------------------
    MENU_TOOLS = {
        "v": ("edit", "crease", "merge", "dissolve"),
        "e": ("edit", "crease", "grow_edge", "offset_edge", "squeeze", "divide", "bevel",
              "slide", "loft", "sweep", "bridge", "merge", "dissolve"),
        "f": ("edit", "grow_face", "inset_face", "stretch", "divide", "shell", "revolve",
              "bridge", "merge", "delete_face"),
    }

    def context_event(self, ev) -> bool:
        """Right-click on the SubD piece: our own menu, with only the SubD tools (the
        model's usual menu stays for everything else, or when this is switched off)."""
        if __import__('time').monotonic() < self._no_menu_until:
            return True                   # the right-click that just validated an adjustment
        if not self.menu_only.isChecked() or self.active_group() is None:
            return False
        x, y = float(ev.pos().x()), float(ev.pos().y())
        if self.pick_item(None, x, y) is None:
            return False
        from PySide6.QtWidgets import QMenu
        menu = QMenu(self.app.viewport)
        self.context_menu(menu, [], (x, y))
        if not menu.actions():
            return False
        menu.exec(ev.globalPos())
        return True

    def _set_levels(self, n) -> None:
        """Smoothing from the right-click menu: 0 to 4, or Auto."""
        if n is None:
            self.auto.setChecked(True)
        else:
            self.auto.setChecked(False)
            self.levels.setValue(int(n))
        self.update_look()

    def context_menu(self, menu, _selection, where=None) -> None:
        """Right-click on a point, edge or face of the active SubD piece (on the cage or
        on the skin): the tools that suit it. A tool that takes a value asks for it
        in a small box at the cursor, so the panel is not needed."""
        vp = self.app.viewport
        where = where or getattr(vp, "_context_pixel", None)
        if where is None:
            return
        self._menu_pos = vp.mapToGlobal(QPoint(int(where[0]), int(where[1])))
        g = self.active_group()
        hit = self.pick_item(None, float(where[0]), float(where[1])) if g is not None else None
        if hit is not None and hit not in self._sels():
            self.on_select(hit)
            vp.update()
        sels = self._sels()
        keys = []
        if hit is not None or sels:
            kind = (hit or sels[0])[0]
            keys = list(self.MENU_TOOLS.get(kind, ()))
        loops, segments = self._loose()
        if (loops or segments) and "revolve" not in keys:
            keys.append("revolve")
        if len(loops) >= 2 and "loft" not in keys:
            keys.append("loft")
        if (loops or sels) and segments and "sweep" not in keys:
            keys.append("sweep")
        if not keys and not self._clip:
            return
        for key in keys:
            spec = subdiv_ops.SPECS[key]
            act = menu.addAction(_icon(spec.icon), T(spec.label) + ("…" if self._takes_input(key) else ""))
            act.setToolTip(self._tip(spec))
            act.triggered.connect(lambda _c=False, k=key: QTimer.singleShot(0, lambda: self._run_tool(k)))
        if g is not None:
            menu.addSeparator()
            menu.addAction(T("Select all faces"), self.select_all_faces)
        if any(x and x[0] == "f" for x in sels):
            menu.addAction(T("Copy faces"), self.copy_faces)
        if self._clip:
            menu.addAction(T("Paste faces"), self.paste_faces)
        if g is not None:
            menu.addSeparator()
            a = menu.addAction(T("Symmetry"))
            a.setCheckable(True)
            a.setChecked(self.sym_box.isChecked())
            a.triggered.connect(lambda _c=False: self.sym_box.toggle())
            a = menu.addAction(T("Soft"))
            a.setCheckable(True)
            a.setChecked(self.soft_box.isChecked())
            a.triggered.connect(lambda _c=False: self.soft_box.toggle())
            sm = menu.addMenu(T("Smoothing"))
            cur = _state(g)[1]
            for n in range(5):
                a = sm.addAction(str(n))
                a.setCheckable(True)
                a.setChecked(not self.auto.isChecked() and cur == n)
                a.triggered.connect(lambda _c=False, k=n: QTimer.singleShot(0, lambda: self._set_levels(k)))
            a = sm.addAction(T("Auto"))
            a.setCheckable(True)
            a.setChecked(self.auto.isChecked())
            a.triggered.connect(lambda _c=False: QTimer.singleShot(0, lambda: self._set_levels(None)))
            act = menu.addAction(T("Hide cage") if self.show_cage.isChecked() else T("Show cage"))
            act.triggered.connect(lambda _c=False: self.show_cage.toggle())

    def _takes_input(self, key: str) -> bool:
        """Does the tool ask for a value or a choice (so the menu entry opens the box)?"""
        spec = subdiv_ops.SPECS[key]
        if spec.value_label or spec.axis:
            return True
        return key in ("shell", "divide", "loft", "sweep")

    def _run_tool(self, key: str) -> None:
        self._pick_tool(key)
        btn = getattr(self, f"_btn_{key}", None)
        if btn is not None:
            btn.setChecked(True)
        spec = subdiv_ops.SPECS[key]
        if self.live_box.isChecked() and key in self.LIVE_TOOLS and self._start_live(key):
            return
        if spec.value_label and key in self._last_value:      # the value last typed for it
            self.value.setValue(self._last_value[key])
        if spec.value_label or self._tool_combo() is not None:
            self._ask_value(spec, then=self.apply)
            return
        self.apply()

    def _tool_combo(self):
        """The panel's choice that goes with the current tool (wall side, cut style,
        ends, direction), or None."""
        if self.tool == "shell":
            return self.side
        if self.tool == "divide":
            return self.cut
        if self.tool in ("loft", "sweep"):
            return self.ends
        return self.axis if subdiv_ops.SPECS[self.tool].axis else None

    _box_dlg = None
    _box_pos = None

    def _ask_value(self, spec, then=None) -> None:
        """A small window with everything the tool asks for: its value and its choice
        (direction, wall side, cut style, ends), with a live preview. Drag it anywhere
        with the mouse; it stays open while you turn the view. Enter or Apply runs
        ``then``; Esc cancels and the panel keeps its values."""
        from PySide6.QtWidgets import QDialog
        if self._box_dlg is not None:
            self._box_dlg.close()
        label = T(subdiv_ops.SPECS[self.tool].label)

        class _Box(QDialog):
            def event(self, ev):                                  # noqa: N802
                if ev.type() == QEvent.ShortcutOverride and ev.key() in (
                        Qt.Key_Escape, Qt.Key_Return, Qt.Key_Enter):
                    ev.accept()                  # the model's own shortcuts must not take these
                    return True
                return super().event(ev)

            def keyPressEvent(self, ev):                          # noqa: N802
                if ev.key() in (Qt.Key_Return, Qt.Key_Enter):
                    self.accept()
                elif ev.key() == Qt.Key_Escape:
                    self.reject()
                else:
                    super().keyPressEvent(ev)

            def mousePressEvent(self, ev):                        # noqa: N802
                if ev.button() == Qt.LeftButton:
                    self._grab = ev.globalPosition().toPoint() - self.frameGeometry().topLeft()
                    handle = self.windowHandle()
                    try:                         # the system moves the window: smooth, no lag
                        if handle is not None and handle.startSystemMove():
                            self._grab = None
                    except Exception:                                # noqa: BLE001
                        pass

            def mouseMoveEvent(self, ev):                         # noqa: N802
                if ev.buttons() & Qt.LeftButton and getattr(self, "_grab", None) is not None:
                    self.move(ev.globalPosition().toPoint() - self._grab)

            def mouseReleaseEvent(self, ev):                      # noqa: N802
                self._grab = None

        dlg = _Box(self.app.viewport.window(), Qt.Tool | Qt.FramelessWindowHint)
        dlg.setAttribute(Qt.WA_DeleteOnClose)
        dlg.setCursor(Qt.SizeAllCursor)
        dlg.setStyleSheet("QDialog { border: 1px solid #888; }")
        col = QVBoxLayout(dlg)
        col.setContentsMargins(10, 8, 10, 8)
        grip = QLabel(f"<b>{label}</b>   ⠿⠿⠿")
        grip.setStyleSheet("background: #e4e4e4; padding: 4px 6px;")
        col.addWidget(grip)
        box = None
        if spec.value_label:
            row = QHBoxLayout()
            row.addWidget(QLabel(T(spec.value_label)))
            box = QDoubleSpinBox()
            box.setCursor(Qt.ArrowCursor)
            box.setDecimals(self.value.decimals())
            box.setRange(self.value.minimum(), self.value.maximum())
            box.setSingleStep(self.value.singleStep())
            box.setSuffix(self.value.suffix())
            box.setValue(self.value.value())
            box.setMinimumWidth(110)
            box.setKeyboardTracking(False)
            row.addWidget(box, 1)
            col.addLayout(row)
        src = self._tool_combo()
        combo = None
        if src is not None:
            combo = QComboBox()
            combo.setCursor(Qt.ArrowCursor)
            for i in range(src.count()):
                combo.addItem(src.itemText(i), src.itemData(i))
            combo.setCurrentIndex(src.currentIndex())
            col.addWidget(combo)
        twist = None
        if self.tool == "loft":
            row = QHBoxLayout()
            row.addWidget(QLabel(T("Twist")))
            twist = QDoubleSpinBox()
            twist.setCursor(Qt.ArrowCursor)
            twist.setDecimals(0)
            twist.setRange(-360.0, 360.0)
            twist.setSingleStep(15.0)
            twist.setSuffix(" °")
            twist.setValue(self.twist.value())
            twist.setKeyboardTracking(False)
            row.addWidget(twist, 1)
            col.addLayout(row)
        radius = None
        if self.tool == "edit" and self.soft_box.isChecked():
            row = QHBoxLayout()
            row.addWidget(QLabel(T("Soft")))
            radius = QDoubleSpinBox()
            radius.setCursor(Qt.ArrowCursor)
            radius.setDecimals(self.soft_radius.decimals())
            radius.setRange(self.soft_radius.minimum(), self.soft_radius.maximum())
            radius.setSuffix(self.soft_radius.suffix())
            radius.setValue(self.soft_radius.value())
            row.addWidget(radius, 1)
            col.addLayout(row)
        hint = QHBoxLayout()
        hint.addWidget(QLabel(T("Enter applies, Esc cancels")), 1)
        ok = QPushButton(T("Apply"))
        ok.setCursor(Qt.ArrowCursor)
        ok.clicked.connect(dlg.accept)
        hint.addWidget(ok)
        col.addLayout(hint)
        saved = (self.value.value(), src.currentIndex() if src is not None else None,
                 self.twist.value())

        def preview(*_a):
            """Show the result for what the window holds, while it is still open."""
            self.value.blockSignals(True)
            if box is not None:
                self.value.setValue(box.value())
            self.value.blockSignals(False)
            if twist is not None:
                self.twist.blockSignals(True)
                self.twist.setValue(twist.value())
                self.twist.blockSignals(False)
            if combo is not None:
                src.blockSignals(True)
                src.setCurrentIndex(combo.currentIndex())
                src.blockSignals(False)
            try:
                _g, cg, _lv, _ln, _res = self._compute()
                verts, faces = cg.smooth(1 if len(cg.faces) > 150 else 2)
                self._box_ghost = (verts, {(min(f[i], f[(i + 1) % len(f)]), max(f[i], f[(i + 1) % len(f)]))
                                           for f in faces for i in range(len(f))})
            except ValueError:
                self._box_ghost = None
            self.app.viewport.update()
        if box is not None:
            box.valueChanged.connect(preview)
        if combo is not None:
            combo.currentIndexChanged.connect(preview)
        if twist is not None:
            twist.valueChanged.connect(preview)

        def done(accepted: bool):
            self._box_pos = dlg.pos()
            self._box_dlg = None
            self._box_ghost = None
            self.app.viewport.update()
            if not accepted:
                self.value.blockSignals(True)
                self.value.setValue(saved[0])
                self.value.blockSignals(False)
                if src is not None and saved[1] is not None:
                    src.setCurrentIndex(saved[1])
                self.twist.setValue(saved[2])
                return
            if box is not None:
                box.interpretText()
                self.value.setValue(box.value())
                self._last_value[self.tool] = box.value()
            if combo is not None:
                src.setCurrentIndex(combo.currentIndex())
            if radius is not None:
                radius.interpretText()
                self.soft_radius.setValue(radius.value())
            if twist is not None:
                twist.interpretText()
                self.twist.setValue(twist.value())
            if then is not None:
                QTimer.singleShot(0, then)
        dlg.accepted.connect(lambda: done(True))
        dlg.rejected.connect(lambda: done(False))
        self._box_dlg = dlg
        for lab in dlg.findChildren(QLabel):            # grab the box by any text, not just the title
            lab.setAttribute(Qt.WA_TransparentForMouseEvents)
        dlg.move(self._box_pos or getattr(self, "_menu_pos", dlg.pos()) + QPoint(24, 24))
        dlg.show()
        dlg.raise_()
        dlg.activateWindow()
        first = box or combo
        QTimer.singleShot(0, lambda: (first.setFocus(), box.selectAll() if box else None))
        QTimer.singleShot(0, preview)

    # ---- live adjustment: move the mouse, see the result, click ------------------------
    LIVE_TOOLS = ("edit", "crease", "grow_face", "grow_edge", "stretch", "inset_face",
                  "offset_edge", "squeeze", "shell", "bevel", "slice", "slide", "merge")
    _live = None
    _no_menu_until = 0.0
    _box_ghost = None

    def _live_value(self, spec, v0: float, d_px: float, mods) -> float:
        """The value for a mouse travel of ``d_px`` pixels (right or up = more)."""
        if mods & Qt.ShiftModifier:
            d_px /= 5.0                                        # fine
        key = spec.key
        if spec.length:
            v = v0 + self._world_len(self._live["centre"], 1.0) * d_px
        elif key in ("stretch", "squeeze"):
            v = v0 * math.exp(d_px / 150.0)
        elif key == "crease":
            v = v0 + d_px / 25.0 * spec.step
        else:
            v = v0 + d_px / 6.0 * spec.step
        v = min(spec.hi, max(spec.lo, v))
        if mods & Qt.ControlModifier and spec.step > 0:
            v = round(v / spec.step) * spec.step
        return v

    def _start_live(self, key: str) -> bool:
        spec = subdiv_ops.SPECS[key]
        g = self.active_group()
        sels = self._sels()
        if g is None or not sels:
            return False
        cage = _state(g)[0]
        idx = subdiv_ops.vertex_union(cage, [x for x in sels if subdiv_ops.valid(cage, x)])
        if not idx:
            return False
        pts = [cage.verts[i] for i in idx]
        centre = tuple(sum(p[k] for p in pts) / len(pts) for k in range(3))
        v0 = 0.0 if key == "slide" else self._last_value.get(key, spec.default)
        vp = self.app.viewport
        self._live = {"key": key, "spec": spec, "v0": v0, "v": v0, "centre": centre,
                      "start": None, "pos": None, "ghost": None, "err": None,
                      "track": vp.hasMouseTracking()}
        vp.setMouseTracking(True)
        self._live_preview(v0)
        self._say(T("Move the mouse to set the value. Click to apply, Enter for an exact value, Esc to cancel"))
        vp.update()
        return True

    def _live_preview(self, v: float) -> None:
        live = self._live
        spec = live["spec"]
        sc = self._scale if spec.length else 1.0
        self.value.blockSignals(True)
        self.value.setValue(v / sc)
        self.value.blockSignals(False)
        live["v"] = v
        try:
            _g, cage, _lv, _ln, _res = self._compute()
            verts, faces = cage.smooth(1 if len(cage.faces) > 150 else 2)
            live["ghost"] = (verts, {(min(f[i], f[(i + 1) % len(f)]), max(f[i], f[(i + 1) % len(f)]))
                                     for f in faces for i in range(len(f))})
            live["err"] = None
        except ValueError as exc:
            live["ghost"] = None
            live["err"] = str(exc)

    def live_move(self, ev) -> bool:
        live = self._live
        pos = ev.position()
        live["pos"] = (pos.x(), pos.y())
        if live["start"] is None:
            live["start"] = live["pos"]
        d = (pos.x() - live["start"][0]) - (pos.y() - live["start"][1])
        self._live_preview(self._live_value(live["spec"], live["v0"], d, ev.modifiers()))
        self.app.viewport.update()
        return True

    def _end_live(self) -> None:
        live, self._live = self._live, None
        if live is not None:
            self.app.viewport.setMouseTracking(live["track"])
        self.app.viewport.update()

    def live_confirm(self, right: bool = False) -> bool:
        if right:
            self._no_menu_until = __import__('time').monotonic() + 0.6
        live = self._live
        if live is None:
            return False
        if live["err"]:
            self._say(live["err"])
            self._end_live()
            return True
        key, v = live["key"], live["v"]
        self._end_live()
        sc = self._scale if live["spec"].length else 1.0
        self._last_value[key] = v
        self.value.setValue(v / sc)
        self._swallow = True
        self.apply()
        return True

    def live_cancel(self) -> bool:
        if self._live is None:
            return False
        self._end_live()
        self._configure_value()
        self._say(T("Cancelled"))
        return True

    def live_exact(self) -> bool:
        """Enter while adjusting: type the exact value in the small box."""
        live = self._live
        if live is None:
            return False
        spec = live["spec"]
        self._end_live()
        self._last_value[live["key"]] = live["v"]
        sc = self._scale if spec.length else 1.0
        self.value.setValue(live["v"] / sc)
        self._ask_value(spec, then=self.apply)
        return True

    def live_key(self, key) -> bool:
        """X, Y, Z while adjusting set the direction."""
        names = {Qt.Key_X: "x", Qt.Key_Y: "y", Qt.Key_Z: "z", Qt.Key_A: "auto"}
        live = self._live
        if key not in names or not live["spec"].axis or self._tool_combo() is not self.axis:
            return False
        i = self.axis.findData(names[key])
        if i >= 0:
            self.axis.setCurrentIndex(i)
            pos = live["pos"]
            if live["start"] is not None and pos is not None:
                d = (pos[0] - live["start"][0]) - (pos[1] - live["start"][1])
                self._live_preview(self._live_value(live["spec"], live["v0"], d, Qt.NoModifier))
            self.app.viewport.update()
        return True

    def _draw_live(self, painter) -> None:
        if self._box_ghost is not None:
            self._draw_ghost(painter, self._box_ghost)
        elif self._auto_ghost is not None and self._live is None:
            self._draw_ghost(painter, self._auto_ghost)
        live = self._live
        if live is None:
            return
        if live["ghost"] is not None:
            self._draw_ghost(painter, live["ghost"])
        if live["pos"] is None:
            return
        spec = live["spec"]
        sc = self._scale if spec.length else 1.0
        v = live["v"] / sc
        suffix = _SUFFIX.get(self._unit, " m") if spec.length else ""
        dec = self._decimals() if spec.length else (0 if spec.step >= 1 else 2)
        text = f"{T(subdiv_ops.SPECS[live['key']].label)}   {v:.{dec}f}{suffix}"
        if live["err"]:
            text = live["err"]
        x, y = live["pos"]
        fm = painter.fontMetrics()
        w = fm.horizontalAdvance(text) + 16
        painter.setPen(QPen(QColor(30, 30, 30), 1.0))
        painter.setBrush(QBrush(QColor(255, 255, 255, 235)))
        painter.drawRoundedRect(x + 18, y + 14, w, 24, 5, 5)
        painter.drawText(int(x + 18), int(y + 14), int(w), 24, int(Qt.AlignCenter), text)

    # ---- copy / paste of cage faces ------------------------------------------------------
    _clip = None                       # a Cage holding the copied faces
    _last_value: dict = {}             # per tool, the value last typed in the right-click box
    _clip_owner = False                # True while our copy is the latest one

    def _has_face_sel(self) -> bool:
        return self.active_group() is not None and any(
            x and x[0] == "f" for x in self._sels())

    def _has_clip_focus(self) -> bool:
        return bool(self._clip_owner)

    def select_all_faces(self) -> None:
        g = self.active_group()
        if g is None:
            return
        n = len(_state(g)[0].faces)
        if n:
            self.sel = ("f", 0)
            self.extra = [("f", i) for i in range(1, n)]
            self._say(T("All {n} faces selected: Ctrl + drag a move handle copies the piece", n=n))
            self.app.viewport.update()

    def copy_faces(self) -> bool:
        g = self.active_group()
        faces = sorted({x[1] for x in self._sels() if x and x[0] == "f"})
        if g is None or not faces:
            return False
        cage = _state(g)[0]
        faces = [f for f in faces if f < len(cage.faces)]
        self._clip = cage.extract(faces)
        self._clip_owner = True
        self._say(T("Copied {n} faces: Ctrl+V pastes them as a new SubD piece", n=len(faces)))
        return True

    def paste_faces(self) -> bool:
        if not self._clip or not self._clip.faces:
            self._say(T("Nothing to paste: select SubD faces and press Ctrl+C first"))
            return False
        cage = self._clip.copy()
        self.pending = None
        self._commit(None, cage, int(self.levels.value()), self.lines.currentData())
        n = len(cage.faces)
        self.sel = ("f", 0)
        self.extra = [("f", i) for i in range(1, n)]
        self._say(T("Pasted {n} faces as a new SubD piece: move it with the handles", n=n))
        self.app.viewport.update()
        return True

    # ---- document / selection --------------------------------------------------------
    def refresh(self) -> None:
        """Called on every document change (edit, undo, New, Open)."""
        self._units_refresh()
        found = [g for g in self.app.scene.groups if _state(g) is not None]
        self.groups.blockSignals(True)
        self.groups.clear()
        for g in found:
            self.groups.addItem(g.name, g.uid)
        if found and self.active_uid not in [g.uid for g in found]:
            self.active_uid = found[-1].uid
            self.pending = None
        idx = self.groups.findData(self.active_uid)
        if idx >= 0:
            self.groups.setCurrentIndex(idx)
        self.groups.blockSignals(False)
        self.join_with.blockSignals(True)
        keep_join = self.join_with.currentData()
        self.join_with.clear()
        for other in found:
            if other.uid != self.active_uid:
                self.join_with.addItem(other.name, other.uid)
        j = self.join_with.findData(keep_join)
        if j >= 0:
            self.join_with.setCurrentIndex(j)
        self.join_with.blockSignals(False)
        self.convertible.blockSignals(True)
        keep = self.convertible.currentData()
        self.convertible.clear()
        for other in self.app.scene.groups:
            if _state(other) is None and getattr(other, "xform", None) is None:
                self.convertible.addItem(other.name, other.uid)
        j = self.convertible.findData(keep)
        if j >= 0:
            self.convertible.setCurrentIndex(j)
        self.convertible.blockSignals(False)
        g = self.active_group()
        if g is None:
            self._clear_sel()
        elif self.sel is not None and not subdiv_ops.valid(_state(g)[0], self.sel):
            self._clear_sel()
        else:
            self.extra = [x for x in self.extra if subdiv_ops.valid(_state(g)[0], x)]
        if g is not None:
            _cage, levels, lines = _state(g)
            self.sym_box.blockSignals(True)
            self.sym_box.setChecked(bool(_cage.sym and _cage.sym["on"]))
            self.sym_box.blockSignals(False)
            self.levels.blockSignals(True)
            self.levels.setValue(levels)
            self.levels.blockSignals(False)
            self._follow_levels()
            i = self.lines.findData(lines)
            if i >= 0:
                self.lines.setCurrentIndex(i)
        self._sync()

    def _on_auto(self, on: bool) -> None:
        self.levels.setEnabled(not on)

    def _on_group_chosen(self, _i: int) -> None:
        if self._building:
            return
        self.active_uid = self.groups.currentData()
        self._clear_sel()
        self.pending = None
        self.refresh()

    def on_select(self, item) -> None:
        """The viewport tells us what the user clicked (None = let go)."""
        self.sel = item
        self.extra = []
        if self.tool == "bridge" and item is not None and item[0] in "fe":
            first = self._bridge_first
            if first is None or first == item:
                self._bridge_first = item
                self._say(T("Bridge: now click the other face (or an edge of the other opening)"))
            else:                                     # second click: bridge straight away
                self.extra = [first]
                self.apply()
                self._auto_bridged = True
                self._bridge_first = item if self.sel is not None else None
                self.extra = []
        elif self.tool != "bridge":
            self._bridge_first = None
        self._sync()

    def delete_item(self, item) -> None:
        """Supr on a selected SubD item removes just that: a face, the faces on an
        edge, or the faces around a point. The rest of the piece stays (one undo step)."""
        g = self.active_group()
        if g is None or item is None:
            return
        cage, levels, lines = _state(g)
        cage = cage.copy()
        kind, idx = item[0], item[1]
        if kind == "f":
            drop = {idx}
        elif kind == "e":
            a, b = item[1], item[2]
            drop = {i for i, f in enumerate(cage.faces)
                    if any({f[k], f[(k + 1) % len(f)]} == {a, b} for k in range(len(f)))}
        else:                                          # a point
            drop = {i for i, f in enumerate(cage.faces) if idx in f}
        if not drop or len(drop) >= len(cage.faces):
            self._say(T("A cage needs at least one face"))
            return
        cage.remove_faces(drop)
        cage.prune()
        self._commit(g, cage, levels, lines)
        self._clear_sel()
        self._say(T("Deleted — Ctrl+Z brings it back"))
        self._sync()

    def _activate_under(self, px: float, py: float) -> bool:
        """A press on a point of another SubD group's cage makes that group
        the active one (unless the active cage is hit first)."""
        if self.pick_item(None, px, py) is not None:
            return False
        for other in self._others():
            cage = _state(other)[0]
            xs, ys, front = self.app.world_to_pixels(np.array(cage.verts, dtype=float))
            hit = bool(subdiv_ops.pick(cage, xs.tolist(), ys.tolist(), front.tolist(), px, py))
            if not hit and self.skin_pick.isChecked():          # its skin works too
                hit = self._pick_on_skin(other, px, py) is not None
            if hit:
                self.active_uid = other.uid
                self._clear_sel()
                self.pending = None
                return True
        return False

    def _section(self, parent, title: str):
        """A collapsible block (closed at first): returns its inner layout."""
        head = QToolButton()
        head.setText(title)
        head.setCheckable(True)
        head.setChecked(False)
        head.setAutoRaise(True)
        head.setArrowType(Qt.RightArrow)
        head.setToolButtonStyle(Qt.ToolButtonTextBesideIcon)
        body = QWidget()
        body.setVisible(False)
        inner = QVBoxLayout(body)
        inner.setContentsMargins(0, 0, 0, 0)

        def toggle(on, h=head, b=body):
            h.setArrowType(Qt.DownArrow if on else Qt.RightArrow)
            b.setVisible(on)
        head.toggled.connect(toggle)
        parent.addWidget(head)
        parent.addWidget(body)
        return inner

    def _skin_mode_changed(self) -> None:
        self._skin = None
        self.app.viewport.update()

    def _skin_of(self, g):
        """The smooth surface of the active group, rebuilt only when the cage or
        the smoothing level has changed."""
        cage, levels = _state(g)[0], _state(g)[1]
        key = (g.uid, levels, hash((tuple(cage.verts), tuple(map(tuple, cage.faces)),
                                    tuple(sorted(cage.creases.items())),
                                    tuple(sorted(cage.vcreases.items())))))
        if self._skin is None or self._skin[0] != key:
            self._skin = (key, subdiv_ops.build_skin(cage, levels))
        return self._skin[1]

    def _pick_on_skin(self, g, px: float, py: float, skip=()):
        cage = _state(g)[0]
        skin = self._skin_of(g)
        try:
            o, d = self.app.viewport._pixel_to_ray(px, py)
        except Exception:                                        # noqa: BLE001
            return None
        if o is None or d is None:
            return None
        xs, ys, front = self.app.world_to_pixels(skin.verts)
        return subdiv_ops.pick_skin(cage, skin, xs, ys, front,
                                    px, py, (self._xyz(o), self._xyz(d)), skip=skip)

    def pick_item(self, viewport, px: float, py: float, skip=()):
        g = self.active_group()
        if g is None:
            return None
        if self.show_cage.isChecked():
            hit = self._pick_on_cage(g, px, py, skip)
            if hit is not None and (hit[0] != "f" or not self.skin_pick.isChecked()):
                return hit                     # a cage point or edge you aimed at
            if not self.skin_pick.isChecked():
                return hit
        if self.skin_pick.isChecked():
            return self._pick_on_skin(g, px, py, skip)
        return None

    def _pick_on_cage(self, g, px: float, py: float, skip=()):
        cage = _state(g)[0]
        xs, ys, front = self.app.world_to_pixels(np.array(cage.verts, dtype=float))
        ray = None
        try:                                    # lets the face nearest the viewer win
            o, d = self.app.viewport._pixel_to_ray(px, py)
            if o is not None and d is not None:
                ray = (self._xyz(o), self._xyz(d))
        except Exception:                                        # noqa: BLE001
            ray = None
        return subdiv_ops.pick(cage, xs.tolist(), ys.tolist(), front.tolist(), px, py,
                               ray=ray, skip=skip)

    # ---- changing the model ----------------------------------------------------------
    FAST_TRIS = 2500           # triangles of the light surface shown while you work
    REFINE_MS = 450            # the full surface is built after this long without an edit

    def _commit(self, old, cage: Cage, levels: int, lines: str, final: bool = False) -> None:
        vp = self.app.viewport
        if not cage.is_consistent():
            cage.orient()                   # mixed winding shows as blue back faces
        if self.auto.isChecked():
            levels = subdiv_group.auto_levels(cage)
        light = levels
        if not final and self.fast_edit.isChecked() and levels > 1:
            light = 1
            for lv in range(levels, 0, -1):
                if subdiv_group.triangle_count(cage, lv) <= self.FAST_TRIS:
                    light = lv
                    break
        name = old.name if old is not None else "SubD"
        new = subdiv_group.build_group(cage, light, Group, Mesh, QVector3D,
                                       name=name, lines=lines)
        if light != levels:                 # the group remembers the real smoothing
            new.ext[subdiv_group.KEY]["levels"] = int(levels)
        if old is not None:
            subdiv_group.carry_over(old, new)
        cmd = _Swap(old, new)
        self._refine_gen += 1
        vp.history.execute(cmd)
        err = getattr(vp.history, "last_error", None)
        if err:
            self._say(T("Could not apply: {err}", err=err))
            return
        self.active_uid = new.uid
        notify = getattr(vp, "notify_scene_changed", None)
        if callable(notify):
            notify()
        vp.update()
        if light != levels:
            gen = self._refine_gen
            QTimer.singleShot(self.REFINE_MS, lambda: self._refine(gen, cmd, new, cage, levels, lines))

    _refine_gen = 0

    def _refine(self, gen, cmd, light, cage: Cage, levels: int, lines: str) -> None:
        """Pause reached: swap the light surface for the full one, inside the same undo step."""
        vp = self.app.viewport
        try:
            if gen != self._refine_gen or self._drag is not None or self._live is not None \
                    or self._box_dlg is not None:
                if gen == self._refine_gen:               # busy: look again shortly
                    QTimer.singleShot(self.REFINE_MS, lambda: self._refine(gen, cmd, light, cage,
                                                                           levels, lines))
                return
            groups = vp.scene.groups
            stack = getattr(vp.history, "undo_stack", [])
            if light not in groups or not stack or stack[-1] is not cmd:
                if light in groups:                       # another action came first
                    self._say(T("Light surface kept: press Update look for the full smoothing"))
                return
            full = subdiv_group.build_group(cage, levels, Group, Mesh, QVector3D,
                                            name=light.name, lines=lines)
            subdiv_group.carry_over(light, full)
            groups[groups.index(light)] = full
            cmd.new = full
            vp.scene.version += 1
            if self.active_uid == light.uid:              # (the same uid: just keep it)
                self.active_uid = full.uid
            notify = getattr(vp, "notify_scene_changed", None)
            if callable(notify):
                notify()
            vp.update()
        except Exception:                                  # noqa: BLE001
            log.exception(T("SubD drag failed"))

    def _finish_levels(self, cage, levels: int) -> int:
        """The smoothing level to finish with, from the Finish detail menu."""
        pick = self.finish_detail.currentData()
        if pick == "auto":
            return max(1, subdiv_group.auto_levels(cage, FINISH_BUDGET))
        return pick or levels

    def _mode(self) -> str:
        """The combo that goes with the current tool: wall side for Shell, cut
        style for Divide, the axis for the rest."""
        if self.tool == "shell":
            return self.side.currentData()
        if self.tool == "divide":
            return self.cut.currentData()
        if self.tool in ("loft", "sweep"):
            return self.ends.currentData()
        return self.axis.currentData()

    def _apply_many(self, cage: Cage):
        """Several items are selected: Edit cage moves them together along the
        chosen axis, and Crease sets the sharpness of all their edges."""
        if self.tool == "crease":                      # round off / sharpen them all
            return subdiv_ops.crease_items(cage, self._sels(), self._metres())
        if self.tool == "grow_edge":                   # a whole contour (repeated click)
            return subdiv_ops.grow_items(cage, self._sels(), self._metres(),
                                         self.axis.currentData())
        if self.tool == "squeeze":                     # a whole contour, or any selection
            return subdiv_ops.squeeze_items(cage, self._sels(), self._metres(),
                                            self.axis.currentData())
        if self.tool == "bevel":                       # every edge of a loop
            return subdiv_ops.bevel_items(cage, self._sels(), self._metres())
        if self.tool == "slide":
            return subdiv_ops.slide_items(cage, self._sels(), self._metres())
        if self.tool == "loft":
            return subdiv_ops.loft_items(cage, self._sels(), self._metres(), self._mode(),
                                         twist_deg=float(self.twist.value()))
        if self.tool == "sweep":
            return subdiv_ops.sweep_items(cage, self._sels(), self._metres(), self._mode())
        if self.tool == "bridge":                      # click one end, Shift+click the other
            sels = self._sels()
            if len(sels) != 2:
                raise ValueError(T("Bridge: select two faces (click one, Shift+click the other)"))
            return subdiv_ops.bridge_two(cage, sels[0], sels[1], self._metres())
        if self.tool != "edit":
            raise ValueError(T("Several items are selected: use Edit cage, Crease, Bevel, "
                             "Slide, Loft or Sweep on them, or click one item for this tool"))
        vec = AXIS_VEC.get(self.axis.currentData())
        if vec is None:
            raise ValueError(T("Choose X, Y or Z to move several items together"))
        delta = tuple(c * self._metres() for c in vec)
        subdiv_ops.symmetric_move(cage, subdiv_ops.vertex_union(cage, self._sels()),
                                  delta, cage.sym, self._soft())
        return subdiv_ops.Result(None, "Moved")

    def _compute(self):
        """Run the current tool on a copy of the cage: ``(group, cage, levels, lines,
        result)``. Nothing is changed in the model."""
        g = self.active_group()
        loose = self._loose_for_tool()
        if g is None and loose is None:
            raise ValueError(T("Create a SubD box first, or choose a SubD group"))
        if g is None:
            cage, levels, lines = Cage(), int(self.levels.value()), self.lines.currentData()
        else:
            cage, levels, lines = _state(g)
            cage = cage.copy()
        if loose is not None:
            loops, segments = loose
            if self.tool == "revolve":
                res = subdiv_ops.revolve_loose(cage, self._sels(), loops, segments,
                                               self._metres(), self._mode())
            elif self.tool == "loft":
                res = subdiv_ops.loft_loose(cage, self._sels(), loops, self._metres(),
                                            self._mode(), twist_deg=float(self.twist.value()))
            else:
                res = subdiv_ops.sweep_loose(cage, self._sels(), loops, segments,
                                             self._metres(), self._mode())
        elif self.extra:
            res = self._apply_many(cage)
        else:
            res = subdiv_ops.apply_tool(
                cage, self.tool, self.sel, self._metres(),
                self._mode(), self.pending, sym=cage.sym, soft=self._soft())
        return g, cage, levels, lines, res

    def apply(self) -> None:
        try:
            if self.tool == "create":
                self._create()
                return
            g, cage, levels, lines, res = self._compute()
        except ValueError as exc:
            self._say(str(exc))
            return
        if res.pending is not None:                    # Bridge: first opening noted
            self.pending = res.pending
            self._say(res.message)
            self._sync()
            return
        self.pending = None
        self._bridge_first = None
        self._auto_ghost = None
        self._commit(g, cage, levels, lines)
        self.sel = res.selection
        self.extra = []
        self._say(res.message)
        self._sync()

    def _create(self) -> None:
        size = self._metres()
        half = size / 2                              # one bottom corner on the origin,
        cage = Cage.box((size, size, size), center=(half, half, half))   # base on the ground
        sharp = 0
        if self.sharp_create.isChecked() and self.angle.value() > 0:
            sharp = cage.crease_by_angle(float(self.angle.value()), 4.0)
        self.pending = None
        self._commit(None, cage, int(self.levels.value()), self.lines.currentData())
        self._clear_sel()
        self._say(T("Sharp-edged SubD box created — click a point, edge or face of the cage")
                  if sharp else T("SubD box created — click a point, edge or face of the cage"))
        self._sync()

    # ---- symmetry ---------------------------------------------------------------------
    def _write_settings(self, g, cage: Cage, levels: int, lines: str, note: str) -> None:
        """Store changed cage settings without rebuilding the surface."""
        vp = self.app.viewport
        ext = subdiv_group.make_ext(cage, levels, lines, g.mesh)
        vp.history.execute(_SetExt(g, ext))
        notify = getattr(vp, "notify_scene_changed", None)
        if callable(notify):
            notify()
        self._say(note)
        vp.update()

    def _plane_centre(self, cage: Cage):
        lo, hi = cage.bounds()
        return tuple((lo[i] + hi[i]) / 2 for i in range(3)), self.sym_axis.currentData()

    def _sym_toggled(self, on: bool) -> None:
        g = self.active_group()
        if g is None:
            self.sym_box.blockSignals(True)
            self.sym_box.setChecked(False)
            self.sym_box.blockSignals(False)
            self._say(T("Create or choose a SubD group first"))
            return
        cage, levels, lines = _state(g)
        cage = cage.copy()
        if cage.sym is None:
            point, normal = self._plane_centre(cage)
            cage.sym = {"on": on, "point": point, "normal": normal}
        else:
            cage.sym["on"] = on
        self._write_settings(g, cage, levels, lines,
                             T("Symmetry on") if on else T("Symmetry off"))

    def _sym_centre(self) -> None:
        g = self.active_group()
        if g is None:
            self._say(T("Create or choose a SubD group first"))
            return
        cage, levels, lines = _state(g)
        cage = cage.copy()
        point, normal = self._plane_centre(cage)
        on = self.sym_box.isChecked() or (cage.sym is not None and cage.sym["on"])
        cage.sym = {"on": on, "point": point, "normal": normal}
        self._write_settings(g, cage, levels, lines, T("Plane set through the centre"))

    def _sym_from_face(self) -> None:
        g = self.active_group()
        if g is None or not self.sel or self.sel[0] != "f":
            self._say(T("Select a face first: its plane becomes the symmetry plane"))
            return
        cage, levels, lines = _state(g)
        cage = cage.copy()
        on = self.sym_box.isChecked() or (cage.sym is not None and cage.sym["on"])
        cage.sym = {"on": on, "point": cage.face_centroid(self.sel[1]),
                    "normal": cage.face_normal(self.sel[1])}
        self._write_settings(g, cage, levels, lines, T("Plane set from the face"))

    def _draw_plane(self, painter, cage: Cage) -> None:
        sym = cage.sym
        if not sym or not sym["on"]:
            return
        n = subdiv_ops._plane(sym)[1]
        helper = (1.0, 0.0, 0.0) if abs(n[0]) < 0.9 else (0.0, 1.0, 0.0)
        u = subdiv_ops._unit_sub(subdiv_ops._cross_(n, helper), (0.0, 0.0, 0.0))
        v = subdiv_ops._cross_(n, u)
        lo, hi = cage.bounds()
        r = 0.65 * (math.dist(lo, hi) or 1.0)
        p = sym["point"]
        corners = [tuple(p[i] + r * (su * u[i] + sv * v[i]) for i in range(3))
                   for su, sv in ((-1, -1), (1, -1), (1, 1), (-1, 1))]
        xs, ys, front = self.app.world_to_pixels(np.array(corners, dtype=float))
        if not all(front):
            return
        painter.setPen(QPen(PLANE_LINE, 1.2))
        painter.setBrush(QBrush(PLANE_FILL))
        painter.drawPolygon(QPolygonF([QPointF(float(x), float(y)) for x, y in zip(xs, ys)]))

    # ---- joining two pieces ------------------------------------------------------------
    def join(self) -> None:
        a = self.active_group()
        uid = self.join_with.currentData()
        b = next((x for x in self.app.scene.groups if x.uid == uid), None)
        if a is None or b is None or _state(b) is None:
            self._say(T("Choose a second SubD group under \"Join with\""))
            return
        ca, levels, lines = _state(a)
        cage = subdiv_group.join_cages(ca, _state(b)[0])
        if self.auto.isChecked():
            levels = subdiv_group.auto_levels(cage)
        vp = self.app.viewport
        new = subdiv_group.build_group(cage, levels, Group, Mesh, QVector3D,
                                       name=a.name, lines=lines)
        subdiv_group.carry_over(a, new)
        vp.history.execute(_Join(a, b, new))
        err = getattr(vp.history, "last_error", None)
        if err:
            self._say(T("Could not join: {err}", err=err))
            return
        self.active_uid = new.uid
        self._clear_sel()
        notify = getattr(vp, "notify_scene_changed", None)
        if callable(notify):
            notify()
        self._say(T("Joined. Choose Bridge, then click a face on each piece (Apply after each)"))
        vp.update()

    def _absorb(self, a, b):
        """Join SubD group ``b`` into ``a`` (undoable); returns ``(first point, first face)``
        of what came from ``b`` in the new cage, or None."""
        ca, levels, lines = _state(a)
        cage = ca.copy()
        v0, f0 = cage.merge(_state(b)[0])
        if self.auto.isChecked():
            levels = subdiv_group.auto_levels(cage)
        vp = self.app.viewport
        new = subdiv_group.build_group(cage, levels, Group, Mesh, QVector3D,
                                       name=a.name, lines=lines)
        subdiv_group.carry_over(a, new)
        vp.history.execute(_Join(a, b, new))
        if getattr(vp.history, "last_error", None):
            self._say(T("Could not join: {err}", err=vp.history.last_error))
            return None
        self.active_uid = new.uid
        notify = getattr(vp, "notify_scene_changed", None)
        if callable(notify):
            notify()
        return v0, f0

    def _other_hit(self, px: float, py: float):
        """``(group, item)`` for a point, edge or face of ANOTHER SubD group under the
        pointer (on its skin, or on its cage), or None."""
        for other in self._others():
            hit = None
            if self.skin_pick.isChecked():
                hit = self._pick_on_skin(other, px, py)
            if hit is None:
                cage = _state(other)[0]
                hit = self._pick_on_cage(other, px, py)
            if hit is not None:
                return other, hit
        return None

    def _join_pick(self, pos) -> bool:
        """Shift+click on a face of another SubD group while Loft or Bridge is the tool:
        that group is joined into the active one (one undo step) and the face is added to
        the selection, so you can loft or bridge between two pieces."""
        a = self.active_group()
        if a is None or self.tool not in ("loft", "bridge") or \
                self.pick_item(None, pos.x(), pos.y()) is not None:
            return False
        found = self._other_hit(pos.x(), pos.y())
        if found is None:
            return False
        other, item = found
        keep = self._sels()
        done = self._absorb(a, other)
        if done is None:
            return True
        v0, f0 = done
        if item[0] == "f":
            item = ("f", item[1] + f0)
        elif item[0] == "e":
            item = ("e", item[1] + v0, item[2] + v0)
        else:
            item = ("v", item[1] + v0)
        sels = keep + [item]
        self.sel = sels[-1]
        self.extra = sels[:-1]
        self._swallow = True
        self.pending = None
        self._say(T("Joined the other piece: now Apply to {tool} between them",
                    tool=T(subdiv_ops.SPECS[self.tool].label)))
        self.refresh()
        self._sync()
        self.app.viewport.update()
        return True

    def split(self) -> None:
        """Undo a Join: every piece of the cage that shares no point with the
        others becomes its own SubD group again."""
        g = self.active_group()
        if g is None:
            self._say(T("No SubD group to split"))
            return
        cage, levels, lines = _state(g)
        parts = cage.components()
        if len(parts) < 2:
            self._say(T("Nothing to split: this is one connected piece. After a "
                      "Bridge, delete the bridge's faces (Delete F) to separate the "
                      "pieces first"))
            return
        vp = self.app.viewport
        news = []
        for k, faces in enumerate(parts):
            sub = cage.extract(faces)
            lv = subdiv_group.auto_levels(sub) if self.auto.isChecked() else levels
            name = g.name if k == 0 else f"{g.name} {k + 1}"
            new = subdiv_group.build_group(sub, lv, Group, Mesh, QVector3D,
                                           name=name, lines=lines)
            if k == 0:
                subdiv_group.carry_over(g, new)
            else:
                new.layer, new.ifc, new.material = g.layer, g.ifc, g.material
            news.append(new)
        vp.history.execute(_Split(g, news))
        err = getattr(vp.history, "last_error", None)
        if err:
            self._say(T("Could not split: {err}", err=err))
            return
        self.active_uid = news[0].uid
        self._clear_sel()
        self.pending = None
        notify = getattr(vp, "notify_scene_changed", None)
        if callable(notify):
            notify()
        self._say(T("Split into {n} separate SubD groups (Ctrl+Z to join them back)", n=len(news)))
        vp.update()

    def convert(self) -> None:
        uid = self.convertible.currentData()
        g = next((x for x in self.app.scene.groups if x.uid == uid), None)
        if g is None:
            self._say(T("No group to convert: make or import one first"))
            return
        try:
            cage, holes = subdiv_group.cage_from_mesh(g.mesh)
            angle = float(self.angle.value())
            creased = cage.crease_by_angle(angle, 4.0) if angle > 0 else 0
        except ValueError as exc:
            self._say(str(exc))
            return
        self.pending = None
        self._commit(g, cage, int(self.levels.value()), self.lines.currentData())
        self._clear_sel()
        note = T(" ({n} faces lost their holes)", n=holes) if holes else ""
        self._say(T("Converted: {n} faces, {k} sharp edges", n=len(cage.faces), k=creased) + note)
        self._sync()

    def update_look(self) -> None:
        g = self.active_group()
        if g is None:
            self._say(T("No SubD group to update"))
            return
        cage = _state(g)[0].copy()
        self._commit(g, cage, int(self.levels.value()), self.lines.currentData(), final=True)
        self._say(T("Look updated"))

    def flip(self) -> None:
        """Turn the whole piece inside out: the faces seen from behind (the
        blue ones) become the front, and the front ones the back."""
        g = self.active_group()
        if g is None:
            self._say(T("No SubD group to flip"))
            return
        cage = _state(g)[0].copy()
        picked = {x[1] for x in self._sels() if x and x[0] == "f" and 0 <= x[1] < len(cage.faces)}
        part = subdiv_ops.connected_faces(cage, picked) if picked else None
        cage.flip(sorted(part) if part else None)
        self._commit(g, cage, int(self.levels.value()), self.lines.currentData())
        if part and len(part) < len(cage.faces):
            self._say(T("Flipped the connected part of the selected face(s): {n} faces",
                        n=len(part)))
        else:
            self._say(T("Whole piece flipped (select a face to flip only its part)"))

    def finish(self) -> None:
        """Stop treating the active group as SubD: it becomes an ordinary
        group made of the smooth surface, where every flat patch (a box face)
        is a single polygon so the other tools stay fast. A closed, sound cage
        is re-oriented outwards and the volume reported (Solid Group); an open
        one is finished as a plain surface. One undo step brings the cage back."""
        g = self.active_group()
        if g is None:
            self._say(T("No SubD group to finish"))
            return
        cage, levels, lines = _state(g)
        ok, problems, vol = cage.solid_report()
        cage = cage.copy()
        if ok:
            cage.orient()
        levels = self._finish_levels(cage, levels)
        vp = self.app.viewport
        new = subdiv_group.build_group(cage, levels, Group, Mesh, QVector3D,
                                       name=g.name, lines=lines, merge_flat=True)
        subdiv_group.carry_over(g, new)
        new.ext = {k: v for k, v in (g.ext or {}).items() if k != subdiv_group.KEY}
        vp.history.execute(_Swap(g, new))
        err = getattr(vp.history, "last_error", None)
        if err:
            self._say(T("Could not finish: {err}", err=err))
            return
        self._clear_sel()
        self.pending = None
        notify = getattr(vp, "notify_scene_changed", None)
        if callable(notify):
            notify()
        if ok:
            shown = vol / (self._scale ** 3) if self._scale else vol
            u = _SUFFIX.get(self._unit, " m").strip()
            text = T("Finished, solid group ({n} faces): volume {v} {u}³",
                     n=_face_count(new), v=f"{shown:.6g}", u=u)
            if u != "m":
                text += f" ({vol:.4g} m³)"
            try:
                from core import solids
                if solids.solid_volume(new) is None:
                    text += T(" — not counted as a solid by Solid Tools; check for coincident points")
            except Exception:                                    # noqa: BLE001
                pass
        else:
            why = "; ".join(p for p in problems if "re-oriented" not in p)
            text = T("Finished, surface only ({n} faces), not a solid: {why}",
                     n=_face_count(new), why=why)
        self._say(text + T(" (Ctrl+Z to edit the cage again)"))
        vp.update()

    # ---- drawing over the view -------------------------------------------------------
    def _others(self):
        """The SubD groups that are not the active one."""
        return [g for g in self.app.scene.groups
                if g.uid != self.active_uid and _state(g) is not None]

    def _draw_inactive(self, painter, cage) -> None:
        """A dim cage for a SubD group that is not being edited: it shows the
        group is still SubD; click one of its points to edit it."""
        if not cage.verts:
            return
        xs, ys, front = self.app.world_to_pixels(np.array(cage.verts, dtype=float))
        pt = [QPointF(float(x), float(y)) for x, y in zip(xs, ys)]
        painter.setPen(QPen(QColor(243, 115, 41, 90), 1.0))
        for (a, b) in cage.edge_faces():
            if front[a] and front[b]:
                painter.drawLine(pt[a], pt[b])
        painter.setPen(Qt.NoPen)
        painter.setBrush(QBrush(QColor(243, 115, 41, 130)))
        for i, p in enumerate(pt):
            if front[i]:
                painter.drawEllipse(p, 2.4, 2.4)

    def _draw_skin_selection(self, painter, g) -> None:
        """With the cage hidden: the picked items drawn on the skin itself (a
        point where the cage point sits on the surface, an edge as its curve,
        a face as its patch)."""
        cage = _state(g)[0]
        sels = [x for x in self._sels() if subdiv_ops.valid(cage, x)]
        self._draw_skin_items(painter, g, sels, QColor(243, 115, 41, 70),
                              QColor(255, 255, 255), QColor(255, 255, 255))

    def _draw_skin_items(self, painter, g, items, fill, line, dot, width=3.4, radius=5.5) -> None:
        cage = _state(g)[0]
        if not items:
            return
        skin = self._skin_of(g)
        xs, ys, front = self.app.world_to_pixels(skin.verts)
        pt = _LazyPoints(xs, ys)                      # only the points drawn are made
        for sel in items:
            if not subdiv_ops.valid(cage, sel):
                continue
            if sel[0] == "f":
                painter.setPen(Qt.NoPen)
                painter.setBrush(QBrush(fill))
                for t in np.nonzero(skin.tri_face == sel[1])[0]:
                    tri = skin.tris[t]
                    if all(front[int(k)] for k in tri):
                        painter.drawPolygon(QPolygonF([pt[int(k)] for k in tri]))
            elif sel[0] == "e":
                chain = skin.curves.get(ekey(sel[1], sel[2]), [])
                painter.setPen(QPen(line, width))
                painter.setBrush(Qt.NoBrush)
                painter.drawPolyline(QPolygonF([pt[k] for k in chain if front[k]]))
            else:
                if front[sel[1]]:
                    painter.setPen(Qt.NoPen)
                    painter.setBrush(QBrush(dot))
                    painter.drawEllipse(pt[sel[1]], radius, radius)

    # ---- what a click would select: the item under the cursor lights up ---------------------
    _hover = None
    _hover_t = 0.0

    def hover_move(self, ev) -> bool:
        """A mouse move with no button down: find what a click here would select.
        Moves come faster than we need: one is handled at once, and the last one is
        always handled a moment later, so the highlight never stays where the mouse was."""
        import time
        now = time.monotonic()
        self._hover_last = (ev.position().x(), ev.position().y(), bool(
            ev.buttons() or ev.modifiers() & (Qt.ControlModifier | Qt.AltModifier)))
        if now - self._hover_t < 0.03:
            if not self._hover_timer_on:
                self._hover_timer_on = True
                QTimer.singleShot(40, self._hover_trailing)
            return False
        self._hover_t = now
        self._hover_apply()
        return False

    _hover_last = None
    _hover_timer_on = False

    def _hover_trailing(self) -> None:
        self._hover_timer_on = False
        self._hover_t = __import__("time").monotonic()
        self._hover_apply()

    def _hover_apply(self) -> None:
        vp = self.app.viewport
        last = self._hover_last
        item = None
        if (last is not None and not last[2] and self._drag is None and self._live is None
                and getattr(getattr(vp, "active_tool", None), "name", "") == "Select"
                and self.active_group() is not None
                and (self.skin_pick.isChecked() or self.show_cage.isChecked())):
            try:
                item = self.pick_item(None, last[0], last[1])
            except Exception:                                    # noqa: BLE001
                item = None
        if item != self._hover:
            self._hover = item
            vp.update()

    def clear_hover(self) -> None:
        if self._hover is not None:
            self._hover = None
            self.app.viewport.update()

    def _draw_hover(self, painter) -> None:
        g = self.active_group()
        if self._hover is None or g is None or self._drag is not None or self._live is not None:
            return
        self._draw_skin_items(painter, g, [self._hover], QColor(40, 130, 255, 100),
                              QColor(40, 130, 255), QColor(40, 130, 255), 4.5, 8.0)
        h = self._hover
        if h[0] in "fe" and not self.show_cage.isChecked():   # show the points you can grab
            cage = _state(g)[0]
            if subdiv_ops.valid(cage, h):
                ids = list(cage.faces[h[1]]) if h[0] == "f" else [h[1], h[2]]
                skin = self._skin_of(g)
                xs, ys, front = self.app.world_to_pixels(skin.verts[ids])
                painter.setPen(QPen(QColor(30, 30, 30), 1.2))
                painter.setBrush(QBrush(QColor(255, 255, 255)))
                for x, y, fr in zip(xs, ys, front):
                    if fr:
                        painter.drawEllipse(QPointF(float(x), float(y)), 3.6, 3.6)

    def _draw_slice_plane(self, painter) -> None:
        """Slice: the cutting plane, drawn as a see-through sheet so you see where it cuts."""
        if self.tool != "slice":
            return
        g = self.active_group()
        axis = self.axis.currentData()
        if g is None or axis not in AXIS_VEC:
            return
        cage = _state(g)[0]
        if not cage.verts:
            return
        sels = [x for x in self._sels() if subdiv_ops.valid(cage, x)]
        lo, hi = cage.bounds()
        if sels:
            pts = [cage.verts[i] for i in subdiv_ops.vertex_set(cage, sels[0])]
        else:
            pts = [lo, hi]
        c = [sum(p[k] for p in pts) / len(pts) for k in range(3)]
        live = self._live
        v = live["v"] if live is not None and live.get("key") == "slice" else self._metres()
        n = AXIS_VEC[axis]
        point = [c[k] + n[k] * v for k in range(3)]
        u, w = subdiv_ops.plane_basis(n)
        half = 0.62 * max(hi[k] - lo[k] for k in range(3)) or 1.0
        mid = [(lo[k] + hi[k]) / 2 for k in range(3)]
        for k in range(3):                       # keep the sheet centred on the piece
            d = (mid[k] - point[k]) * (1 - abs(n[k]))
            point[k] += d
        corners = [[point[k] + u[k] * a * half + w[k] * b * half for k in range(3)]
                   for a, b in ((-1, -1), (1, -1), (1, 1), (-1, 1))]
        xs, ys, front = self.app.world_to_pixels(np.array(corners, dtype=float))
        col = AXIS_COLOR[axis]
        poly = QPolygonF([QPointF(float(x), float(y)) for x, y in zip(xs, ys)])
        painter.setPen(QPen(QColor(col.red(), col.green(), col.blue(), 220), 1.6, Qt.DashLine))
        painter.setBrush(QBrush(QColor(col.red(), col.green(), col.blue(), 45)))
        painter.drawPolygon(poly)

    def draw(self, viewport, painter) -> None:
        self._draw_live(painter)
        self._draw_hover(painter)
        self._draw_slice_plane(painter)
        if not self.show_cage.isChecked():
            g0 = self.active_group()
            if g0 is not None and self.skin_pick.isChecked():
                self._draw_skin_selection(painter, g0)
            if g0 is not None:                  # the move / rotate handles stay usable
                drag = self._drag
                live = drag is not None and drag.get("preview") is not None
                cage = drag["preview"] if live else _state(g0)[0]
                if cage.verts:
                    self._draw_plane(painter, cage)       # the symmetry plane too
                    if live:
                        self._draw_ghost(painter, drag["ghost"])
                    self._draw_handles(painter, cage)
            return
        for other in self._others():
            self._draw_inactive(painter, _state(other)[0])
        g = self.active_group()
        if g is None:
            return
        drag = self._drag
        live = drag is not None and drag.get("preview") is not None
        cage = drag["preview"] if live else _state(g)[0]
        if not cage.verts:
            return
        self._draw_plane(painter, cage)
        if live:
            self._draw_ghost(painter, drag["ghost"])
        xs, ys, front = self.app.world_to_pixels(np.array(cage.verts, dtype=float))
        pt = [QPointF(float(x), float(y)) for x, y in zip(xs, ys)]

        sels = [x for x in self._sels() if subdiv_ops.valid(cage, x)]
        for sel in sels:
            if sel[0] == "f":
                face = cage.faces[sel[1]]
                if all(front[v] for v in face):
                    painter.setPen(Qt.NoPen)
                    painter.setBrush(QBrush(QColor(243, 115, 41, 70)))
                    painter.drawPolygon(QPolygonF([pt[v] for v in face]))
        hot_edges = {frozenset((x[1], x[2])) for x in sels if x[0] == "e"}
        hot_points = {x[1] for x in sels if x[0] == "v"}

        for (a, b) in cage.edge_faces():
            if not (front[a] and front[b]):
                continue
            creased = cage.creases.get((a, b), 0) > 0
            hot = frozenset((a, b)) in hot_edges
            painter.setPen(QPen(CREASE_LINE if creased else CAGE_LINE,
                                3.2 if hot else (2.2 if creased else 1.3)))
            painter.drawLine(pt[a], pt[b])

        painter.setPen(Qt.NoPen)
        for i, p in enumerate(pt):
            if not front[i]:
                continue
            hot = i in hot_points
            painter.setBrush(QBrush(QColor(255, 255, 255) if hot else ACCENT))
            r = 5.5 if hot else 3.2
            painter.drawEllipse(p, r, r)
        self._draw_handles(painter, cage)

    def _draw_handles(self, painter, cage) -> None:
        mode = self.handles.currentData()
        if mode in ("both", "rotate"):
            self._draw_rings(painter, cage)
        if mode in ("both", "move") and not (self._drag and self._drag.get("rot")):
            self._draw_gizmo(painter, cage)

    RING_STEPS = 72
    RING_PX = 56.0                   # handles keep the same size on screen,
    REACH_PX = 84.0                  # whatever the piece or the zoom

    def _world_len(self, c, pixels: float) -> float:
        """The world length that spans ``pixels`` on screen around point ``c``."""
        pts = np.array([c, [c[0] + 1, c[1], c[2]], [c[0], c[1] + 1, c[2]],
                        [c[0], c[1], c[2] + 1]], dtype=float)
        xs, ys, _f = self.app.world_to_pixels(pts)
        d2 = sum((float(xs[i]) - float(xs[0])) ** 2 + (float(ys[i]) - float(ys[0])) ** 2
                 for i in (1, 2, 3))
        per_unit = math.sqrt(d2 / 2.0)               # three axes project to 2 s^2 in all
        return pixels / per_unit if per_unit > 1e-9 else 1.0

    def _rings(self, cage):
        """The protractor: ``(pivot, radius, {axis: [pixel points]})`` or None.
        One ring per axis (only the chosen one when X, Y or Z is picked in the
        direction list), centred on the selection, in the plane at right
        angles to that axis."""
        sels = [x for x in self._sels() if subdiv_ops.valid(cage, x)]
        if not sels:
            return None
        chosen = self.axis.currentData()
        keys = list(AXIS_VEC)                  # always the three: the direction list is for Apply
        idx = subdiv_ops.vertex_union(cage, sels)
        pts = [cage.verts[i] for i in idx]
        c = tuple(sum(p[k] for p in pts) / len(pts) for k in range(3))
        radius = self._world_len(c, self.RING_PX)
        rings = {}
        for a in keys:
            u, v = subdiv_ops.plane_basis(AXIS_VEC[a])
            world = []
            for i in range(self.RING_STEPS + 1):
                t = 2.0 * math.pi * i / self.RING_STEPS
                co, si = math.cos(t) * radius, math.sin(t) * radius
                world.append([c[k] + u[k] * co + v[k] * si for k in range(3)])
            xs, ys, _f = self.app.world_to_pixels(np.array(world, dtype=float))
            rings[a] = [QPointF(float(x), float(y)) for x, y in zip(xs, ys)]
        return c, radius, rings

    def _draw_rings(self, painter, cage) -> None:
        """Rotation handles: a coloured ring per axis (X red, Y green, Z blue).
        While turning, the ring in use gets a tick every 15 degrees (a
        protractor) and the angle swept is written next to the pointer."""
        r = self._rings(cage)
        if r is None:
            return
        pivot, radius, rings = r
        d = self._drag
        turning = d is not None and d.get("rot") and d.get("started")
        for axis, poly in rings.items():
            if turning and d["rot"] != axis:
                continue
            col = AXIS_COLOR[axis]
            painter.setPen(QPen(col, 3.4 if turning else 2.4))
            painter.setBrush(Qt.NoBrush)
            painter.drawPolyline(QPolygonF(poly))
        if turning:
            axis = d["rot"]
            u, v = subdiv_ops.plane_basis(AXIS_VEC[axis])
            ticks = []
            for k in range(24):                                  # every 15 degrees
                t = 2.0 * math.pi * k / 24
                for rr in (radius, radius * (0.86 if k % 6 else 0.78)):
                    ticks.append([pivot[j] + (u[j] * math.cos(t) + v[j] * math.sin(t)) * rr
                                  for j in range(3)])
            xs, ys, _f = self.app.world_to_pixels(np.array(ticks, dtype=float))
            painter.setPen(QPen(AXIS_COLOR[axis], 1.4))
            for k in range(24):
                painter.drawLine(QPointF(float(xs[2 * k]), float(ys[2 * k])),
                                 QPointF(float(xs[2 * k + 1]), float(ys[2 * k + 1])))
            deg = math.degrees(d.get("angle", 0.0))
            cx, cy = self.app.world_to_pixels(np.array([pivot], dtype=float))[:2]
            painter.setPen(QPen(QColor(30, 30, 30), 1.0))
            painter.setBrush(QBrush(QColor(255, 255, 255, 230)))
            painter.drawRoundedRect(float(cx[0]) - 34, float(cy[0]) - 12, 68, 24, 5, 5)
            painter.drawText(float(cx[0]) - 34, float(cy[0]) - 12, 68, 24,
                             int(Qt.AlignCenter), f"{deg:+.1f}\u00b0")
        else:
            painter.setPen(QPen(QColor(40, 40, 40), 1.2))
            painter.setBrush(QBrush(QColor(255, 255, 255)))
            cx, cy = self.app.world_to_pixels(np.array([pivot], dtype=float))[:2]
            painter.drawEllipse(QPointF(float(cx[0]), float(cy[0])), 4.0, 4.0)

    def _grab_ring(self, g, pos) -> bool:
        """Press on a protractor ring: start a rotation about that axis."""
        cage = _state(g)[0]
        r = self._rings(cage)
        if r is None:
            return False
        pivot, _radius, rings = r
        best, best_d = None, 9.0
        for axis, poly in rings.items():
            for a, b in zip(poly, poly[1:]):
                dx, dy = b.x() - a.x(), b.y() - a.y()
                L2 = dx * dx + dy * dy
                t = 0.0 if L2 < 1e-9 else max(0.0, min(1.0, (
                    (pos.x() - a.x()) * dx + (pos.y() - a.y()) * dy) / L2))
                dist = math.hypot(pos.x() - (a.x() + t * dx), pos.y() - (a.y() + t * dy))
                if dist < best_d:
                    best, best_d = axis, dist
        if best is None:
            return False
        self._drag = {
            "press": (pos.x(), pos.y()), "hit": None, "group": g,
            "vset": subdiv_ops.vertex_union(cage, self._sels()), "base": cage.copy(),
            "levels": _state(g)[1], "lines": _state(g)[2], "sym": cage.sym,
            "started": False, "delta": (0.0, 0.0, 0.0), "preview": None,
            "rot": best, "angle": 0.0, "total": 0.0,
        }
        return True

    def _gizmo(self, cage):
        """Pixel positions of the move handles: ``(centre, {axis: tip})`` or
        None. One handle per axis (only the chosen one when X, Y or Z is
        picked in the direction list); each tip drags along its axis."""
        sels = [x for x in self._sels() if subdiv_ops.valid(cage, x)]
        if not sels:
            return None
        chosen = self.axis.currentData()
        keys = list(AXIS_VEC)                  # always the three: the direction list is for Apply
        idx = subdiv_ops.vertex_union(cage, sels)
        pts = [cage.verts[i] for i in idx]
        c = [sum(p[k] for p in pts) / len(pts) for k in range(3)]
        reach = self._world_len(c, self.REACH_PX)
        world = [c] + [[c[k] + AXIS_VEC[a][k] * reach for k in range(3)] for a in keys]
        xs, ys, _front = self.app.world_to_pixels(np.array(world, dtype=float))
        centre = QPointF(float(xs[0]), float(ys[0]))
        tips = {a: QPointF(float(xs[i + 1]), float(ys[i + 1])) for i, a in enumerate(keys)}
        return centre, tips

    def _draw_gizmo(self, painter, cage) -> None:
        """Move handles on the selection: a line and a round tip per axis, in
        the axis colour (X red, Y green, Z blue). Drag a tip to move the
        selection along that axis only."""
        g = self._gizmo(cage)
        if g is None:
            return
        centre, tips = g
        for axis, tip in tips.items():
            col = AXIS_COLOR[axis]
            painter.setPen(QPen(col, 2.2))
            painter.drawLine(centre, tip)
            painter.setPen(QPen(QColor(255, 255, 255), 1.5))
            painter.setBrush(QBrush(col))
            painter.drawEllipse(tip, 6.5, 6.5)
        painter.setPen(QPen(QColor(40, 40, 40), 1.2))
        painter.setBrush(QBrush(QColor(255, 255, 255)))
        painter.drawEllipse(centre, 4.0, 4.0)

    def _grab_handle(self, g, pos) -> bool:
        """Press on a move handle: start a drag locked to that axis."""
        cage = _state(g)[0]
        gz = self._gizmo(cage)
        if gz is None:
            return False
        _centre, tips = gz
        for axis, tip in tips.items():
            if math.hypot(pos.x() - tip.x(), pos.y() - tip.y()) <= 10.0:
                self._drag = {
                    "press": (pos.x(), pos.y()), "hit": None, "group": g,
                    "vset": subdiv_ops.vertex_union(cage, self._sels()), "base": cage.copy(),
                    "levels": _state(g)[1], "lines": _state(g)[2], "sym": cage.sym,
                    "started": False, "delta": (0.0, 0.0, 0.0), "preview": None,
                    "forced": axis,
                }
                return True
        return False

    def _draw_ghost(self, painter, ghost) -> None:
        """A light wireframe of the smoothed surface while a point is dragged
        (the real surface is rebuilt when the mouse is released)."""
        verts, edges = ghost
        if not verts:
            return
        xs, ys, front = self.app.world_to_pixels(np.array(verts, dtype=float))
        painter.setPen(QPen(GHOST_LINE, 1.0))
        for a, b in edges:
            if front[a] and front[b]:
                painter.drawLine(QPointF(float(xs[a]), float(ys[a])),
                                 QPointF(float(xs[b]), float(ys[b])))

    # ---- freestyle dragging ------------------------------------------------------
    _cc = None                         # (time, (x, y), count) of the last quick left clicks

    def click_count(self, ev, kind):
        """Counts quick clicks on the same spot. On a SubD piece: the second click of
        a double-click is kept from the model (it would enter group editing, which hides
        the SubD handles) and the third selects the whole piece, to move, copy or delete.
        Returns True when the event is used up, None to go on as usual."""
        import time
        now = time.monotonic()
        pos = ev.position()
        last = self._cc
        n = 1
        if last and now - last[0] < 0.55 and math.hypot(pos.x() - last[1][0], pos.y() - last[1][1]) < 6.0:
            n = last[2] + 1
        self._cc = (now, (pos.x(), pos.y()), n)
        vp = self.app.viewport
        if n < 2 or ev.modifiers() or \
                getattr(getattr(vp, "active_tool", None), "name", "") != "Select":
            return None
        if self._activate_under(pos.x(), pos.y()):
            self.refresh()
        g = self.active_group()
        if g is None or self.pick_item(None, pos.x(), pos.y()) is None:
            return None
        if n == 2:
            return True if kind == QEvent.MouseButtonDblClick else None
        self._cc = None
        self._drag = None
        self._click = None
        self.clear_hover()
        vp.clear_extension_pick()
        self._clear_sel()
        vp.scene.select([g])
        self._swallow = True                       # the release that follows
        self._say(T("Whole piece selected: move it, copy it, or press Delete to remove it"))
        vp.update()
        return True

    def _press_copy(self, ev) -> bool:
        """Ctrl held on a move handle with faces selected: the drag carries a copy of
        the faces (or of the whole piece when every face is selected)."""
        vp = self.app.viewport
        if getattr(getattr(vp, "active_tool", None), "name", "") != "Select":
            return False
        if ev.modifiers() & Qt.ShiftModifier or not self._has_face_sel():
            return False
        if self.handles.currentData() not in ("both", "move"):
            return False
        g = self.active_group()
        if g is None or not self._grab_handle(g, ev.position()):
            return False
        d = self._drag
        cage = _state(g)[0]
        faces = sorted({x[1] for x in self._sels() if x and x[0] == "f" and x[1] < len(cage.faces)})
        d["sym"] = None
        if len(faces) == len(cage.faces):                       # the whole piece: a new group
            d["newgroup"] = True
            d["base"] = cage.copy()
            d["vset"] = list(range(len(cage.verts)))
            d["copy_faces"] = list(range(len(cage.faces)))
        else:                                                   # some faces: copied in place
            base = cage.copy()
            newv, newf = modeling.duplicate_faces(base, faces)
            d["copy"] = True
            d["base"] = base
            d["vset"] = newv
            d["copy_faces"] = newf
        self._say(T("Ctrl: dragging a copy"))
        return True

    def mouse_press(self, ev) -> bool:
        """Press on a cage handle with the Select tool: select it and get
        ready to drag. Anything else is left to the viewport (returns False)."""
        vp = self.app.viewport
        mods = ev.modifiers()
        if mods & Qt.AltModifier:
            return False
        if mods & Qt.ControlModifier:                  # Ctrl + a move handle: drag a copy
            return self._press_copy(ev)
        shift = bool(mods & Qt.ShiftModifier)
        if getattr(getattr(vp, "active_tool", None), "name", "") != "Select":
            return False
        if not (self.show_cage.isChecked() or self.skin_pick.isChecked()):
            return False
        pos = ev.position()
        if shift and self._join_pick(pos):
            return True
        if self._activate_under(pos.x(), pos.y()):
            self.refresh()
            vp.update()
        g = self.active_group()
        if g is None:
            return False
        if shift:
            return self._toggle_pick(g, pos)
        mode = self.handles.currentData()
        if mode in ("both", "move") and self._grab_handle(g, pos):     # tips first
            return True
        if mode in ("both", "rotate") and self._grab_ring(g, pos):
            return True
        hit = vp.pick_extension_item(pos.x(), pos.y())
        if hit is None or hit[0].get("key") != self.app.key:
            return False
        cage = _state(g)[0]
        group_drag = len(self._sels()) > 1 and hit[1] in self._sels()
        lc = self._click
        again = (lc is not None and not group_drag and self.sel == lc["expect"]
                 and math.hypot(pos.x() - lc["pos"][0], pos.y() - lc["pos"][1]) <= 4.0)
        if not again:
            self._click = {"pos": (pos.x(), pos.y()), "seen": [hit[1]], "stage": 0,
                           "expect": hit[1]}
        if not group_drag:
            clear = getattr(vp.scene, "clear_selection", None)
            if callable(clear):
                clear()
            vp.set_extension_pick(hit)                # -> self.on_select(item)
        if self._auto_bridged:                        # the click already made the bridge:
            self._auto_bridged = False                # nothing to drag
            self._swallow = True
            return True
        self._drag = {
            "press": (pos.x(), pos.y()), "hit": None if group_drag else hit, "group": g,
            "vset": (subdiv_ops.vertex_union(cage, self._sels()) if group_drag
                     else subdiv_ops.vertex_set(cage, hit[1])), "base": cage.copy(),
            "levels": _state(g)[1], "lines": _state(g)[2], "sym": cage.sym,
            "started": False, "delta": (0.0, 0.0, 0.0), "preview": None,
            "cycle": again,
        }
        return True

    def _cycle_click(self) -> None:
        """A click repeated on the same spot goes on to the next thing there:
        for a face, the face behind it (round again at the last one); for an
        edge, the whole contour it belongs to, then back to the edge alone."""
        lc = self._click
        g = self.active_group()
        if lc is None or g is None:
            return
        cage = _state(g)[0]
        x, y = lc["pos"]
        first = lc["seen"][0]
        if first[0] == "f":
            nxt = self.pick_item(None, x, y, skip=lc["seen"])
            if nxt is None or nxt[0] != "f":
                lc["seen"] = []                                 # the last one: start over
                nxt = self.pick_item(None, x, y)
            if nxt is None:
                return
            lc["seen"].append(nxt)
            items = [nxt]
        elif first[0] == "e":
            stages = subdiv_ops.edge_contours(cage, first[1], first[2])
            lc["stage"] = (lc["stage"] + 1) % len(stages)
            label, edges = stages[lc["stage"]]
            items = [("e", x, y) for x, y in edges]
            note = label if lc["stage"] else "Edge"
        else:
            return
        self.sel = items[-1]
        self.extra = items[:-1]
        lc["expect"] = self.sel
        self._sync()
        if first[0] == "e":
            self._say((T("{note} ({n} edges) - click again for the next contour", note=T(note), n=len(items))
                       if len(items) > 1 else
                       T("{note} ({n} edge) - click again for the next contour", note=T(note), n=len(items))))
        self.app.viewport.update()

    def _toggle_pick(self, g, pos) -> bool:
        """Shift+click: add the item under the pointer to the selection, or
        take it out if it is already there. A click on nothing is ignored."""
        item = self.pick_item(None, pos.x(), pos.y())
        if item is None:
            return False                           # Shift+click elsewhere: the viewport's
        self._swallow = True                       # the viewport never sees this click
        sels = self._sels()
        if item in sels and item[0] == "f":        # a selected face hides the one behind it:
            behind = self.pick_item(None, pos.x(), pos.y(), skip=sels)   # reach through it
            if behind is not None and behind[0] == "f":
                item = behind
        if item in sels:
            sels.remove(item)
        else:
            sels.append(item)
        self.sel = sels[-1] if sels else None
        self.extra = sels[:-1]
        self._sync()
        self.app.viewport.update()
        return True

    @staticmethod
    def _xyz(v):
        return (float(v.x()), float(v.y()), float(v.z()))

    def _begin_drag(self, d) -> bool:
        vp = self.app.viewport
        pts = [d["base"].verts[v] for v in d["vset"]]
        pivot = tuple(sum(p[i] for p in pts) / len(pts) for i in range(3))
        o, ray = vp._pixel_to_ray(*d["press"])
        _o2, view = vp._pixel_to_ray(vp.width() / 2, vp.height() / 2)
        if o is None or view is None:
            return False
        d["pivot"] = QVector3D(*pivot)
        d["view"] = view
        if d.get("rot"):
            d["pivot_t"] = pivot
            a0 = subdiv_ops.angle_in_plane(self._xyz(o), self._xyz(ray), pivot,
                                           AXIS_VEC[d["rot"]])
            if a0 is None:
                return False
            d["last"] = a0
            d["started"] = True
            return True
        axis = d.get("forced") or self.axis.currentData()
        d["axis"] = {"x": (1.0, 0.0, 0.0), "y": (0.0, 1.0, 0.0),
                     "z": (0.0, 0.0, 1.0)}.get(axis)
        if d["axis"] is not None:
            s0 = subdiv_ops.closest_on_axis(self._xyz(o), self._xyz(ray), pivot, d["axis"])
            d["s0"] = 0.0 if s0 is None else s0
        else:
            p0 = vp._ray_plane(o, ray, d["pivot"], view)
            d["p0"] = p0 if p0 is not None else d["pivot"]
        d["started"] = True
        return True

    def mouse_move(self, ev) -> bool:
        d = self._drag
        if d is None:
            return False
        if not (ev.buttons() & Qt.LeftButton):
            self._drag = None
            return False
        vp = self.app.viewport
        pos = ev.position()
        if not d["started"]:
            if math.hypot(pos.x() - d["press"][0], pos.y() - d["press"][1]) < 4.0:
                return True
            if not self._begin_drag(d):
                self._drag = None
                return False
        o, ray = vp._pixel_to_ray(pos.x(), pos.y())
        if o is None:
            return True
        if d.get("rot"):
            a = subdiv_ops.angle_in_plane(self._xyz(o), self._xyz(ray), d["pivot_t"],
                                          AXIS_VEC[d["rot"]])
            if a is None:
                return True
            d["total"] += (a - d["last"] + math.pi) % (2.0 * math.pi) - math.pi
            d["last"] = a
            ang = d["total"]
            if ev.modifiers() & Qt.ControlModifier:
                ang = math.radians(round(math.degrees(ang) / 15.0) * 15.0)
            d["angle"] = ang
            prev = d["base"].copy()
            subdiv_ops.symmetric_rotate(prev, d["vset"], d["pivot_t"], AXIS_VEC[d["rot"]],
                                        ang, d["sym"])
            d["preview"] = prev
            verts, faces = prev.smooth(1 if len(prev.faces) > 150 else 2)
            d["ghost"] = (verts, {(min(f[i], f[(i + 1) % len(f)]), max(f[i], f[(i + 1) % len(f)]))
                                  for f in faces for i in range(len(f))})
            vp.update()
            return True
        if d["axis"] is not None:
            s = subdiv_ops.closest_on_axis(self._xyz(o), self._xyz(ray),
                                           self._xyz(d["pivot"]), d["axis"])
            if s is None:
                return True
            k = s - d["s0"]
            delta = tuple(c * k for c in d["axis"])
        else:
            p = vp._ray_plane(o, ray, d["pivot"], d["view"])
            if p is None:
                return True
            delta = self._xyz(p - d["p0"])
        d["delta"] = delta
        prev = d["base"].copy()
        subdiv_ops.symmetric_move(prev, d["vset"], delta, d["sym"], self._soft())
        d["preview"] = prev
        verts, faces = prev.smooth(1 if len(prev.faces) > 150 else 2)
        edges = {(min(f[i], f[(i + 1) % len(f)]), max(f[i], f[(i + 1) % len(f)]))
                 for f in faces for i in range(len(f))}
        d["ghost"] = (verts, edges)
        vp.update()
        return True

    def mouse_release(self, ev) -> bool:
        d = self._drag
        if d is None:
            swallowed, self._swallow = self._swallow, False
            return swallowed
        self._drag = None
        vp = self.app.viewport
        if not d["started"] and d.get("cycle"):
            self._cycle_click()                      # same spot again: the next item
            return True
        if d["started"] and d.get("rot") and abs(d["angle"]) > 1e-9:
            cage = d["base"].copy()
            subdiv_ops.symmetric_rotate(cage, d["vset"], d["pivot_t"], AXIS_VEC[d["rot"]],
                                        d["angle"], d["sym"])
            self._commit(d["group"], cage, d["levels"], d["lines"])
            self._say(T("Rotated {a}° around {axis}", a=f"{math.degrees(d['angle']):+.1f}",
                        axis=d['rot'].upper()))
        elif d["started"] and any(abs(c) > 1e-9 for c in d["delta"]):
            cage = d["base"].copy()
            subdiv_ops.symmetric_move(cage, d["vset"], d["delta"], d["sym"], self._soft())
            if d.get("newgroup") or d.get("copy"):
                self._commit(None if d.get("newgroup") else d["group"], cage,
                             d["levels"], d["lines"])
                faces = d["copy_faces"]
                self.sel = ("f", faces[0])
                self.extra = [("f", i) for i in faces[1:]]
                self._say(T("Copy made: {n} faces", n=len(faces)))
                vp.update()
                return True
            self._commit(d["group"], cage, d["levels"], d["lines"])
            if d["hit"] is not None:
                vp.set_extension_pick(d["hit"])       # keep it selected
            self._say("Moved")
        vp.update()
        return True

    def cancel_drag(self) -> bool:
        if self._drag is None or not self._drag["started"]:
            return False
        self._drag = None
        self.app.viewport.update()
        return True


class _DragFilter(QObject):
    """Lets the panel see the viewport's mouse events before the viewport does.
    It only ever claims a press that lands on a cage handle (Select tool)."""

    def __init__(self, panel) -> None:
        super().__init__(panel)
        self.panel = panel

    def eventFilter(self, obj, ev) -> bool:                      # noqa: N802
        try:
            t = ev.type()
            if (t in (QEvent.MouseButtonPress, QEvent.MouseButtonDblClick)
                    and ev.button() == Qt.LeftButton and self.panel._live is None):
                used = self.panel.click_count(ev, t)
                if used:
                    return True
            if self.panel._live is not None:
                pn = self.panel
                if t == QEvent.MouseMove:
                    return pn.live_move(ev)
                if t == QEvent.MouseButtonPress:
                    return pn.live_confirm(right=ev.button() == Qt.RightButton)
                if t == QEvent.MouseButtonRelease:
                    return True
                if t == QEvent.ContextMenu:
                    return True
                if t in (QEvent.ShortcutOverride, QEvent.KeyPress):
                    if ev.key() == Qt.Key_Escape:
                        if t == QEvent.KeyPress:
                            pn.live_cancel()
                        ev.accept()
                        return True
                    if ev.key() in (Qt.Key_Return, Qt.Key_Enter):
                        if t == QEvent.KeyPress:
                            pn.live_exact()
                        ev.accept()
                        return True
                    if ev.key() in (Qt.Key_X, Qt.Key_Y, Qt.Key_Z, Qt.Key_A) and \
                            pn._live["spec"].axis:
                        if t == QEvent.KeyPress:
                            pn.live_key(ev.key())
                        ev.accept()
                        return True
            if t == QEvent.MouseButtonPress and ev.button() == Qt.LeftButton:
                return bool(self.panel.mouse_press(ev))
            if t == QEvent.Leave:
                self.panel.clear_hover()
            if t == QEvent.ContextMenu:
                self.panel.clear_hover()
                return bool(self.panel.context_event(ev))
            if t == QEvent.MouseMove:
                if not ev.buttons():
                    self.panel.hover_move(ev)
                return bool(self.panel.mouse_move(ev))
            if t == QEvent.MouseButtonRelease and ev.button() == Qt.LeftButton:
                QTimer.singleShot(60, self.panel._sync)       # the drawing selection may have changed
                return bool(self.panel.mouse_release(ev))
            if t == QEvent.KeyPress and ev.key() == Qt.Key_Escape:
                if self.panel.cancel_drag():
                    return True
                if self.panel._live is None and self.panel._box_dlg is None:
                    return bool(self.panel.cancel_tool())
                return False
            if (t == QEvent.ShortcutOverride and ev.key() == Qt.Key_Escape
                    and self.panel._live is None and self.panel._box_dlg is None
                    and (self.panel.tool != "edit" or self.panel.pending is not None
                         or self.panel._auto_ghost is not None)):
                ev.accept()                          # the model's Esc must not take it first
                return True
            if t in (QEvent.ShortcutOverride, QEvent.KeyPress) and \
                    ev.key() in (Qt.Key_Delete, Qt.Key_Backspace) and not ev.modifiers():
                vp = self.panel.app.viewport                # Supr: the SubD item picked
                if (self.panel.sel is not None and self.panel.active_group() is not None
                        and not vp.scene.selection):         # (a whole piece selected: host erases it)
                    if t == QEvent.KeyPress:
                        self.panel.delete_item(self.panel.sel)
                    ev.accept()
                    return True
            if t in (QEvent.ShortcutOverride, QEvent.KeyPress) and \
                    ev.modifiers() & Qt.ControlModifier and not ev.modifiers() & Qt.ShiftModifier:
                if ev.key() == Qt.Key_C:
                    if self.panel._has_face_sel():
                        if t == QEvent.KeyPress:
                            self.panel.copy_faces()
                        ev.accept()
                        return True
                    self.panel._clip_owner = False
                elif ev.key() == Qt.Key_V and self.panel._clip and self.panel._has_clip_focus():
                    if t == QEvent.KeyPress:
                        self.panel.paste_faces()
                    ev.accept()
                    return True
        except Exception:                                        # noqa: BLE001
            log.exception(T("SubD drag failed"))
            self.panel._drag = None
        return False


class _LazyPoints:
    """``pt[k]`` as a QPointF, made when asked (a skin can have tens of thousands)."""
    def __init__(self, xs, ys) -> None:
        self.xs, self.ys = xs, ys

    def __getitem__(self, k):
        return QPointF(float(self.xs[int(k)]), float(self.ys[int(k)]))


def _face_count(group) -> int:
    try:
        return len(group.mesh.faces)
    except Exception:                                            # noqa: BLE001
        return 0


def _icon(key: str):
    from . import icons
    return icons.tool_icon(key)


def setup(app) -> None:
    global _SCENE
    _SCENE = app.scene
    panel = SubdPanel(app)
    scroll = QScrollArea()                    # the panel is taller than many screens
    scroll.setWidgetResizable(True)
    scroll.setFrameShape(QScrollArea.NoFrame)
    scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
    scroll.setWidget(panel)
    panel._scroll = scroll
    try:                                   # the tab's icon (older hosts: no icon= argument)
        dock = app.add_panel("SubD", scroll, icon=_icon("subd_create"))
    except TypeError:
        dock = app.add_panel("SubD", scroll)
    app.on_document_changed(panel.refresh)
    app.add_overlay(panel.draw)
    app.add_pickable(panel.pick_item, on_select=panel.on_select, delete=panel.delete_item)
    if hasattr(app, "add_context_menu"):
        app.add_context_menu(panel.context_menu)
    panel.axis.currentIndexChanged.connect(lambda _i: app.viewport.update())
    panel._filter = _DragFilter(panel)                 # freestyle dragging
    app.viewport.installEventFilter(panel._filter)
    app.viewport.setMouseTracking(True)           # so the item under the cursor can light up
    app.add_menu_action(T("SubD panel"), lambda: app.show_panel(dock), None,
                        tip=T("Show the subdivision-modelling panel."))
