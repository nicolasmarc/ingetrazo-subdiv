# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 IngeTrazo contributors.
"""The twelve subdivision tools as plain functions on a :class:`Cage`.

This is the logic behind the SubD side panel, kept free of Qt so it can be
tested without a window: which selection each tool needs, what it does with
the panel's value, and what to select afterwards.

A selection is one of ``("v", i)``, ``("e", a, b)`` or ``("f", i)``.
A tool that cannot act on the current selection raises ``ValueError`` with a
sentence meant for the status bar.
"""
from __future__ import annotations

from .lang import T as _T

import math
from typing import Callable, NamedTuple, Sequence

import numpy as np

from .edit import Cage, ekey
from . import modeling
from .subdivide import _step as _subdivide_step

Selection = tuple


class ToolSpec(NamedTuple):
    key: str            # short id, also the panel's button id
    icon: str           # key in icons.SUBD_ICONS
    label: str
    tip: str            # what it needs and does
    value_label: str    # "" = the tool takes no value
    default: float
    lo: float
    hi: float
    step: float
    axis: bool          # does the panel's axis choice matter?
    length: bool = False    # is the value a length (shown in the model's unit)?


TOOL_SPECS = [
    ToolSpec("create", "subd_create", "Create",
             "New box cage (size in {unit}), with its lower corner on the origin.",
             "Size", 1.0, 0.05, 1000.0, 0.1, False, True),
    ToolSpec("edit", "subd_edit", "Edit cage",
             "Move the selected point, edge or face along an axis.",
             "Move by", 0.25, -1000.0, 1000.0, 0.05, True, True),
    ToolSpec("crease", "subd_crease", "Crease",
             "Keep the selected edge (or the edges of a face) sharp for N levels; 0 clears. "
             "A fraction (1.5, 0.5...) gives a softer edge, and a selected point becomes a "
             "corner. With nothing selected it applies to every edge; with several selected "
             "(Shift+click, or click an edge again for its contour) to all their edges. "
             "The value starts at the smoothing level, which keeps the edge crisp; "
             "a smaller one leaves a small radius.",
             "Sharpness", 2.0, 0.0, 6.0, 0.5, False),
    ToolSpec("grow_face", "subd_grow_face", "Grow F",
             "Push the selected face out along its normal.",
             "Height", 0.5, -1000.0, 1000.0, 0.05, False, True),
    ToolSpec("grow_edge", "subd_grow_edge", "Grow E",
             "Extend the selected open edge into a new strip (Auto). With a whole contour "
             "selected (click an edge again for its contour) it is extruded outwards; "
             "with X, Y or Z chosen the whole contour of the edge goes along that axis "
             "(negative distance goes the other way).",
             "Distance", 0.5, -1000.0, 1000.0, 0.05, True, True),
    ToolSpec("stretch", "subd_stretch", "Stretch",
             "Scale the selection along an axis. A face stretched along its own normal "
             "stretches the whole piece that way, the far side staying put.",
             "Factor", 1.5, 0.05, 20.0, 0.05, True),
    ToolSpec("inset_face", "subd_inset_face", "Offset F",
             "Add a smaller copy of the selected face inside it.",
             "Inset (0-0.95)", 0.3, 0.0, 0.95, 0.05, False),
    ToolSpec("offset_edge", "subd_offset_edge", "Offset E",
             "Run a new loop inside the open border the selected edge belongs to.",
             "Inset (0-0.95)", 0.3, 0.0, 0.95, 0.05, False),
    ToolSpec("squeeze", "subd_squeeze", "Squeeze",
             "Pinch the selected face's ring (or the open contour of the selected edge, or the "
             "contour selected with repeated clicks) towards its axis.",
             "Factor", 0.6, 0.0, 5.0, 0.05, True),
    ToolSpec("divide", "subd_divide", "Divide",
             "Cut the selected face in four (each cut runs on round the piece as a loop, or "
             "this face only), or select an edge to cut across it (the whole loop, or only "
             "the faces touching that edge).",
             "", 0.0, 0.0, 0.0, 0.0, False),
    ToolSpec("delete_face", "subd_delete_face", "Delete F",
             "Remove the selected face, leaving an opening to Close or Bridge.",
             "", 0.0, 0.0, 0.0, 0.0, False),
    ToolSpec("close", "subd_close", "Close",
             "Fill the open border the selected edge belongs to.",
             "", 0.0, 0.0, 0.0, 0.0, False),
    ToolSpec("bridge", "subd_bridge", "Bridge",
             "Click a face (or an edge of an opening), then click the other one: the "
             "bridge is made at the second click, the faces removed and joined by a ring "
             "of quads. (Shift+click then Apply, or Apply after each, also work.) "
             "Twist turns the ring by that many points; set it before the second click.",
             "Twist", 0.0, -50.0, 50.0, 1.0, False),
    ToolSpec("shell", "subd_shell", "Shell",
             "Give the whole piece a wall: choose Inside, Outside or Centred, then "
             "Apply. An open piece becomes a thick sheet, a closed one a hollow body.",
             "Thickness", 0.05, 0.001, 1000.0, 0.01, False, True),
    ToolSpec("revolve", "subd_revolve", "Revolve",
             "Turn the selected face (the profile, drawn away from the axis) round the X, Y or Z "
             "axis through the origin into a body of revolution. Points on the axis become poles. "
             "The profile can also be a plain face or plain lines from your drawing (select "
             "them in the model, then Apply).",
             "Segments", 12.0, 3.0, 96.0, 1.0, True),
    ToolSpec("bevel", "subd_bevel", "Bevel",
             "Replace the selected edge by a narrow flat strip, to give a corner a support "
             "or a chamfer. Click an edge again for its loop to bevel the whole loop.",
             "Width", 0.1, 0.001, 1000.0, 0.01, False, True),
    ToolSpec("loft", "subd_loft", "Loft",
             "Pass a surface through several faces used as sections: SubD faces (click one, "
             "Shift+click the others) or plain faces from your drawing (select them, then "
             "Apply). They are taken in the order they lie along the piece. The sections "
             "stay where they are. Choose whether the ends are closed.",
             "Segments", 1.0, 1.0, 32.0, 1.0, False),
    ToolSpec("sweep", "subd_sweep", "Sweep",
             "Carry a face (the profile) along a path: select the face, then Shift+click the "
             "edges of the path, which must be one chain. The profile turns to follow the path. "
             "The profile and the path can also be a plain face and plain lines from your "
             "drawing (select them in the model, then Apply).",
             "Twist (deg)", 0.0, -1440.0, 1440.0, 5.0, False),
    ToolSpec("slice", "subd_slice", "Slice",
             "Cut the cage with a plane perpendicular to X, Y or Z through the selected "
             "item (or the middle of the piece), moved by the value.",
             "Offset", 0.0, -1000.0, 1000.0, 0.05, True, True),
    ToolSpec("merge", "subd_merge", "Merge",
             "Select an edge or a face to merge its points at the middle, or a point to "
             "merge every point within the distance into it.",
             "Distance", 0.01, 0.0001, 1000.0, 0.01, False, True),
    ToolSpec("dissolve", "subd_dissolve", "Dissolve",
             "Remove the selected edge (its two faces become one) or point, keeping the "
             "surface closed.",
             "", 0.0, 0.0, 0.0, 0.0, False),
    ToolSpec("slide", "subd_slide", "Slide",
             "Slide the loop through the selected edge sideways, by a fraction of the way to "
             "its neighbour (negative goes the other way). Click an edge again for its loop.",
             "Slide (-0.9..0.9)", 0.25, -0.9, 0.9, 0.05, False),
]
SPECS = {s.key: s for s in TOOL_SPECS}


