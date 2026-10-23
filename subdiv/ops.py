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

import math
from typing import Callable, NamedTuple, Sequence

from .edit import Cage, ekey

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
             "With nothing selected it applies to every edge; with several selected "
             "(Shift+click, or click an edge again for its contour) to all their edges. "
             "The value starts at the smoothing level, which keeps the edge crisp; "
             "a smaller one leaves a small radius.",
             "Sharpness", 2.0, 0.0, 6.0, 1.0, False),
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
        return "Nothing selected"
    return {"v": lambda: f"Point {sel[1]}", "e": lambda: f"Edge {sel[1]}-{sel[2]}",
            "f": lambda: f"Face {sel[1]}"}[sel[0]]()


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
    return f"{len(sels)} items selected (Shift+click adds or removes one)"


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
        raise ValueError(f"Select {what} first")
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
    _need(sel, "e", "an open edge")
    a, b = sel[1], sel[2]
    for loop in cage.boundary_loops():
        n = len(loop)
        if any({loop[i], loop[(i + 1) % n]} == {a, b} for i in range(n)):
            return loop
    raise ValueError("That edge is not on an open border")


# ---- the tools ----------------------------------------------------------------------------
def _edit(cage, sel, value, axis, pending):
    _need(sel, "vef", "a point, edge or face")
    d = _axis(cage, sel, axis)
    cage.move(vertex_set(cage, sel), (d[0] * value, d[1] * value, d[2] * value))
    return Result(sel, "Moved")


def _crease(cage, sel, value, axis, pending):
    if not sel:                                    # nothing selected: every edge
        cage.set_crease(cage.edges(), value)
        return Result(None, "All creases cleared" if value <= 0
                      else f"Every edge creased {value:g}")
    _need(sel, "ef", "an edge or a face")
    if sel[0] == "e":
        edges = [(sel[1], sel[2])]
    else:
        f = cage.faces[sel[1]]
        edges = [(f[i], f[(i + 1) % len(f)]) for i in range(len(f))]
    cage.set_crease(edges, value)
    return Result(sel, "Crease cleared" if value <= 0 else f"Crease {value:g}")


def crease_items(cage: Cage, sels, value: float) -> Result:
    """Crease (or, with 0, round off) every edge of several selected items at
    once: edges as picked, faces by their outline. Points alone have no edge."""
    edges: list[tuple[int, int]] = []
    seen = set()
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
    if not edges:
        raise ValueError("Select edges or faces first")
    cage.set_crease(edges, value)
    n = len(edges)
    return Result(None, f"{n} edge{'s' if n > 1 else ''} rounded off" if value <= 0
                  else f"{n} edge{'s' if n > 1 else ''} creased {value:g}")


def _grow_face(cage, sel, value, axis, pending):
    _need(sel, "f", "a face")
    cage.extrude_face(sel[1], value)
    return Result(sel, "Face grown")


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
        where = f"along {axis.upper()}"
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
            raise ValueError("Cannot tell which way is outward for that contour: "
                             "choose X, Y or Z")
        c = tuple(sum(p[k] for p in pts) / len(pts) for k in range(3))
        mid = tuple(sum(p[k] for p in cage.verts) / len(cage.verts) for k in range(3))
        d = (nx / n, ny / n, nz / n)
        if _dot(d, _sub(c, mid)) < 0:           # point away from the piece, not into it
            d = _mul(d, -1.0)
        where = "outwards"
    new = cage.extrude_edges(list(loop) + [loop[0]], _mul(d, value))
    return Result(("e", new[0], new[1]), f"Open contour of {len(loop)} edges extruded {where}")


def _grow_edge(cage, sel, value, axis, pending):
    loop = _open_loop(cage, sel)
    if axis in ("x", "y", "z"):                      # the whole open contour, along that axis
        return _grow_loop(cage, loop, value, axis)
    a, b = sel[1], sel[2]
    d = _outward(cage, a, b)
    if d is None:
        raise ValueError("Cannot tell which way is outward for that edge")
    new = cage.extrude_edges([a, b], _mul(d, value))
    return Result(("e", new[0], new[1]), "Edge grown")


