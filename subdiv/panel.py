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
from PySide6.QtCore import QEvent, QObject, QPointF, QSize, Qt
from PySide6.QtGui import QBrush, QColor, QPen, QPolygonF, QVector3D
from PySide6.QtWidgets import (
    QButtonGroup, QCheckBox, QComboBox, QDoubleSpinBox, QGridLayout,
    QHBoxLayout, QLabel, QPushButton, QScrollArea, QSpinBox, QToolButton,
    QVBoxLayout, QWidget,
)

from core import units
from . import group as subdiv_group
from . import ops as subdiv_ops
from core.group import Group
from core.history import Command
from core.mesh import Mesh

from .edit import Cage

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
        self._building = True

        lay = QVBoxLayout(self)
        row = QHBoxLayout()
        row.addWidget(QLabel("SubD group"))
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
            b.setText(spec.label)
            b.setIcon(_icon(spec.icon))
            b.setIconSize(QSize(34, 34))
            b.setToolButtonStyle(Qt.ToolButtonTextUnderIcon)
            b.setToolTip(f"{spec.label} — {subdiv_ops.tip_for(spec)}")
            b.setAutoRaise(True)
            b.clicked.connect(lambda _c=False, k=spec.key: self._pick_tool(k))
            self.buttons.addButton(b)
            grid.addWidget(b, n // 4, n % 4)
            setattr(self, f"_btn_{spec.key}", b)
        lay.addLayout(grid)

        self.hint = QLabel()
        self.hint.setWordWrap(True)
        lay.addWidget(self.hint)

        vrow = QHBoxLayout()
        self.value_label = QLabel()
        vrow.addWidget(self.value_label)
        self.value = QDoubleSpinBox()
        self.value.setDecimals(2)
        vrow.addWidget(self.value, 1)
        self.axis = QComboBox()
        for text, data in (("Auto", "auto"), ("X", "x"), ("Y", "y"), ("Z", "z")):
            self.axis.addItem(text, data)
        self.axis.setToolTip("Direction for Edit, Stretch and Squeeze "
                             "(Auto: the face's normal / ring)")
        vrow.addWidget(self.axis)
        self.side = QComboBox()
        for text, data in (("Outside", "outside"), ("Inside", "inside"), ("Centred", "center")):
            self.side.addItem(text, data)
        self.side.setToolTip("Where the wall grows from the current surface")
        vrow.addWidget(self.side)
        self.cut = QComboBox()
        for text, data in (("Whole loop", "loop"), ("Only this face", "face")):
            self.cut.addItem(text, data)
        self.cut.setToolTip("Divide a face or an edge. Whole loop: the cut runs on round the "
                            "piece through the quads beyond (clean quads). Only this face: "
                            "just the face (or the faces touching the edge) is cut; the "
                            "neighbours get an extra point.")
        vrow.addWidget(self.cut)
        lay.addLayout(vrow)

        self.selection_label = QLabel()
        lay.addWidget(self.selection_label)
        self.apply_btn = QPushButton("Apply")
        self.apply_btn.clicked.connect(self.apply)
        lay.addWidget(self.apply_btn)
        self.status = QLabel()                     # right under Apply, so the answer is
        self.status.setWordWrap(True)              # always in view (no scrolling)
        lay.addWidget(self.status)

        sym = QHBoxLayout()
        self.sym_box = QCheckBox("Symmetry")
        self.sym_box.setToolTip("Repeat every edit on the other side of the plane.")
        self.sym_box.toggled.connect(self._sym_toggled)
        sym.addWidget(self.sym_box)
        self.sym_axis = QComboBox()
        for text, data in (("X", (1.0, 0.0, 0.0)), ("Y", (0.0, 1.0, 0.0)),
                           ("Z", (0.0, 0.0, 1.0))):
            self.sym_axis.addItem(text, data)
        self.sym_axis.setToolTip("Axis the plane is perpendicular to.")
        sym.addWidget(self.sym_axis)
        centre = QPushButton("Centre")
        centre.setToolTip("Put the plane through the middle of the piece.")
        centre.clicked.connect(self._sym_centre)
        sym.addWidget(centre)
        face = QPushButton("From face")
        face.setToolTip("Use the plane of the selected face.")
        face.clicked.connect(self._sym_from_face)
        sym.addWidget(face)
        lay.addLayout(sym)

        join = QHBoxLayout()
        join.addWidget(QLabel("Join with"))
        self.join_with = QComboBox()
        self.join_with.setToolTip("Another SubD group to merge into this one, "
                                  "so Bridge can link their openings.")
        join.addWidget(self.join_with, 1)
        join_btn = QPushButton("Join")
        join_btn.clicked.connect(self.join)
        join.addWidget(join_btn)
        split_btn = QPushButton("Split")
        split_btn.setToolTip("Undo a Join: every separate piece of this group "
                             "becomes its own SubD group again.")
        split_btn.clicked.connect(self.split)
        join.addWidget(split_btn)
        lay.addLayout(join)

        conv = QHBoxLayout()
        conv.addWidget(QLabel("Convert group"))
        self.convertible = QComboBox()
        self.convertible.setToolTip("Groups not made by this plugin. Their faces become "
                                    "the cage, so use a coarse one (under 7000 faces; editing gets slow above a few hundred).")
        conv.addWidget(self.convertible, 1)
        lay.addLayout(conv)
        conv2 = QHBoxLayout()
        conv2.addWidget(QLabel("Crease edges over"))
        self.angle = QDoubleSpinBox()
        self.angle.setRange(0.0, 180.0)
        self.angle.setDecimals(0)
        self.angle.setValue(30.0)
        self.angle.setSuffix("°")
        self.angle.setToolTip("Edges where two faces meet at more than this angle stay "
                              "sharp. 0 = no automatic creases (everything rounds).")
        conv2.addWidget(self.angle)
        convert = QPushButton("Convert to SubD")
        convert.setToolTip("Replace the chosen group by a SubD group built on its faces. "
                           "Ctrl+Z brings the original back.")
        convert.clicked.connect(self.convert)
        conv2.addWidget(convert, 1)
        lay.addLayout(conv2)
        self.sharp_create = QCheckBox("Create with sharp edges (angle above)")
        self.sharp_create.setToolTip(
            "Create then gives a crisp box instead of a rounded block: the edges of the "
            "new box stay sharp when the angle above is below 90 degrees (30 is fine). "
            "Stretch, Grow and Shell then work on a rectilinear piece.")
        lay.addWidget(self.sharp_create)

        look = QHBoxLayout()
        look.addWidget(QLabel("Smoothing"))
        self.levels = QSpinBox()
        self.levels.setRange(0, 4)
        self.levels.setValue(4)
        self.levels.setToolTip("Subdivision steps: 0 is the cage itself.")
        look.addWidget(self.levels)
        self.auto = QCheckBox("Auto")
        self.auto.setChecked(True)
        self.auto.setToolTip("Smoothest level that keeps the surface under "
                             "about 25 000 triangles; uncheck to choose it yourself.")
        self.auto.toggled.connect(self._on_auto)
        look.addWidget(self.auto)
        self.lines = QComboBox()
        for text, data in (("Cage lines", "cage"), ("All edges", "all"), ("No lines", "none")):
            self.lines.addItem(text, data)
        look.addWidget(self.lines, 1)
        lay.addLayout(look)
        upd = QPushButton("Update look")
        upd.setToolTip("Rebuild the surface with this smoothing and these lines.")
        upd.clicked.connect(self.update_look)
        flip = QPushButton("Flip faces")
        flip.setToolTip("Blue faces are seen from behind. Flip turns the whole piece "
                        "inside out so the front and the back swap.")
        flip.clicked.connect(self.flip)
        urow = QHBoxLayout()
        urow.addWidget(upd)
        urow.addWidget(flip)
        lay.addLayout(urow)
        frow = QHBoxLayout()
        frow.addWidget(QLabel("Finish detail"))
        self.finish_detail = QComboBox()
        self.finish_detail.addItem("Automatic (light)", "auto")
        self.finish_detail.addItem("Same as the view", None)
        self.finish_detail.addItem("Light (1)", 1)
        self.finish_detail.addItem("Medium (2)", 2)
        self.finish_detail.addItem("Fine (3)", 3)
        self.finish_detail.setToolTip(
            "How finely the curved parts are cut when the piece is finished."
            " Automatic keeps the result under about %d faces so ordinary tools "
            "stay fast (the smoothest level that fits). Each step up multiplies the "
            "triangles by four. Flat faces are always single polygons, whatever you "
            "choose." % FINISH_BUDGET)
        frow.addWidget(self.finish_detail, 1)
        lay.addLayout(frow)
        fin = QPushButton("Finish")
        fin.setToolTip("Finish (no longer SubD): keep the smooth surface as an ordinary "
                       "group and drop the cage. If the cage is closed and sound, the "
                       "result is a Solid Group (usable with Solid Tools) and its "
                       "volume is reported; if it is still open, you get the surface "
                       "and the reason. Undo brings the SubD group back.")
        fin.clicked.connect(self.finish)
        lay.addWidget(fin)
        hrow = QHBoxLayout()
        hrow.addWidget(QLabel("Handles"))
        self.handles = QComboBox()
        self.handles.addItem("Move + Rotate", "both")
        self.handles.addItem("Move only", "move")
        self.handles.addItem("Rotate only (protractor)", "rotate")
        self.handles.setToolTip(
            "Move: drag a coloured tip to slide the selection along that axis.\n"
            "Rotate: drag a coloured ring to turn the selection around that axis "
            "(hold Ctrl to snap to 15 degrees).\n"
            "Both are shown by default; pick one to keep the view clear.")
        self.handles.currentIndexChanged.connect(lambda _i: self.app.viewport.update())
        hrow.addWidget(self.handles, 1)
        self.show_cage = QCheckBox("Show cage")
        self.show_cage.setChecked(True)
        self.show_cage.toggled.connect(lambda _on: self.app.viewport.update())
        hrow.addWidget(self.show_cage)
        lay.addLayout(hrow)

        lay.addStretch(1)

        self._building = False
        self.levels.setEnabled(not self.auto.isChecked())
        getattr(self, f"_btn_{self.tool}").setChecked(True)
        self._pick_tool(self.tool)
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
        self.hint.setText(subdiv_ops.tip_for(spec, self._unit_name()))
        has_value = bool(spec.value_label)
        self.value_label.setText(spec.value_label)
        self.value_label.setVisible(has_value)
        self.value.setVisible(has_value)
        self.axis.setVisible(spec.axis)
        self.side.setVisible(self.tool == "shell")
        self.cut.setVisible(self.tool == "divide")
        suffix = "  (waiting for the second opening)" if self.pending else ""
        self.selection_label.setText(subdiv_ops.describe_many(self._sels()) + suffix)
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

    def _unit_name(self) -> str:
        """The document's length unit as shown in the value box (m, mm, in...)."""
        return _SUFFIX.get(self._unit, " m").strip()

    def _refresh_tips(self) -> None:
        """Tool tips and the hint line follow the document's unit."""
        name = self._unit_name()
        for b, spec in zip(self.buttons.buttons(), subdiv_ops.TOOL_SPECS):
            b.setToolTip(f"{spec.label} — {subdiv_ops.tip_for(spec, name)}")
        self.hint.setText(subdiv_ops.tip_for(subdiv_ops.SPECS[self.tool], name))

    def _units_refresh(self) -> None:
        """Follow the document's unit (mm, cm, in…): the model itself is metres."""
        try:
            unit, scale = units.model_unit(), float(units.bare_number_scale())
        except Exception:                                    # noqa: BLE001
            unit, scale = "m", 1.0
        if unit != self._unit or abs(scale - self._scale) > 1e-12:
            keep = self._metres() if self._unit is not None else None
            self._unit, self._scale = unit, scale
            self._configure_value(keep)
            self._refresh_tips()

    def _pick_tool(self, key: str) -> None:
        if key != self.tool:
            self.pending = None
            self._bridge_first = None
        self.tool = key
        self._units_refresh()
        self._configure_value()
        self._sync()

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
                self._say("Bridge: now click the other face (or an edge of the other opening)")
            else:                                     # second click: bridge straight away
                self.extra = [first]
                self.apply()
                self._auto_bridged = True
                self._bridge_first = item if self.sel is not None else None
                self.extra = []
        elif self.tool != "bridge":
            self._bridge_first = None
        self._sync()

    def _activate_under(self, px: float, py: float) -> bool:
        """A press on a point of another SubD group's cage makes that group
        the active one (unless the active cage is hit first)."""
        if self.pick_item(None, px, py) is not None:
            return False
        for other in self._others():
            cage = _state(other)[0]
            xs, ys, front = self.app.world_to_pixels(np.array(cage.verts, dtype=float))
            if subdiv_ops.pick(cage, xs.tolist(), ys.tolist(), front.tolist(), px, py):
                self.active_uid = other.uid
                self._clear_sel()
                self.pending = None
                return True
        return False

    def pick_item(self, viewport, px: float, py: float, skip=()):
        g = self.active_group()
        if g is None or not self.show_cage.isChecked():
            return None
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
    def _commit(self, old, cage: Cage, levels: int, lines: str) -> None:
        vp = self.app.viewport
        if not cage.is_consistent():
            cage.orient()                   # mixed winding shows as blue back faces
        if self.auto.isChecked():
            levels = subdiv_group.auto_levels(cage)
        name = old.name if old is not None else "SubD"
        new = subdiv_group.build_group(cage, levels, Group, Mesh, QVector3D,
                                       name=name, lines=lines)
        if old is not None:
            subdiv_group.carry_over(old, new)
        vp.history.execute(_Swap(old, new))
        err = getattr(vp.history, "last_error", None)
        if err:
            self._say(f"Could not apply: {err}")
            return
        self.active_uid = new.uid
        notify = getattr(vp, "notify_scene_changed", None)
        if callable(notify):
            notify()
        vp.update()

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
        if self.tool == "bridge":                      # click one end, Shift+click the other
            sels = self._sels()
            if len(sels) != 2:
                raise ValueError("Bridge: select two faces (click one, Shift+click the other)")
            return subdiv_ops.bridge_two(cage, sels[0], sels[1], self._metres())
        if self.tool != "edit":
            raise ValueError("Several items are selected: use Edit cage or Crease on "
                             "them, or click one item for this tool")
        vec = AXIS_VEC.get(self.axis.currentData())
        if vec is None:
            raise ValueError("Choose X, Y or Z to move several items together")
        delta = tuple(c * self._metres() for c in vec)
        subdiv_ops.symmetric_move(cage, subdiv_ops.vertex_union(cage, self._sels()),
                                  delta, cage.sym)
        return subdiv_ops.Result(None, "Moved")

    def apply(self) -> None:
        try:
            if self.tool == "create":
                self._create()
                return
            g = self.active_group()
            if g is None:
                raise ValueError("Create a SubD box first, or choose a SubD group")
            cage, levels, lines = _state(g)
            cage = cage.copy()
            if self.extra:
                res = self._apply_many(cage)
            else:
                res = subdiv_ops.apply_tool(
                    cage, self.tool, self.sel, self._metres(),
                    self._mode(), self.pending, sym=cage.sym)
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
        self._say("Sharp-edged SubD box created — click a point, edge or face of the cage"
                  if sharp else "SubD box created — click a point, edge or face of the cage")
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
            self._say("Create or choose a SubD group first")
            return
        cage, levels, lines = _state(g)
        cage = cage.copy()
        if cage.sym is None:
            point, normal = self._plane_centre(cage)
            cage.sym = {"on": on, "point": point, "normal": normal}
        else:
            cage.sym["on"] = on
        self._write_settings(g, cage, levels, lines,
                             "Symmetry on" if on else "Symmetry off")

    def _sym_centre(self) -> None:
        g = self.active_group()
        if g is None:
            self._say("Create or choose a SubD group first")
            return
        cage, levels, lines = _state(g)
        cage = cage.copy()
        point, normal = self._plane_centre(cage)
        on = self.sym_box.isChecked() or (cage.sym is not None and cage.sym["on"])
        cage.sym = {"on": on, "point": point, "normal": normal}
        self._write_settings(g, cage, levels, lines, "Plane set through the centre")

    def _sym_from_face(self) -> None:
        g = self.active_group()
        if g is None or not self.sel or self.sel[0] != "f":
            self._say("Select a face first: its plane becomes the symmetry plane")
            return
        cage, levels, lines = _state(g)
        cage = cage.copy()
        on = self.sym_box.isChecked() or (cage.sym is not None and cage.sym["on"])
        cage.sym = {"on": on, "point": cage.face_centroid(self.sel[1]),
                    "normal": cage.face_normal(self.sel[1])}
        self._write_settings(g, cage, levels, lines, "Plane set from the face")

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
            self._say("Choose a second SubD group under \"Join with\"")
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
            self._say(f"Could not join: {err}")
            return
        self.active_uid = new.uid
        self._clear_sel()
        notify = getattr(vp, "notify_scene_changed", None)
        if callable(notify):
            notify()
        self._say("Joined. Choose Bridge, then click a face on each piece (Apply after each)")
        vp.update()

    def split(self) -> None:
        """Undo a Join: every piece of the cage that shares no point with the
        others becomes its own SubD group again."""
        g = self.active_group()
        if g is None:
            self._say("No SubD group to split")
            return
        cage, levels, lines = _state(g)
        parts = cage.components()
        if len(parts) < 2:
            self._say("Nothing to split: this is one connected piece. After a "
                      "Bridge, delete the bridge's faces (Delete F) to separate the "
                      "pieces first")
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
            self._say(f"Could not split: {err}")
            return
        self.active_uid = news[0].uid
        self._clear_sel()
        self.pending = None
        notify = getattr(vp, "notify_scene_changed", None)
        if callable(notify):
            notify()
        self._say(f"Split into {len(news)} separate SubD groups (Ctrl+Z to join them back)")
        vp.update()

    def convert(self) -> None:
        uid = self.convertible.currentData()
        g = next((x for x in self.app.scene.groups if x.uid == uid), None)
        if g is None:
            self._say("No group to convert: make or import one first")
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
        note = f" ({holes} faces lost their holes)" if holes else ""
        self._say(f"Converted: {len(cage.faces)} faces, {creased} sharp edges{note}")
        self._sync()

    def update_look(self) -> None:
        g = self.active_group()
        if g is None:
            self._say("No SubD group to update")
            return
        cage = _state(g)[0].copy()
        self._commit(g, cage, int(self.levels.value()), self.lines.currentData())
        self._say("Look updated")

    def flip(self) -> None:
        """Turn the whole piece inside out: the faces seen from behind (the
        blue ones) become the front, and the front ones the back."""
        g = self.active_group()
        if g is None:
            self._say("No SubD group to flip")
            return
        cage = _state(g)[0].copy()
        cage.flip()
        self._commit(g, cage, int(self.levels.value()), self.lines.currentData())
        self._say("Faces flipped")

    def finish(self) -> None:
        """Stop treating the active group as SubD: it becomes an ordinary
        group made of the smooth surface, where every flat patch (a box face)
        is a single polygon so the other tools stay fast. A closed, sound cage
        is re-oriented outwards and the volume reported (Solid Group); an open
        one is finished as a plain surface. One undo step brings the cage back."""
        g = self.active_group()
        if g is None:
            self._say("No SubD group to finish")
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
            self._say(f"Could not finish: {err}")
            return
        self._clear_sel()
        self.pending = None
        notify = getattr(vp, "notify_scene_changed", None)
        if callable(notify):
            notify()
        if ok:
            shown = vol / (self._scale ** 3) if self._scale else vol
            text = (f"Finished, solid group ({_face_count(new)} faces): volume {vol:.4g} m³ "
                    f"({shown:.6g} {_SUFFIX.get(self._unit, ' m').strip()}³)")
            try:
                from core import solids
                if solids.solid_volume(new) is None:
                    text += " — not counted as a solid by Solid Tools; check for coincident points"
            except Exception:                                    # noqa: BLE001
                pass
        else:
            why = "; ".join(p for p in problems if "re-oriented" not in p)
            text = (f"Finished, surface only ({_face_count(new)} faces), not a solid: {why}")
        self._say(text + " (Ctrl+Z to edit the cage again)")
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

    def draw(self, viewport, painter) -> None:
        if not self.show_cage.isChecked():
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
        keys = [chosen] if chosen in AXIS_VEC else list(AXIS_VEC)
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
        keys = [chosen] if chosen in AXIS_VEC else list(AXIS_VEC)
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
    def mouse_press(self, ev) -> bool:
        """Press on a cage handle with the Select tool: select it and get
        ready to drag. Anything else is left to the viewport (returns False)."""
        vp = self.app.viewport
        mods = ev.modifiers()
        if mods & (Qt.ControlModifier | Qt.AltModifier):
            return False
        shift = bool(mods & Qt.ShiftModifier)
        if getattr(getattr(vp, "active_tool", None), "name", "") != "Select":
            return False
        if not self.show_cage.isChecked():
            return False
        pos = ev.position()
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
            self._say(f"{note} ({len(items)} edge{'s' if len(items) > 1 else ''}) - "
                      "click again for the next contour")
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
        subdiv_ops.symmetric_move(prev, d["vset"], delta, d["sym"])
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
            self._say(f"Rotated {math.degrees(d['angle']):+.1f}\u00b0 around {d['rot'].upper()}")
        elif d["started"] and any(abs(c) > 1e-9 for c in d["delta"]):
            cage = d["base"].copy()
            subdiv_ops.symmetric_move(cage, d["vset"], d["delta"], d["sym"])
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
            if t == QEvent.MouseButtonPress and ev.button() == Qt.LeftButton:
                return bool(self.panel.mouse_press(ev))
            if t == QEvent.MouseMove:
                return bool(self.panel.mouse_move(ev))
            if t == QEvent.MouseButtonRelease and ev.button() == Qt.LeftButton:
                return bool(self.panel.mouse_release(ev))
            if t == QEvent.KeyPress and ev.key() == Qt.Key_Escape:
                return bool(self.panel.cancel_drag())
        except Exception:                                        # noqa: BLE001
            log.exception("SubD drag failed")
            self.panel._drag = None
        return False


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
    dock = app.add_panel("SubD", scroll)
    app.on_document_changed(panel.refresh)
    app.add_overlay(panel.draw)
    app.add_pickable(panel.pick_item, on_select=panel.on_select)
    panel.axis.currentIndexChanged.connect(lambda _i: app.viewport.update())
    panel._filter = _DragFilter(panel)                 # freestyle dragging
    app.viewport.installEventFilter(panel._filter)
    app.add_menu_action("SubD panel", lambda: app.show_panel(dock), None,
                        tip="Show the subdivision-modelling panel.")