def tip_for(spec, unit: str = "m") -> str:
    """``spec.tip`` with ``{unit}`` replaced by the document's length unit
    (the value box follows the document: mm, cm, m, in...)."""
    return spec.tip.replace("{unit}", unit)


class Result(NamedTuple):
    selection: Selection | None     # what to select next (None = nothing)
    message: str                    # for the status bar
    pending: object = None          # a half-done tool (Bridge between its two clicks)


# ---- selection helpers -----------------------------------------------------------------
def describe(sel: Selection | None) -> str:
    if not sel:
        return _T("Nothing selected")
    return {"v": lambda: _T("Point {i}", i=sel[1]), "e": lambda: _T("Edge {a}-{b}", a=sel[1], b=sel[2]),
            "f": lambda: _T("Face {i}", i=sel[1])}[sel[0]]()


def vertex_union(cage: Cage, sels) -> list[int]:
    """The points of every selected item, each once, in order."""
    out: list[int] = []
    for sel in sels:
        for v in vertex_set(cage, sel):
            if v not in out:
                out.append(v)
    return out


def describe_many(sels) -> str:
    sels = [s for s in sels if s]
    if len(sels) <= 1:
        return describe(sels[0] if sels else None)
    return _T("{n} items selected (Shift+click adds or removes one)", n=len(sels))


def valid(cage: Cage, sel: Selection | None) -> bool:
    """Does the selection still point at something in this cage?"""
    if not sel:
        return False
    n = len(cage.verts)
    if sel[0] == "v":
        return 0 <= sel[1] < n
    if sel[0] == "e":
        return ekey(sel[1], sel[2]) in cage.edge_faces()
    return sel[0] == "f" and 0 <= sel[1] < len(cage.faces)


def vertex_set(cage: Cage, sel: Selection) -> list[int]:
    if sel[0] == "v":
        return [sel[1]]
    if sel[0] == "e":
        return [sel[1], sel[2]]
    return list(cage.faces[sel[1]])


def _need(sel, kind: str, what: str) -> Selection:
    if not sel or sel[0] not in kind:
        raise ValueError(_T('Select {what} first', what=what))
    return sel


def _axis(cage: Cage, sel: Selection | None, axis):
    if isinstance(axis, tuple):                      # an explicit direction
        return axis
    if axis in ("x", "y", "z"):
        return {"x": (1.0, 0.0, 0.0), "y": (0.0, 1.0, 0.0), "z": (0.0, 0.0, 1.0)}[axis]
    if sel and sel[0] == "f":
        return cage.face_normal(sel[1])
    return (0.0, 0.0, 1.0)


def _open_loop(cage: Cage, sel) -> list[int]:
    """The open border (boundary loop) the selected edge lies on."""
    _need(sel, "e", _T("an open edge"))
    a, b = sel[1], sel[2]
    for loop in cage.boundary_loops():
        n = len(loop)
        if any({loop[i], loop[(i + 1) % n]} == {a, b} for i in range(n)):
            return loop
    raise ValueError(_T("That edge is not on an open border"))


# ---- the tools ----------------------------------------------------------------------------
def _edit(cage, sel, value, axis, pending):
    _need(sel, "vef", _T("a point, edge or face"))
    d = _axis(cage, sel, axis)
    cage.move(vertex_set(cage, sel), (d[0] * value, d[1] * value, d[2] * value))
    return Result(sel, "Moved")


def _crease(cage, sel, value, axis, pending):
    if not sel:                                    # nothing selected: every edge
        cage.set_crease(cage.edges(), value)
        return Result(None, _T("All creases cleared") if value <= 0
                      else _T('Every edge creased {value}', value=format(value, 'g')))
    _need(sel, "vef", _T("a point, an edge or a face"))
    if sel[0] == "v":
        cage.set_vertex_crease([sel[1]], value)
        return Result(sel, _T("Corner cleared") if value <= 0
                      else _T('Corner {value}', value=format(value, 'g')))
    if sel[0] == "e":
        edges = [(sel[1], sel[2])]
    else:
        f = cage.faces[sel[1]]
        edges = [(f[i], f[(i + 1) % len(f)]) for i in range(len(f))]
    cage.set_crease(edges, value)
    return Result(sel, _T("Crease cleared") if value <= 0 else _T('Crease {value}', value=format(value, 'g')))


def crease_items(cage: Cage, sels, value: float) -> Result:
    """Crease (or, with 0, round off) every edge of several selected items at
    once: edges as picked, faces by their outline. Points alone have no edge."""
    edges: list[tuple[int, int]] = []
    seen = set()
    points = [s[1] for s in sels if s and s[0] == "v"]
    if points:
        cage.set_vertex_crease(points, value)
    for sel in sels:
        if not sel:
            continue
        if sel[0] == "e":
            pairs = [(sel[1], sel[2])]
        elif sel[0] == "f":
            f = cage.faces[sel[1]]
            pairs = [(f[i], f[(i + 1) % len(f)]) for i in range(len(f))]
        else:
            continue
        for a, b in pairs:
            if ekey(a, b) not in seen:
                seen.add(ekey(a, b))
                edges.append((a, b))
    if not edges and points:
        n = len(points)
        return Result(None, (_T('{n} corners rounded off', n=n) if value <= 0
                             else _T('{n} corners creased {value}', n=n, value=format(value, 'g'))))
    if not edges:
        raise ValueError(_T("Select edges or faces first"))
    cage.set_crease(edges, value)
    n = len(edges)
    return Result(None, (_T('{n} edges rounded off', n=n) if n > 1 else _T('{n} edge rounded off', n=n)) if value <= 0
                  else (_T('{n} edges creased {value}', n=n, value=format(value, 'g')) if n > 1
                       else _T('{n} edge creased {value}', n=n, value=format(value, 'g'))))


def _grow_face(cage, sel, value, axis, pending):
    _need(sel, "f", _T("a face"))
    cage.extrude_face(sel[1], value)
    return Result(sel, _T("Face grown"))


def _outward(cage, a, b):
    """Unit direction that leads away from the face an open edge belongs to
    (in that face's plane), or None when it cannot be told."""
    fi = cage.edge_faces()[ekey(a, b)][0]
    pa, pb = cage.verts[a], cage.verts[b]
    along = _unit_sub(pb, pa)
    mid = tuple((pa[i] + pb[i]) / 2 for i in range(3))
    away = _sub(mid, cage.face_centroid(fi))
    d = _sub(away, _mul(along, _dot(away, along)))
    n = math.sqrt(_dot(d, d))
    return None if n < 1e-12 else _mul(d, 1.0 / n)