def grow_items(cage, sels, value, axis="auto") -> Result:
    """Grow E with several edges selected (a contour picked with repeated clicks):
    they must be all the edges of one open contour; it is extruded as a whole."""
    if not sels or any(x[0] != "e" for x in sels):
        raise ValueError("Grow E: select edges of an open contour")
    loop = _open_loop(cage, sels[0])
    wanted = {ekey(loop[i], loop[(i + 1) % len(loop)]) for i in range(len(loop))}
    if {ekey(x[1], x[2]) for x in sels} != wanted:
        raise ValueError("Select the whole open contour (click an edge again for its "
                         "contour), or a single edge")
    return _grow_loop(cage, loop, value, axis)


def _stretch(cage, sel, value, axis, pending):
    _need(sel, "vef", "a point, edge or face")
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
        return Result(sel, "Whole piece stretched (the selection alone has no length along that direction)")
    cage.stretch(ids, value, u)
    return Result(sel, "Stretched")


def _inset_face(cage, sel, value, axis, pending):
    _need(sel, "f", "a face")
    cage.inset_face(sel[1], value)
    return Result(sel, "Face offset")


def _offset_edge(cage, sel, value, axis, pending):
    loop = _open_loop(cage, sel)
    new = cage.offset_edges(loop + [loop[0]], value)
    return Result(("e", new[0], new[1]), "Border offset")


def _squeeze(cage, sel, value, axis, pending):
    _need(sel, "fe", "a face, or an edge of an open contour")
    ax = _axis(cage, sel, axis) if axis != "auto" else None
    if sel[0] == "e":                                # an open edge: its whole contour
        cage.squeeze(_open_loop(cage, sel), value, ax)
        return Result(sel, "Open contour squeezed")
    cage.squeeze(vertex_set(cage, sel), value, ax)
    return Result(sel, "Squeezed")


def squeeze_items(cage, sels, value, axis="auto") -> Result:
    """Squeeze with several items selected (a contour picked with repeated
    clicks, or a few faces): all their points are pinched together towards the
    axis through their centre (Auto: the ring's own normal)."""
    if not sels:
        raise ValueError("Select a face or the edges of a contour first")
    ax = _axis(cage, None, axis) if axis != "auto" else None
    ids = vertex_union(cage, sels)
    if len(ids) < 3:
        raise ValueError("Select at least three points to squeeze")
    cage.squeeze(ids, value, ax)
    return Result(sels[-1], "Squeezed")


def _divide(cage, sel, value, axis, pending):
    """Divide a face (``axis`` "face": that face only; otherwise the cut runs
    on round the piece as a loop) or cut the loop through a chosen edge."""
    _need(sel, "fe", "a face or an edge")
    if sel[0] == "e":
        cage.loop_cut(sel[1], sel[2], whole=axis != "face")
        return Result(sel, "Loop cut" if axis != "face" else "Cut across the face")
    if axis == "face":
        cage.divide_face_only(sel[1])
        return Result(sel, "Face divided")
    cage.divide_face(sel[1])
    return Result(sel, "Face divided")


def _delete_face(cage, sel, value, axis, pending):
    _need(sel, "f", "a face")
    if len(cage.faces) <= 1:
        raise ValueError("A cage needs at least one face")
    cage.remove_faces([sel[1]])
    return Result(None, "Face deleted — Close it again or Bridge it to another opening")