def _grow_loop(cage, loop, value, axis):
    """Extrude a whole open contour: along X, Y or Z when chosen, otherwise along
    the contour's own normal, pointing away from the piece."""
    if axis in ("x", "y", "z"):
        d = _axis(cage, None, axis)
        where = _T('along {v0}', v0=axis.upper())
    else:
        pts = [cage.verts[v] for v in loop]
        nx = ny = nz = 0.0                      # the contour's own normal (Newell)
        for i, p in enumerate(pts):
            q = pts[(i + 1) % len(pts)]
            nx += (p[1] - q[1]) * (p[2] + q[2])
            ny += (p[2] - q[2]) * (p[0] + q[0])
            nz += (p[0] - q[0]) * (p[1] + q[1])
        n = math.sqrt(nx * nx + ny * ny + nz * nz)
        if n < 1e-12:
            raise ValueError(_T("Cannot tell which way is outward for that contour: "
                             "choose X, Y or Z"))
        c = tuple(sum(p[k] for p in pts) / len(pts) for k in range(3))
        mid = tuple(sum(p[k] for p in cage.verts) / len(cage.verts) for k in range(3))
        d = (nx / n, ny / n, nz / n)
        if _dot(d, _sub(c, mid)) < 0:           # point away from the piece, not into it
            d = _mul(d, -1.0)
        where = "outwards"
    new = cage.extrude_edges(list(loop) + [loop[0]], _mul(d, value))
    return Result(("e", new[0], new[1]), _T('Open contour of {v0} edges extruded {where}', v0=len(loop), where=where))


def _grow_edge(cage, sel, value, axis, pending):
    loop = _open_loop(cage, sel)
    if axis in ("x", "y", "z"):                      # the whole open contour, along that axis
        return _grow_loop(cage, loop, value, axis)
    a, b = sel[1], sel[2]
    d = _outward(cage, a, b)
    if d is None:
        raise ValueError(_T("Cannot tell which way is outward for that edge"))
    new = cage.extrude_edges([a, b], _mul(d, value))
    return Result(("e", new[0], new[1]), _T("Edge grown"))


def grow_items(cage, sels, value, axis="auto") -> Result:
    """Grow E with several edges selected (a contour picked with repeated clicks):
    they must be all the edges of one open contour; it is extruded as a whole."""
    if not sels or any(x[0] != "e" for x in sels):
        raise ValueError(_T("Grow E: select edges of an open contour"))
    loop = _open_loop(cage, sels[0])
    wanted = {ekey(loop[i], loop[(i + 1) % len(loop)]) for i in range(len(loop))}
    if {ekey(x[1], x[2]) for x in sels} != wanted:
        raise ValueError(_T("Select the whole open contour (click an edge again for its "
                         "contour), or a single edge"))
    return _grow_loop(cage, loop, value, axis)


def _stretch(cage, sel, value, axis, pending):
    _need(sel, "vef", _T("a point, edge or face"))
    ids = list(dict.fromkeys(vertex_set(cage, sel)))
    u = _axis(cage, sel, axis)
    n = math.sqrt(sum(c * c for c in u)) or 1.0
    u = tuple(c / n for c in u)
    proj = [sum(cage.verts[v][i] * u[i] for i in range(3)) for v in ids]
    all_proj = [sum(p[i] * u[i] for i in range(3)) for p in cage.verts]
    span = (max(all_proj) - min(all_proj)) or 1.0
    if max(proj) - min(proj) < 1e-6 * span:
        # The selection is flat across this direction (a face stretched along its
        # own normal): stretching it alone would do nothing, so the whole piece
        # is stretched along it, anchored on the far side from the selection.
        here = sum(proj) / len(proj)
        mid = (max(all_proj) + min(all_proj)) / 2.0
        anchor = min(all_proj) if here >= mid else max(all_proj)
        c0 = cage.verts[ids[0]]
        origin = tuple(c0[i] + u[i] * (anchor - proj[0]) for i in range(3))
        cage.stretch(list(range(len(cage.verts))), value, u, origin)
        return Result(sel, _T("Whole piece stretched (the selection alone has no length along that direction)"))
    cage.stretch(ids, value, u)
    return Result(sel, "Stretched")


def _inset_face(cage, sel, value, axis, pending):
    _need(sel, "f", _T("a face"))
    cage.inset_face(sel[1], value)
    return Result(sel, _T("Face offset"))


def _offset_edge(cage, sel, value, axis, pending):
    loop = _open_loop(cage, sel)
    new = cage.offset_edges(loop + [loop[0]], value)
    return Result(("e", new[0], new[1]), _T("Border offset"))


def _squeeze(cage, sel, value, axis, pending):
    _need(sel, "fe", _T("a face, or an edge of an open contour"))
    ax = _axis(cage, sel, axis) if axis != "auto" else None
    if sel[0] == "e":                                # an open edge: its whole contour
        cage.squeeze(_open_loop(cage, sel), value, ax)
        return Result(sel, _T("Open contour squeezed"))
    cage.squeeze(vertex_set(cage, sel), value, ax)
    return Result(sel, "Squeezed")


def squeeze_items(cage, sels, value, axis="auto") -> Result:
    """Squeeze with several items selected (a contour picked with repeated
    clicks, or a few faces): all their points are pinched together towards the
    axis through their centre (Auto: the ring's own normal)."""
    if not sels:
        raise ValueError(_T("Select a face or the edges of a contour first"))
    ax = _axis(cage, None, axis) if axis != "auto" else None
    ids = vertex_union(cage, sels)
    if len(ids) < 3:
        raise ValueError(_T("Select at least three points to squeeze"))
    cage.squeeze(ids, value, ax)
    return Result(sels[-1], "Squeezed")


def _divide(cage, sel, value, axis, pending):
    """Divide a face (``axis`` "face": that face only; otherwise the cut runs
    on round the piece as a loop) or cut the loop through a chosen edge."""
    _need(sel, "fe", _T("a face or an edge"))
    if sel[0] == "e":
        cage.loop_cut(sel[1], sel[2], whole=axis != "face")
        return Result(sel, _T("Loop cut") if axis != "face" else _T("Cut across the face"))
    if axis == "face":
        cage.divide_face_only(sel[1])
        return Result(sel, _T("Face divided"))
    cage.divide_face(sel[1])
    return Result(sel, _T("Face divided"))


def _delete_face(cage, sel, value, axis, pending):
    _need(sel, "f", _T("a face"))
    if len(cage.faces) <= 1:
        raise ValueError(_T("A cage needs at least one face"))
    cage.remove_faces([sel[1]])
    return Result(None, _T("Face deleted — Close it again or Bridge it to another opening"))

def _close(cage, sel, value, axis, pending):
    loop = _open_loop(cage, sel)
    return Result(("f", cage.close_hole(loop)), _T("Hole closed"))


def _bridge_end(cage, sel):
    """One end of a Bridge: a face (it will be removed, its border becomes the
    opening) or an edge of an opening that already exists."""
    if sel and sel[0] == "f":
        face = tuple(cage.faces[sel[1]])
        return ("face", sel[1], face, list(reversed(face)))
    return ("loop", None, None, _open_loop(cage, sel))


def _bridge(cage, sel, value, axis, pending):
    end = _bridge_end(cage, sel)
    if pending is None:
        what = _T("face") if end[0] == "face" else _T("opening")
        return Result(sel, _T('Now select the other {what} (a face or an edge of an opening) and press Apply again', what=what), pending=("bridge", end))
    first = pending[1]
    if first[0] == "face" and end[0] == "face" and first[1] == end[1]:
        raise ValueError(_T("Pick a different face"))
    if first[0] == "loop" and end[0] == "loop" and set(first[3]) == set(end[3]):
        raise ValueError(_T("Pick an edge of a different opening"))
    if len(first[3]) != len(end[3]):
        raise ValueError(_T('Both ends need the same number of sides ({v0} and {v1})', v0=len(first[3]), v1=len(end[3])))
    if set(first[3]) & set(end[3]):
        raise ValueError(_T("The two ends touch each other: pick faces that do not share a point"))
    drop = [e[1] for e in (first, end) if e[0] == "face"]
    for e in (first, end):
        if e[0] == "face" and tuple(cage.faces[e[1]]) != e[2]:
            raise ValueError(_T("The cage changed since the first click: start the Bridge again"))
    if len(drop) >= len(cage.faces):
        raise ValueError(_T("A cage needs at least one face"))
    cage.remove_faces(drop)
    cage.bridge(first[3], end[3], twist=int(round(value)))
    return Result(None, _T("Bridged") if drop else _T("Openings bridged"))


def bridge_two(cage, first, second, value=0.0) -> Result:
    """Bridge two selected ends (faces, or edges of openings) in one go: the
    same work as two Apply clicks, with both ends already chosen."""
    started = _bridge(cage, first, value, "auto", None)
    return _bridge(cage, second, value, "auto", started.pending)


def _shell(cage, sel, value, axis, pending):
    mode = axis if axis in ("inside", "outside", "center") else "outside"
    cage.shell(value, mode)
    return Result(None, _T('Wall added ({mode}). Smooth it, or use Finish', mode=_T(mode)))


def _revolve(cage, sel, value, axis, pending):
    _need(sel, "f", _T("a face (the profile)"))
    n = modeling.revolve(cage, sel[1], "z" if axis == "auto" else axis, int(round(value)))
    return Result(None, _T('Revolved: {n} faces added', n=n))


def _bevel(cage, sel, value, axis, pending):
    _need(sel, "e", _T("an edge"))
    n = len(modeling.bevel(cage, [(sel[1], sel[2])], value))
    return Result(None, _T('Bevelled: {n} faces added', n=n))


def bevel_items(cage, sels, value, axis="auto") -> Result:
    """Bevel every selected edge (a loop picked with repeated clicks)."""
    edges = [(x[1], x[2]) for x in sels if x and x[0] == "e"]
    if not edges:
        raise ValueError(_T("Select edges to bevel"))
    n = len(modeling.bevel(cage, edges, value))
    return Result(None, _T('Bevelled: {n} faces added', n=n))


def _sections(cage, sels):
    """The closed sections picked: each selected face, and each closed loop
    of selected edges."""
    out, faces = [], []
    for x in sels:
        if x and x[0] == "f":
            out.append(list(cage.faces[x[1]]))
            faces.append(x[1])
    edges = [(x[1], x[2]) for x in sels if x and x[0] == "e"]
    if edges:
        left = [ekey(a, b) for a, b in edges]
        while left:
            comp = [left.pop()]
            grew = True
            while grew:
                grew = False
                verts = {v for e in comp for v in e}
                for e in list(left):
                    if e[0] in verts or e[1] in verts:
                        comp.append(e)
                        left.remove(e)
                        grew = True
            try:
                pts, closed = modeling.chain_from_edges(comp)
            except ValueError:
                pts, closed = [], False
            if not closed:
                raise ValueError(_T("An edge section must be a closed loop"))
            out.append(pts)
            faces.append(None)
    return out, faces


def loft_items(cage, sels, value, axis="closed") -> Result:
    sections, faces = _sections(cage, sels)
    if len(sections) < 2:
        raise ValueError(_T("Loft: select two or more faces (click one, Shift+click the others)"))
    sections, faces = _order_both(cage, sections, faces)
    n = modeling.loft(cage, sections, int(round(value)), closed_ends=axis != "open", faces=faces)
    return Result(None, _T('Lofted through {k} sections: {n} faces added', k=len(sections), n=n))


def sweep_items(cage, sels, value, axis="closed") -> Result:
    faces = [x for x in sels if x and x[0] == "f"]
    edges = [(x[1], x[2]) for x in sels if x and x[0] == "e"]
    if len(faces) != 1 or not edges:
        raise ValueError(_T("Sweep: select one face (the profile), then Shift+click the edges of the path"))
    path, closed = modeling.chain_from_edges(edges)
    prof = list(cage.faces[faces[0][1]])
    if set(prof) & set(path) and not closed:
        # the profile shares a point with the path: start the path there
        pass
    n = modeling.sweep(cage, prof, path, closed, closed_ends=axis != "open", twist_deg=value,
                       face=faces[0][1])
    return Result(None, _T('Swept along {k} points: {n} faces added', k=len(path), n=n))


# ---- plain drawing as input (faces and lines drawn outside any SubD group) -------------------
def _weld_points(cage: Cage, pts, tol: float = 1e-6) -> list[int]:
    """Cage point numbers for ``pts`` (new ones are added; a point already
    there within ``tol`` is reused)."""
    out = []
    for p in pts:
        for i, q in enumerate(cage.verts):
            if abs(q[0] - p[0]) <= tol and abs(q[1] - p[1]) <= tol and abs(q[2] - p[2]) <= tol:
                out.append(i)
                break
        else:
            out.append(cage._new_vert(p))
    return out


def _section_order(cage: Cage, sections) -> list[int]:
    """The order the sections lie along the piece: from one end, always to the
    nearest one left (a selection has no click order to follow)."""
    n = len(sections)
    if n < 3:
        return list(range(n))
    cen = []
    for sec in sections:
        pts = [cage.verts[v] for v in sec]
        cen.append(tuple(sum(p[k] for p in pts) / len(pts) for k in range(3)))
    mid = tuple(sum(c[k] for c in cen) / n for k in range(3))
    left = list(range(n))
    cur = max(left, key=lambda i: math.dist(cen[i], mid))
    order = [cur]
    left.remove(cur)
    while left:
        cur = min(left, key=lambda i: math.dist(cen[i], cen[order[-1]]))
        order.append(cur)
        left.remove(cur)
    return order


def _order_both(cage: Cage, sections, faces):
    """Sections (and their cage faces) in the order they lie along the piece."""
    idx = _section_order(cage, sections)
    return [sections[i] for i in idx], [faces[i] for i in idx]


def loft_loose(cage: Cage, sels, loops, value, axis="closed") -> Result:
    """Loft through the selected cage faces and plain faces (``loops`` of xyz)."""
    fidx = [x[1] for x in sels if x and x[0] == "f"]
    sections = [list(cage.faces[f]) for f in fidx]
    faces = list(fidx)
    sections += [_weld_points(cage, lp) for lp in loops]
    faces += [None] * len(loops)
    if len(sections) < 2:
        raise ValueError(_T("Loft: select two or more faces (click one, Shift+click the others)"))
    sections, faces = _order_both(cage, sections, faces)
    n = modeling.loft(cage, sections, int(round(value)), closed_ends=axis != "open", faces=faces)
    cage.prune()
    return Result(None, _T('Lofted through {k} sections: {n} faces added', k=len(sections), n=n))