def _close(cage, sel, value, axis, pending):
    loop = _open_loop(cage, sel)
    return Result(("f", cage.close_hole(loop)), "Hole closed")


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
        what = "face" if end[0] == "face" else "opening"
        return Result(sel, f"Now select the other {what} (a face or an edge of an "
                      "opening) and press Apply again", pending=("bridge", end))
    first = pending[1]
    if first[0] == "face" and end[0] == "face" and first[1] == end[1]:
        raise ValueError("Pick a different face")
    if first[0] == "loop" and end[0] == "loop" and set(first[3]) == set(end[3]):
        raise ValueError("Pick an edge of a different opening")
    if len(first[3]) != len(end[3]):
        raise ValueError("Both ends need the same number of sides "
                         f"({len(first[3])} and {len(end[3])})")
    if set(first[3]) & set(end[3]):
        raise ValueError("The two ends touch each other: pick faces that do not share a point")
    drop = [e[1] for e in (first, end) if e[0] == "face"]
    for e in (first, end):
        if e[0] == "face" and tuple(cage.faces[e[1]]) != e[2]:
            raise ValueError("The cage changed since the first click: start the Bridge again")
    if len(drop) >= len(cage.faces):
        raise ValueError("A cage needs at least one face")
    cage.remove_faces(drop)
    cage.bridge(first[3], end[3], twist=int(round(value)))
    return Result(None, "Bridged" if drop else "Openings bridged")


def bridge_two(cage, first, second, value=0.0) -> Result:
    """Bridge two selected ends (faces, or edges of openings) in one go: the
    same work as two Apply clicks, with both ends already chosen."""
    started = _bridge(cage, first, value, "auto", None)
    return _bridge(cage, second, value, "auto", started.pending)


def _shell(cage, sel, value, axis, pending):
    mode = axis if axis in ("inside", "outside", "center") else "outside"
    cage.shell(value, mode)
    return Result(None, f"Wall added ({mode}). Smooth it, or use Finish")


_TOOLS: dict[str, Callable] = {
    "edit": _edit, "crease": _crease, "grow_face": _grow_face,
    "grow_edge": _grow_edge, "stretch": _stretch, "inset_face": _inset_face,
    "offset_edge": _offset_edge, "squeeze": _squeeze, "divide": _divide,
    "delete_face": _delete_face, "close": _close, "bridge": _bridge,
    "shell": _shell,
}


def apply_tool(cage: Cage, tool: str, sel: Selection | None, value: float = 0.0,
               axis: str = "auto", pending=None, sym: dict | None = None) -> Result:
    """Run ``tool`` on ``cage`` in place. ``axis`` is "auto", "x", "y" or "z".
    With ``sym`` (``{"on": True, "point": ..., "normal": ...}``) the work is
    mirrored across that plane. Raises ValueError (status-bar wording) when
    the selection does not fit; the cage is only touched once the selection
    has been checked."""
    if tool not in _TOOLS:
        raise ValueError(f"Unknown tool {tool!r}")
    if sel and not valid(cage, sel):
        raise ValueError("The selection no longer exists")
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


def edge_loop(cage: Cage, a: int, b: int) -> list[tuple[int, int]]:
    """The contour an edge belongs to, as a list of ``(a, b)`` edges (the edge
    itself first). On a border it is the whole border loop; inside the surface
    it is the edge loop that runs straight through every four-way point, and
    stops at any other kind of point. An edge with nothing to follow gives
    just itself."""
    ef = cage.edge_faces()
    if ekey(a, b) not in ef:
        raise ValueError("That is not an edge of the cage")
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
        raise ValueError("That is not an edge of the cage")
    out: list[tuple[str, list[tuple[int, int]]]] = [("Edge", [(a, b)])]
    seen = [{key}]

    def add(label, edges):
        ks = {ekey(x, y) for x, y in edges}
        if ks not in seen:
            seen.append(ks)
            out.append((label, edges))

    loop = edge_loop(cage, a, b)
    if len(loop) > 1:
        add("Loop", loop)
    for fi in ef[key]:
        f = cage.faces[fi]
        ring = [(f[i], f[(i + 1) % len(f)]) for i in range(len(f))]
        add("Face outline", ring)
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
_NO_SYMMETRY = ("bridge", "delete_face", "shell")          # bridge needs two clicks; delete is exact
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


def symmetric_move(cage: Cage, vset, delta, sym: dict | None) -> None:
    """Move points by ``delta``; with an active symmetry the mirrored points
    follow, so a drag on one side reshapes both."""
    vset = list(dict.fromkeys(vset))
    partners = mirror_partners(cage, sym) if sym and sym.get("on") else {}
    cage.move(vset, delta)
    if partners:
        sync_moves(cage, sym, vset, partners)


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