def sweep_loose(cage: Cage, sels, loops, segments, value, axis="closed") -> Result:
    """Sweep a profile (a cage face or a plain face) along a path (cage edges or
    plain lines, ``segments`` of two xyz points)."""
    faces = [x for x in sels if x and x[0] == "f"]
    edges = [(x[1], x[2]) for x in sels if x and x[0] == "e"]
    if segments:
        edges = [tuple(_weld_points(cage, seg)) for seg in segments]
    face = faces[0][1] if faces else None
    if faces:
        prof = list(cage.faces[faces[0][1]])
    elif len(loops) == 1:
        prof = _weld_points(cage, loops[0])
    else:
        prof = None
    if prof is None or not edges:
        raise ValueError(_T("Sweep: select one face (the profile), then Shift+click the edges of the path"))
    path, closed = modeling.chain_from_edges(edges)
    n = modeling.sweep(cage, prof, path, closed, closed_ends=axis != "open", twist_deg=value,
                       face=face)
    cage.prune()
    return Result(None, _T('Swept along {k} points: {n} faces added', k=len(path), n=n))


def revolve_loose(cage: Cage, sels, loops, segments_xyz, value, axis) -> Result:
    """Revolve a plain face, or a plain line chain, round the X, Y or Z axis."""
    n_seg = int(round(value))
    axis = "z" if axis == "auto" else axis                  # Auto turns round the vertical axis
    faces = [x for x in sels if x and x[0] == "f"]
    if faces:
        n = modeling.revolve(cage, faces[0][1], axis, n_seg)
    elif loops:
        prof = _weld_points(cage, loops[0])
        n = modeling.revolve(cage, 0, axis, n_seg, profile=prof, closed=True)
    elif segments_xyz:
        edges = [tuple(_weld_points(cage, sg)) for sg in segments_xyz]
        path, closed = modeling.chain_from_edges(edges)
        n = modeling.revolve(cage, 0, axis, n_seg, profile=path, closed=closed)
    else:
        raise ValueError(_T("a face (the profile)"))
    cage.prune()
    return Result(None, _T('Revolved: {n} faces added', n=n))


def _loft(cage, sel, value, axis, pending):
    raise ValueError(_T("Loft: select two or more faces (click one, Shift+click the others)"))


def _sweep(cage, sel, value, axis, pending):
    raise ValueError(_T("Sweep: select one face (the profile), then Shift+click the edges of the path"))


def _slice(cage, sel, value, axis, pending):
    if axis not in ("x", "y", "z"):
        raise ValueError(_T("Choose X, Y or Z: the plane is perpendicular to that axis"))
    n = {"x": (1.0, 0.0, 0.0), "y": (0.0, 1.0, 0.0), "z": (0.0, 0.0, 1.0)}[axis]
    if sel:
        pts = [cage.verts[v] for v in vertex_set(cage, sel)]
    else:
        lo, hi = cage.bounds()
        pts = [lo, hi]
    c = tuple(sum(p[k] for p in pts) / len(pts) for k in range(3))
    point = tuple(c[k] + n[k] * value for k in range(3))
    new = modeling.slice_plane(cage, point, n)
    if not new:
        raise ValueError(_T("The plane does not cut the cage"))
    a, b = new[0]
    return Result(("e", a, b), _T('Sliced: {n} edges in the cut', n=len(new)))


def _merge(cage, sel, value, axis, pending):
    _need(sel, "vef", _T("a point, an edge or a face"))
    if sel[0] == "e":
        v = modeling.collapse_edge(cage, sel[1], sel[2])
        return Result(("v", v), _T("Edge merged at its middle"))
    if sel[0] == "f":
        v = modeling.collapse_face(cage, sel[1])
        return Result(("v", v), _T("Face merged into one point"))
    n = modeling.weld(cage, sel[1], value)
    return Result(None, _T('{n} points merged', n=n))


def _dissolve(cage, sel, value, axis, pending):
    _need(sel, "ve", _T("an edge or a point"))
    if sel[0] == "e":
        modeling.dissolve_edge(cage, sel[1], sel[2])
        return Result(None, _T("Edge dissolved"))
    modeling.dissolve_vertex(cage, sel[1])
    return Result(None, _T("Point dissolved"))


def _slide(cage, sel, value, axis, pending):
    _need(sel, "e", _T("an edge"))
    loop = edge_loop(cage, sel[1], sel[2])
    n = modeling.slide_loop(cage, loop, value)
    return Result(sel, _T('Loop slid: {n} points', n=n))


def slide_items(cage, sels, value, axis="auto") -> Result:
    edges = [(x[1], x[2]) for x in sels if x and x[0] == "e"]
    if not edges:
        raise ValueError(_T("Select the edges of a loop to slide"))
    n = modeling.slide_loop(cage, edges, value)
    return Result(sels[-1], _T('Loop slid: {n} points', n=n))


_TOOLS: dict[str, Callable] = {
    "edit": _edit, "crease": _crease, "grow_face": _grow_face,
    "grow_edge": _grow_edge, "stretch": _stretch, "inset_face": _inset_face,
    "offset_edge": _offset_edge, "squeeze": _squeeze, "divide": _divide,
    "delete_face": _delete_face, "close": _close, "bridge": _bridge,
    "shell": _shell, "revolve": _revolve, "bevel": _bevel, "loft": _loft, "sweep": _sweep,
    "slice": _slice, "merge": _merge, "dissolve": _dissolve, "slide": _slide,
}


def apply_tool(cage: Cage, tool: str, sel: Selection | None, value: float = 0.0,
               axis: str = "auto", pending=None, sym: dict | None = None,
               soft: float = 0.0) -> Result:
    """Run ``tool`` on ``cage`` in place. ``axis`` is "auto", "x", "y" or "z".
    With ``sym`` (``{"on": True, "point": ..., "normal": ...}``) the work is
    mirrored across that plane. Raises ValueError (status-bar wording) when
    the selection does not fit; the cage is only touched once the selection
    has been checked."""
    if tool not in _TOOLS:
        raise ValueError(_T('Unknown tool {tool}', tool=repr(tool)))
    if sel and not valid(cage, sel):
        raise ValueError(_T("The selection no longer exists"))
    if tool == "edit" and soft > 0:                    # proportional move
        _need(sel, "vef", _T("a point, edge or face"))
        d = _axis(cage, sel, axis)
        symmetric_move(cage, vertex_set(cage, sel), (d[0] * value, d[1] * value, d[2] * value),
                       sym, soft)
        return Result(sel, "Moved")
    if sym and sym.get("on") and tool not in _NO_SYMMETRY:
        return _symmetric(cage, tool, sel, value, axis, pending, sym)
    return _TOOLS[tool](cage, sel, value, axis, pending)


# ---- tiny vector helpers --------------------------------------------------------------------
def _sub(a, b):
    return (a[0] - b[0], a[1] - b[1], a[2] - b[2])


def _mul(a, s):
    return (a[0] * s, a[1] * s, a[2] * s)


def _dot(a, b):
    return a[0] * b[0] + a[1] * b[1] + a[2] * b[2]


def _cross_(a, b):
    return (a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0])


def _unit_sub(b, a):
    d = _sub(b, a)
    n = math.sqrt(_dot(d, d)) or 1.0
    return _mul(d, 1.0 / n)


# ---- picking on screen ---------------------------------------------------------------------
def pick(cage: Cage, xs: Sequence[float], ys: Sequence[float], front: Sequence[bool],
         px: float, py: float, tol: float = 9.0, ray=None, skip=()) -> Selection | None:
    """The cage element under pixel (px, py), given each vertex's projected
    position. Points win over edges, edges over faces; ``None`` for a miss.
    With the mouse ``ray`` (origin, direction) the face nearest the viewer wins
    when several overlap on screen; without it, the one whose centre is closest.
    Faces listed in ``skip`` are ignored, which reaches the face behind one
    that is already selected."""
    best, best_d = None, tol
    for i in range(len(cage.verts)):
        if front[i]:
            d = math.hypot(xs[i] - px, ys[i] - py)
            if d <= best_d:
                best, best_d = ("v", i), d
    if best:
        return best
    best_d = tol * 0.7
    for a, b in cage.edge_faces():
        if not (front[a] and front[b]):
            continue
        d = _seg_dist(px, py, xs[a], ys[a], xs[b], ys[b])
        if d <= best_d:
            best, best_d = ("e", a, b), d
    if best:
        return best
    best_d = None
    for fi, f in enumerate(cage.faces):
        if not all(front[v] for v in f) or ("f", fi) in skip:
            continue
        poly = [(xs[v], ys[v]) for v in f]
        if _inside(px, py, poly):
            cx = sum(p[0] for p in poly) / len(poly)
            cy = sum(p[1] for p in poly) / len(poly)
            d = math.hypot(cx - px, cy - py)
            if ray is not None:
                t = _ray_face_distance(cage, fi, ray)
                if t is not None:
                    d = t - 1e9                 # any real hit beats a miss; nearer wins
            if best_d is None or d < best_d:
                best, best_d = ("f", fi), d
    return best


# ---- picking on the smooth skin -----------------------------------------------------------
class Skin(NamedTuple):
    """The smooth surface of a cage, with what is needed to point at the cage
    through it: every skin face knows its cage face, and every cage edge knows
    the chain of skin points that makes its curve on the skin."""
    verts: np.ndarray                       # (N, 3) skin points; cage point i is skin point i
    tris: np.ndarray                        # (T, 3) skin triangles
    tri_face: np.ndarray                    # (T,) cage face of each triangle
    curves: dict                            # cage edge (a, b) -> list of skin point indices


def build_skin(cage: Cage, levels: int) -> Skin:
    """Smooth ``cage`` ``levels`` times, keeping the cage-to-skin lineage."""
    v = list(cage.verts)
    f = [tuple(x) for x in cage.faces]
    c = {k: s for k, s in cage.creases.items() if s > 0}
    vc = {k: s for k, s in cage.vcreases.items() if s > 0}
    src = list(range(len(f)))
    curves = {e: [e[0], e[1]] for e in cage.edge_faces()}
    for _ in range(max(0, int(levels))):
        v, f, c, eidx, parents, vc = _subdivide_step(v, f, c, vc)
        src = [src[p] for p in parents]
        for e, chain in curves.items():
            out = [chain[0]]
            for p, q in zip(chain, chain[1:]):
                out.append(eidx[(p, q) if p < q else (q, p)])
                out.append(q)
            curves[e] = out
    tris, owner = [], []
    for fi, face in enumerate(f):
        for k in range(1, len(face) - 1):
            tris.append((face[0], face[k], face[k + 1]))
            owner.append(src[fi])
    return Skin(np.array(v, dtype=float).reshape(-1, 3), np.array(tris, dtype=np.int64).reshape(-1, 3),
                np.array(owner, dtype=np.int64), curves)


def skin_hit(skin: Skin, ray, skip=()) -> int | None:
    """The cage face behind the skin point under the mouse ray (origin,
    direction): the nearest skin triangle the ray crosses, any side. Cage faces
    in ``skip`` are ignored, which reaches the surface behind one already picked."""
    if len(skin.tris) == 0:
        return None
    o = np.asarray(ray[0], dtype=float)
    d = np.asarray(ray[1], dtype=float)
    a = skin.verts[skin.tris[:, 0]]
    e1 = skin.verts[skin.tris[:, 1]] - a
    e2 = skin.verts[skin.tris[:, 2]] - a
    p = np.cross(d, e2)
    det = np.einsum("ij,ij->i", e1, p)
    ok = np.abs(det) > 1e-14
    inv = np.where(ok, 1.0 / np.where(ok, det, 1.0), 0.0)
    tv = o - a
    u = np.einsum("ij,ij->i", tv, p) * inv
    q = np.cross(tv, e1)
    w = (q @ d) * inv
    t = np.einsum("ij,ij->i", e2, q) * inv
    hit = ok & (u >= -1e-9) & (w >= -1e-9) & (u + w <= 1 + 1e-9) & (t > 0)
    if skip:
        hit &= ~np.isin(skin.tri_face, [x[1] for x in skip if x[0] == "f"])
    if not hit.any():
        return None
    t = np.where(hit, t, np.inf)
    return int(skin.tri_face[int(np.argmin(t))])


def pick_skin(cage: Cage, skin: Skin, xs, ys, front, px: float, py: float, ray,
              tol: float = 9.0, skip=()) -> Selection | None:
    """Select a cage element by clicking on the smooth surface. ``xs, ys,
    front`` are the screen positions of the skin points. The cage face behind
    the click is found first; then, among that face's own points and edges as
    they lie on the skin, a point within ``tol`` pixels wins, then an edge
    curve, otherwise the face. ``None`` when the click misses the skin."""
    fi = skin_hit(skin, ray, skip) if ray is not None else None
    if fi is None:
        return None
    face = cage.faces[fi]
    near = {fi}                                    # this face and the ones across its edges
    ef = cage.edge_faces()
    for i, a in enumerate(face):
        b = face[(i + 1) % len(face)]
        near.update(ef.get(ekey(a, b), ()))
    # How close is "on" a point or an edge depends on how big the face looks: on a
    # small face the zones shrink, so a click inside it still means the face.
    lens = [math.hypot(xs[face[i]] - xs[face[(i + 1) % len(face)]],
                       ys[face[i]] - ys[face[(i + 1) % len(face)]]) for i in range(len(face))]
    size = min(lens) if lens else tol
    tol_v = min(tol * 1.35, max(6.0, 0.3 * size))        # easy to grab, still near the cursor
    tol_e = min(tol * 0.85, max(3.5, 0.2 * size))
    best, best_score = None, 1.0
    for fj in near:
        for v in cage.faces[fj]:
            if front[v]:
                score = (0.9 if fj != fi else 0.85) * math.hypot(xs[v] - px, ys[v] - py) / tol_v
                if score < best_score:
                    best, best_score = ("v", v), score
    for fj in near:
        g = cage.faces[fj]
        for i, a in enumerate(g):
            b = g[(i + 1) % len(g)]
            chain = skin.curves.get(ekey(a, b))
            if not chain:
                continue
            for p, q in zip(chain, chain[1:]):
                score = (1.0 if fj != fi else 0.95) * _seg_dist(px, py, xs[p], ys[p], xs[q], ys[q]) / tol_e
                if score < best_score:
                    best, best_score = ("e",) + ekey(a, b), score
    return best or ("f", fi)


def edge_loop(cage: Cage, a: int, b: int) -> list[tuple[int, int]]:
    """The contour an edge belongs to, as a list of ``(a, b)`` edges (the edge
    itself first). On a border it is the whole border loop; inside the surface
    it is the edge loop that runs straight through every four-way point, and
    stops at any other kind of point. An edge with nothing to follow gives
    just itself."""
    ef = cage.edge_faces()
    if ekey(a, b) not in ef:
        raise ValueError(_T("That is not an edge of the cage"))
    nbr: dict[int, list[int]] = {}
    for (x, y) in ef:
        nbr.setdefault(x, []).append(y)
        nbr.setdefault(y, []).append(x)
    border = len(ef[ekey(a, b)]) == 1

    def step(prev: int, v: int):
        """The edge that carries on from ``prev -> v``, or None."""
        around = nbr[v]
        if border:
            nxt = [w for w in around if w != prev and len(ef[ekey(v, w)]) == 1]
            return nxt[0] if len(nxt) == 1 else None
        if len(around) != 4 or any(len(ef[ekey(v, w)]) != 2 for w in around):
            return None
        touching = set(ef[ekey(prev, v)])
        opp = [w for w in around if w != prev and not (set(ef[ekey(v, w)]) & touching)]
        return opp[0] if len(opp) == 1 else None

    loop = [(a, b)]
    seen = {ekey(a, b)}
    for start, tip in ((a, b), (b, a)):               # walk both ways from the edge
        prev, v = start, tip
        out = []
        while True:
            w = step(prev, v)
            if w is None or ekey(v, w) in seen:
                break
            seen.add(ekey(v, w))
            out.append((v, w))
            prev, v = v, w
        if start == a:
            loop += out
        else:
            loop = [(y, x) for (x, y) in reversed(out)] + loop
    return loop


def edge_contours(cage: Cage, a: int, b: int) -> list[tuple[str, list[tuple[int, int]]]]:
    """What repeated clicks on an edge step through: ``[(label, edges), ...]``.
    The edge alone, then its loop (when that is longer than the edge), then the
    outline of each face it touches. Lists that would repeat are left out."""
    ef = cage.edge_faces()
    key = ekey(a, b)
    if key not in ef:
        raise ValueError(_T("That is not an edge of the cage"))
    out: list[tuple[str, list[tuple[int, int]]]] = [("Edge", [(a, b)])]
    seen = [{key}]

    def add(label, edges):
        ks = {ekey(x, y) for x, y in edges}
        if ks not in seen:
            seen.append(ks)
            out.append((label, edges))

    loop = edge_loop(cage, a, b)
    if len(loop) > 1:
        add(_T("Loop"), loop)
    try:
        ring_edges, _rf, _closed = cage.edge_ring(a, b)
    except ValueError:
        ring_edges = []
    if len(ring_edges) > 1:
        add(_T("Ring"), [tuple(e) for e in ring_edges])
    for fi in ef[key]:
        f = cage.faces[fi]
        ring = [(f[i], f[(i + 1) % len(f)]) for i in range(len(f))]
        add(_T("Face outline"), ring)
    return out


def _ray_face_distance(cage: Cage, fi: int, ray) -> float | None:
    """How far along the mouse ray it meets the plane of face ``fi`` (None
    when the ray runs along the face or it lies behind the viewer)."""
    origin, direction = ray
    n = cage.face_normal(fi)
    den = _dot(direction, n)
    if abs(den) < 1e-9:
        return None
    t = _dot(_sub(cage.face_centroid(fi), origin), n) / den
    return t if t > 0 else None


def _seg_dist(px, py, ax, ay, bx, by) -> float:
    dx, dy = bx - ax, by - ay
    L = dx * dx + dy * dy
    t = 0.0 if L == 0 else max(0.0, min(1.0, ((px - ax) * dx + (py - ay) * dy) / L))
    return math.hypot(px - (ax + t * dx), py - (ay + t * dy))


def _inside(px, py, poly) -> bool:
    inside = False
    n = len(poly)
    for i in range(n):
        x0, y0 = poly[i]
        x1, y1 = poly[(i + 1) % n]
        if (y0 > py) != (y1 > py) and px < (x1 - x0) * (py - y0) / (y1 - y0) + x0:
            inside = not inside
    return inside


# ---- dragging ----------------------------------------------------------------------------
def closest_on_axis(ray_origin, ray_dir, point, axis) -> float | None:
    """Where along the line ``point + s * axis`` does the mouse ray pass
    nearest? Returns ``s`` (metres), or None when the ray runs parallel to the
    axis and gives no usable answer."""
    n = math.sqrt(_dot(axis, axis)) or 1.0
    a = _mul(axis, 1.0 / n)
    m = math.sqrt(_dot(ray_dir, ray_dir)) or 1.0
    d = _mul(ray_dir, 1.0 / m)
    w0 = _sub(point, ray_origin)
    b, dd, e = _dot(a, d), _dot(a, w0), _dot(d, w0)
    den = 1.0 - b * b
    if den < 1e-6:
        return None
    return (b * e - dd) / den


# ---- mirror symmetry -------------------------------------------------------------------------
_NO_SYMMETRY = ("bridge", "delete_face", "shell", "revolve", "bevel", "loft", "sweep",
                "slice", "merge", "dissolve", "slide")          # bridge needs two clicks; delete is exact
_MOVES = ("edit", "stretch", "squeeze")           # moves points: partners are re-synced
_LOOPS = ("offset_edge", "close")                 # act on a whole border


def reflect_point(p, point, normal):
    d = 2.0 * _dot(_sub(p, point), normal)
    return (p[0] - d * normal[0], p[1] - d * normal[1], p[2] - d * normal[2])


def reflect_vector(v, normal):
    d = 2.0 * _dot(v, normal)
    return (v[0] - d * normal[0], v[1] - d * normal[1], v[2] - d * normal[2])


def _plane(sym: dict):
    n = sym["normal"]
    ln = math.sqrt(_dot(n, n)) or 1.0
    return tuple(sym["point"]), (n[0] / ln, n[1] / ln, n[2] / ln)


def mirror_partners(cage: Cage, sym: dict, tol: float | None = None) -> dict[int, int]:
    """For each point of the cage, the point sitting at its mirror image
    (itself when it lies on the plane). Points without a partner are absent."""
    point, normal = _plane(sym)
    if tol is None:
        lo, hi = cage.bounds()
        tol = 1e-5 * (math.dist(lo, hi) or 1.0) + 1e-9
    grid: dict[tuple, list[int]] = {}
    for i, p in enumerate(cage.verts):
        grid.setdefault(tuple(round(c / tol) for c in p), []).append(i)
    out: dict[int, int] = {}
    for i, p in enumerate(cage.verts):
        q = reflect_point(p, point, normal)
        cell = tuple(round(c / tol) for c in q)
        best = None
        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                for dz in (-1, 0, 1):
                    for j in grid.get((cell[0] + dx, cell[1] + dy, cell[2] + dz), ()):
                        if math.dist(cage.verts[j], q) <= tol * 2:
                            best = j if best is None else best
        if best is not None:
            out[i] = best
    return out


def mirror_selection(cage: Cage, sel, partners: dict[int, int]):
    """The selection's mirror image, or None when the cage has no such element."""
    if not sel:
        return None
    if sel[0] == "v":
        return ("v", partners[sel[1]]) if sel[1] in partners else None
    if sel[0] == "e":
        a, b = partners.get(sel[1]), partners.get(sel[2])
        if a is None or b is None or a == b or ekey(a, b) not in cage.edge_faces():
            return None
        return ("e", a, b)
    ids = [partners.get(v) for v in cage.faces[sel[1]]]
    if None in ids:
        return None
    want = frozenset(ids)
    for fi, f in enumerate(cage.faces):
        if frozenset(f) == want:
            return ("f", fi)
    return None


def sync_moves(cage: Cage, sym: dict, moved, partners: dict[int, int]) -> None:
    """After points moved, put their partners at the mirror image (points on
    the plane are kept on it; a pair that both moved meets halfway)."""
    point, normal = _plane(sym)
    moved = set(moved)
    done: set[int] = set()
    for v in moved:
        w = partners.get(v)
        if w is None or v in done:
            continue
        p = cage.verts[v]
        if w == v:                                    # on the plane: stay on it
            d = _dot(_sub(p, point), normal)
            cage.verts[v] = (p[0] - d * normal[0], p[1] - d * normal[1], p[2] - d * normal[2])
        elif w in moved:                              # both moved: meet in the middle
            q = reflect_point(cage.verts[w], point, normal)
            m = ((p[0] + q[0]) / 2, (p[1] + q[1]) / 2, (p[2] + q[2]) / 2)
            cage.verts[v] = m
            cage.verts[w] = reflect_point(m, point, normal)
            done.update((v, w))
        else:
            cage.verts[w] = reflect_point(p, point, normal)
            done.add(w)


def soft_weights(cage: Cage, vset, radius: float) -> dict[int, float]:
    """Proportional ("soft") selection: every point within ``radius`` of the
    selected ones gets a weight that falls smoothly from 1 (selected) to 0 at
    the radius, so a move drags the surface around it along, tapering off."""
    ids = list(dict.fromkeys(vset))
    if radius <= 0 or not ids:
        return {}
    chosen = set(ids)
    out: dict[int, float] = {}
    cell = radius
    grid: dict[tuple, list[int]] = {}
    for v in ids:
        p = cage.verts[v]
        grid.setdefault((int(p[0] // cell), int(p[1] // cell), int(p[2] // cell)), []).append(v)
    for i, q in enumerate(cage.verts):
        if i in chosen:
            continue
        cx, cy, cz = int(q[0] // cell), int(q[1] // cell), int(q[2] // cell)
        best = None
        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                for dz in (-1, 0, 1):
                    for v in grid.get((cx + dx, cy + dy, cz + dz), ()):
                        d = math.dist(cage.verts[v], q)
                        if best is None or d < best:
                            best = d
        if best is not None and best < radius:
            t = best / radius
            out[i] = 1.0 - t * t * (3.0 - 2.0 * t)           # smoothstep falloff
    return out


def symmetric_move(cage: Cage, vset, delta, sym: dict | None, soft: float = 0.0) -> None:
    """Move points by ``delta``; with an active symmetry the mirrored points
    follow, so a drag on one side reshapes both. With ``soft`` (a radius) the
    points around the selection follow too, by a smoothly fading share."""
    vset = list(dict.fromkeys(vset))
    partners = mirror_partners(cage, sym) if sym and sym.get("on") else {}
    cage.move(vset, delta)
    moved = list(vset)
    if soft > 0:
        for v, w in soft_weights(cage, vset, soft).items():
            cage.move([v], (delta[0] * w, delta[1] * w, delta[2] * w))
            moved.append(v)
    if partners:
        sync_moves(cage, sym, moved, partners)


def symmetric_rotate(cage: Cage, vset, pivot, axis, angle: float, sym: dict | None) -> None:
    """Turn points by ``angle`` about ``axis`` through ``pivot``; with an active
    symmetry the mirrored points follow."""
    vset = list(dict.fromkeys(vset))
    partners = mirror_partners(cage, sym) if sym and sym.get("on") else {}
    cage.rotate(vset, pivot, axis, angle)
    if partners:
        sync_moves(cage, sym, vset, partners)


def plane_basis(axis):
    """Two unit vectors ``u, v`` spanning the plane perpendicular to ``axis``
    (``u x v`` points along ``axis``): the fixed frame the protractor uses."""
    n = math.sqrt(_dot(axis, axis)) or 1.0
    a = _mul(axis, 1.0 / n)
    helper = (1.0, 0.0, 0.0) if abs(a[0]) < 0.9 else (0.0, 1.0, 0.0)
    u = _cross_(helper, a)
    un = math.sqrt(_dot(u, u))
    u = _mul(u, 1.0 / un)
    return u, _cross_(a, u)


def angle_in_plane(ray_origin, ray_dir, pivot, axis, ref=None):
    """Angle (radians) of the mouse ray's hit on the plane through ``pivot``
    perpendicular to ``axis``, measured around ``axis`` from a fixed reference
    direction. None when the ray runs parallel to the plane. The reference is
    the same for every call with the same axis, so differences between two
    calls are the angle the pointer swept."""
    n = math.sqrt(_dot(axis, axis)) or 1.0
    a = _mul(axis, 1.0 / n)
    den = _dot(ray_dir, a)
    if abs(den) < 1e-9:
        return None
    t = _dot(_sub(pivot, ray_origin), a) / den
    hit = (ray_origin[0] + ray_dir[0] * t, ray_origin[1] + ray_dir[1] * t,
           ray_origin[2] + ray_dir[2] * t)
    r = _sub(hit, pivot)
    u, v = plane_basis(axis)
    return math.atan2(_dot(r, v), _dot(r, u))


def _symmetric(cage, tool, sel, value, axis, pending, sym):
    partners = mirror_partners(cage, sym)
    if tool in _MOVES:
        vset = vertex_set(cage, sel) if sel else []
        res = _TOOLS[tool](cage, sel, value, axis, pending)
        sync_moves(cage, sym, vset, partners)
        return res
    msel = mirror_selection(cage, sel, partners)
    skip = msel is None or msel == sel
    if not skip and tool in _LOOPS:                  # both clicks on one border: once
        try:
            skip = set(_open_loop(cage, sel)) == set(_open_loop(cage, msel))
        except ValueError:
            skip = True
    before = cage.faces[msel[1]] if (not skip and tool == "divide" and msel[0] == "f"
                                      and axis != "face") else None
    res = _TOOLS[tool](cage, sel, value, axis, pending)
    if before is not None and cage.faces[msel[1]] != before:
        skip = True                                  # the loop cut already went through it
    if not skip:
        try:
            _TOOLS[tool](cage, msel, value, axis, pending)
        except ValueError:                           # already done by the first pass
            pass
    return res
