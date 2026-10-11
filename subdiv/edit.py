# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 IngeTrazo contributors.
"""Editable subdivision control cage and its modelling operations.

Pure Python, UI-independent (no Qt, no NumPy). A :class:`Cage` holds the
control mesh (vertices, polygon faces, creases) and offers the editing
operations of a subdivision modeller; ``Cage.smooth(levels)`` evaluates the
limit-like surface through :mod:`subdiv.subdivide`.

Conventions
-----------
* Faces are tuples of vertex indices, counter-clockwise seen from outside,
  so a closed cage has every directed edge used exactly once.
* Operations edit the cage in place and return the indices they created.
  Indices of existing vertices and faces never change, except
  :meth:`Cage.remove_faces` / :meth:`Cage.prune`, which say so.
* Edges are identified by their two vertex indices, in any order.
"""
from __future__ import annotations

import math
from typing import Iterable, Sequence

from .subdivide import Detailed, Face, Vec, subdivide, subdivide_detailed
from .follow import apply_normal, apply_point

# ---- small vector helpers -------------------------------------------------------


def _sub(a: Vec, b: Vec) -> Vec:
    return (a[0] - b[0], a[1] - b[1], a[2] - b[2])


def _add(a: Vec, b: Vec) -> Vec:
    return (a[0] + b[0], a[1] + b[1], a[2] + b[2])


def _mul(a: Vec, s: float) -> Vec:
    return (a[0] * s, a[1] * s, a[2] * s)


def _dot(a: Vec, b: Vec) -> float:
    return a[0] * b[0] + a[1] * b[1] + a[2] * b[2]


def _length(a: Vec) -> float:
    return math.sqrt(_dot(a, a))


def _unit(a: Vec, fallback: Vec = (0.0, 0.0, 1.0)) -> Vec:
    n = _length(a)
    return fallback if n < 1e-12 else _mul(a, 1.0 / n)


def _centroid(pts: Sequence[Vec]) -> Vec:
    n = len(pts)
    return (sum(p[0] for p in pts) / n, sum(p[1] for p in pts) / n, sum(p[2] for p in pts) / n)


def _newell(pts: Sequence[Vec]) -> Vec:
    """Unnormalised polygon normal (Newell's method), CCW = outward."""
    nx = ny = nz = 0.0
    n = len(pts)
    for i in range(n):
        x0, y0, z0 = pts[i]
        x1, y1, z1 = pts[(i + 1) % n]
        nx += (y0 - y1) * (z0 + z1)
        ny += (z0 - z1) * (x0 + x1)
        nz += (x0 - x1) * (y0 + y1)
    return (nx, ny, nz)


def _triple(a, b, c) -> float:
    return (a[0] * (b[1] * c[2] - b[2] * c[1]) - a[1] * (b[0] * c[2] - b[2] * c[0])
            + a[2] * (b[0] * c[1] - b[1] * c[0]))


def _solve3(m, r):
    """Solve the 3 x 3 system ``m x = r`` (Cramer's rule); None if singular."""
    def det(a):
        return (a[0][0] * (a[1][1] * a[2][2] - a[1][2] * a[2][1])
                - a[0][1] * (a[1][0] * a[2][2] - a[1][2] * a[2][0])
                + a[0][2] * (a[1][0] * a[2][1] - a[1][1] * a[2][0]))
    d = det(m)
    if abs(d) < 1e-12:
        return None
    out = []
    for k in range(3):
        mk = [[r[i] if j == k else m[i][j] for j in range(3)] for i in range(3)]
        out.append(det(mk) / d)
    return (out[0], out[1], out[2])


def ekey(a: int, b: int) -> tuple[int, int]:
    """Canonical (sorted) key of the edge between vertices ``a`` and ``b``."""
    return (a, b) if a < b else (b, a)


class Cage:
    """A subdivision control cage with creases."""

    def __init__(self, verts: Iterable[Vec] = (), faces: Iterable[Face] = (),
                 creases: dict | None = None, colors: Iterable | None = None,
                 sym: dict | None = None) -> None:
        self.verts: list[Vec] = [(float(v[0]), float(v[1]), float(v[2])) for v in verts]
        self.faces: list[Face] = [tuple(f) for f in faces]
        self.creases: dict[tuple[int, int], float] = {
            ekey(*e): float(s) for e, s in (creases or {}).items() if s > 0}
        # One optional (r, g, b) per face, parallel to ``faces``.
        cols = [None if c is None else tuple(c) for c in (colors or [])]
        self.colors: list = (cols + [None] * len(self.faces))[:len(self.faces)]
        # Mirror-symmetry plane: {"on": bool, "point": (x, y, z), "normal": (x, y, z)}
        self.sym: dict | None = None
        if sym:
            self.sym = {"on": bool(sym.get("on", False)),
                        "point": tuple(float(c) for c in sym["point"]),
                        "normal": tuple(float(c) for c in sym["normal"])}

    # ---- construction -------------------------------------------------------------
    @classmethod
    def box(cls, size: Vec = (1.0, 1.0, 1.0), center: Vec = (0.0, 0.0, 0.0)) -> "Cage":
        """Closed box cage (8 vertices, 6 quads) — the usual starting shape."""
        hx, hy, hz = size[0] / 2, size[1] / 2, size[2] / 2
        verts = [(center[0] + sx * hx, center[1] + sy * hy, center[2] + sz * hz)
                 for sz in (-1, 1) for sy in (-1, 1) for sx in (-1, 1)]
        faces = [(0, 2, 3, 1), (4, 5, 7, 6), (0, 1, 5, 4),
                 (2, 6, 7, 3), (0, 4, 6, 2), (1, 3, 7, 5)]
        return cls(verts, faces)

    def copy(self) -> "Cage":
        return Cage(self.verts, self.faces, self.creases, self.colors, self.sym)

    # ---- (de)serialisation: JSON-safe, for storing the cage in a document ----------
    def to_dict(self) -> dict:
        """A JSON-safe snapshot (what a group keeps in its ``ext``)."""
        return {
            "verts": [list(v) for v in self.verts],
            "faces": [list(f) for f in self.faces],
            "creases": [[a, b, s] for (a, b), s in sorted(self.creases.items())],
            "colors": [None if c is None else list(c) for c in self.colors],
            "sym": None if self.sym is None else {
                "on": self.sym["on"], "point": list(self.sym["point"]),
                "normal": list(self.sym["normal"])},
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Cage":
        return cls(
            [tuple(v) for v in data["verts"]],
            [tuple(f) for f in data["faces"]],
            {(a, b): s for a, b, s in data.get("creases", [])},
            data.get("colors"),
            data.get("sym"),
        )

    # ---- queries ------------------------------------------------------------------
    def edge_faces(self) -> dict[tuple[int, int], list[int]]:
        out: dict[tuple[int, int], list[int]] = {}
        for fi, f in enumerate(self.faces):
            for i, a in enumerate(f):
                out.setdefault(ekey(a, f[(i + 1) % len(f)]), []).append(fi)
        return out

    def edges(self) -> list[tuple[int, int]]:
        return list(self.edge_faces())

    def face_normal(self, fi: int) -> Vec:
        return _unit(_newell([self.verts[i] for i in self.faces[fi]]))

    def face_centroid(self, fi: int) -> Vec:
        return _centroid([self.verts[i] for i in self.faces[fi]])

    def is_closed(self) -> bool:
        """True when every edge is shared by exactly two faces."""
        ef = self.edge_faces()
        return bool(ef) and all(len(v) == 2 for v in ef.values())

    def signed_volume(self) -> float:
        """Volume enclosed by the faces (fan from each face's centroid);
        positive when the faces point outwards, negative when inside out."""
        total = 0.0
        for fi, f in enumerate(self.faces):
            c = self.face_centroid(fi)
            for i in range(len(f)):
                a, b = self.verts[f[i]], self.verts[f[(i + 1) % len(f)]]
                total += _triple(c, a, b) / 6.0
        return total

    def solid_report(self, tol: float = 1e-9) -> tuple[bool, list[str], float]:
        """Can this cage make a watertight solid? ``(ok, problems, volume)``.
        Looks for open borders, edges shared by three or more faces, mixed
        winding, points lying on top of each other, degenerate faces and an
        inside-out orientation (which ``orient`` can fix)."""
        problems: list[str] = []
        if len(self.faces) < 4:
            problems.append("fewer than 4 faces")
        ef = self.edge_faces()
        open_edges = sum(1 for v in ef.values() if len(v) == 1)
        bad_edges = sum(1 for v in ef.values() if len(v) > 2)
        if open_edges:
            problems.append(f"{len(self.boundary_loops())} opening(s) left "
                            f"({open_edges} open edges): Close or Bridge them")
        if bad_edges:
            problems.append(f"{bad_edges} edge(s) shared by more than two faces")
        if not self.is_consistent():
            problems.append("faces wind in mixed directions (they will be re-oriented)")
        seen: dict = {}
        used = {v for f in self.faces for v in f}
        for v in used:
            key = tuple(round(c / max(tol, 1e-12)) for c in self.verts[v])
            seen.setdefault(key, []).append(v)
        twins = sum(1 for g in seen.values() if len(g) > 1)
        if twins:
            problems.append(f"{twins} point(s) sit exactly on another point")
        flat = sum(1 for fi in range(len(self.faces))
                   if _length(_newell([self.verts[i] for i in self.faces[fi]])) < 1e-18)
        if flat:
            problems.append(f"{flat} face(s) have no area")
        vol = abs(self.signed_volume()) if not open_edges and not bad_edges else 0.0
        if not open_edges and not bad_edges and vol <= 1e-12:
            problems.append("the cage encloses no volume")
        fatal = [p for p in problems if "re-oriented" not in p]
        return (not fatal), problems, vol

    def is_consistent(self) -> bool:
        """True when no directed edge is used twice (orientation is coherent)."""
        seen = set()
        for f in self.faces:
            for i, a in enumerate(f):
                d = (a, f[(i + 1) % len(f)])
                if d in seen:
                    return False
                seen.add(d)
        return True

    def euler(self) -> int:
        used = {v for f in self.faces for v in f}
        return len(used) - len(self.edge_faces()) + len(self.faces)

    def boundary_loops(self) -> list[list[int]]:
        """Closed chains of open (one-face) edges, each in the direction its
        face uses it — the order :meth:`close_hole` and :meth:`bridge` expect."""
        ef = self.edge_faces()
        nxt: dict[int, list[int]] = {}
        for f in self.faces:
            for i, a in enumerate(f):
                b = f[(i + 1) % len(f)]
                if len(ef[ekey(a, b)]) == 1:
                    nxt.setdefault(a, []).append(b)
        loops: list[list[int]] = []
        for start in list(nxt):
            while nxt.get(start):
                loop, cur = [start], start
                while True:
                    b = nxt[cur].pop(0)
                    if b == start:
                        break
                    loop.append(b)
                    cur = b
                    if not nxt.get(cur):
                        loop = []
                        break
                if len(loop) >= 3:
                    loops.append(loop)
        return loops

    # ---- evaluation ---------------------------------------------------------------
    def smooth(self, levels: int = 2) -> tuple[list[Vec], list[Face]]:
        """The smoothed surface at ``levels`` Catmull-Clark steps (creases kept)."""
        return subdivide(self.verts, self.faces, levels, self.creases)

    def flip(self) -> None:
        """Reverse every face (what was the back becomes the front)."""
        self.faces = [tuple(reversed(f)) for f in self.faces]

    def orient(self) -> int:
        """Make the faces wind consistently (every shared edge used once in
        each direction), and point closed pieces outwards. Imported or
        hand-built meshes often arrive with mixed winding. Returns how many
        faces were flipped."""
        ef = self.edge_faces()
        seen: set[int] = set()
        flipped = 0
        for start in range(len(self.faces)):
            if start in seen:
                continue
            comp = [start]
            seen.add(start)
            stack = [start]
            while stack:
                f = stack.pop()
                loop = self.faces[f]
                for i, a in enumerate(loop):
                    b = loop[(i + 1) % len(loop)]
                    fl = ef[ekey(a, b)]
                    if len(fl) != 2:
                        continue                       # open or non-manifold: no vote
                    g = fl[0] if fl[1] == f else fl[1]
                    if g in seen:
                        continue
                    gl = self.faces[g]
                    if any(gl[j] == a and gl[(j + 1) % len(gl)] == b for j in range(len(gl))):
                        self.faces[g] = tuple(reversed(gl))
                        flipped += 1
                    seen.add(g)
                    comp.append(g)
                    stack.append(g)
            closed = all(len(ef[ekey(f[i], f[(i + 1) % len(f)])]) == 2
                         for c in comp for f in [self.faces[c]] for i in range(len(f)))
            if closed and self._volume(comp) < 0:
                for c in comp:
                    self.faces[c] = tuple(reversed(self.faces[c]))
                    flipped += 1
        return flipped

    def _volume(self, face_indices) -> float:
        """Signed volume enclosed by the given faces (positive = outward)."""
        total = 0.0
        for c in face_indices:
            f = self.faces[c]
            p0 = self.verts[f[0]]
            for i in range(1, len(f) - 1):
                p1, p2 = self.verts[f[i]], self.verts[f[i + 1]]
                total += _dot(p0, (p1[1] * p2[2] - p1[2] * p2[1],
                                   p1[2] * p2[0] - p1[0] * p2[2],
                                   p1[0] * p2[1] - p1[1] * p2[0]))
        return total / 6.0

    def crease_by_angle(self, angle: float = 30.0, sharpness: float = 4.0) -> int:
        """Crease every edge whose two faces meet at more than ``angle``
        degrees, so a converted box stays boxy while a gentle curve rounds
        off. Returns how many edges were creased."""
        limit = math.cos(math.radians(angle))
        normals = [_unit(_newell([self.verts[i] for i in f])) for f in self.faces]
        count = 0
        for (a, b), fl in self.edge_faces().items():
            if len(fl) == 2 and _dot(normals[fl[0]], normals[fl[1]]) < limit:
                self.creases[(a, b)] = float(sharpness)
                count += 1
        return count

    def bounds(self) -> tuple[Vec, Vec]:
        """Opposite corners of the axis-aligned box around the cage."""
        xs, ys, zs = zip(*self.verts) if self.verts else ((0,), (0,), (0,))
        return (min(xs), min(ys), min(zs)), (max(xs), max(ys), max(zs))

    def transform(self, aff) -> None:
        """Carry the whole cage — and its symmetry plane — through the affine
        map ``aff`` (used to follow a group that was moved, rotated or scaled)."""
        self.verts = [apply_point(aff, v) for v in self.verts]
        if self.sym is not None:
            self.sym = {"on": self.sym["on"],
                        "point": apply_point(aff, self.sym["point"]),
                        "normal": apply_normal(aff, self.sym["normal"])}

    def shell(self, thickness: float, mode: str = "outside", rim_crease: float = 2.0) -> None:
        """Give the cage a wall (in place). ``mode`` says where the wall grows
        from the current surface: "outside" (the cage stays the inner skin),
        "inside" (it stays the outer skin) or "center" (half each way). A
        closed cage becomes a hollow body; an open one a thick sheet whose lip
        is closed by a ring of quads, kept crisp by ``rim_crease``.
        The offset is measured on the cage, so the smoothed wall comes out a
        little thinner than ``thickness`` where the surface curves."""
        if mode not in ("outside", "inside", "center"):
            raise ValueError("Shell side must be outside, inside or centred")
        if not (thickness > 0):
            raise ValueError("The wall thickness must be above zero")
        if not self.faces:
            raise ValueError("Nothing to shell")
        self.orient()                    # one winding everywhere (outwards if closed)
        ef = self.edge_faces()
        lo, hi = {"outside": (0.0, thickness), "inside": (-thickness, 0.0),
                  "center": (-thickness / 2, thickness / 2)}[mode]
        normals = self._vertex_normals()
        n = len(self.verts)
        outer = [_add(v, _mul(nm, hi)) for v, nm in zip(self.verts, normals)]
        inner = [_add(v, _mul(nm, lo)) for v, nm in zip(self.verts, normals)]
        faces = [tuple(f) for f in self.faces]
        colors = list(self.colors)
        new_faces = list(faces) + [tuple(v + n for v in reversed(f)) for f in faces]
        new_colors = colors + colors
        creases = dict(self.creases)
        for (a, b), sh in self.creases.items():
            creases[ekey(a + n, b + n)] = sh
        sharp_rim = dict(self.creases)                  # the rim as the user left it
        lip_nbrs: dict[int, list[int]] = {}
        for fi, f in enumerate(faces):
            for i, a in enumerate(f):
                b = f[(i + 1) % len(f)]
                if len(ef[ekey(a, b)]) == 1:             # a lip edge
                    lip_nbrs.setdefault(a, []).append(b)
                    lip_nbrs.setdefault(b, []).append(a)
                    new_faces.append((b, a, a + n, b + n))
                    new_colors.append(colors[fi])
                    if rim_crease > 0:
                        for key in (ekey(a, b), ekey(a + n, b + n)):
                            creases[key] = max(creases.get(key, 0.0), float(rim_crease))
        # A sharp rim that turns a corner (the mouth of a box): crease the edge
        # across the lip there too, or the ring's reflex corner would round the
        # opening off into an oval.
        for a, nb in lip_nbrs.items():
            if len(nb) != 2:
                continue
            s1 = sharp_rim.get(ekey(a, nb[0]), 0.0)
            s2 = sharp_rim.get(ekey(a, nb[1]), 0.0)
            if s1 <= 0 or s2 <= 0:
                continue
            u = _unit(_sub(self.verts[nb[0]], self.verts[a]))
            w = _unit(_sub(self.verts[nb[1]], self.verts[a]))
            if _dot(u, w) > -0.94:                       # turns by more than about 20 degrees
                key = ekey(a, a + n)
                creases[key] = max(creases.get(key, 0.0), min(s1, s2))
        self.verts = outer + inner
        self.faces = new_faces
        self.colors = new_colors
        self.creases = creases

    def _vertex_normals(self) -> list[Vec]:
        """Where each point goes for a wall of thickness 1: the offset ``d``
        that lands as near as possible on every face plane around the point,
        i.e. ``n . d = 1`` for each distinct face normal ``n`` there. On a
        flat area it is the normal; on a box edge or corner it is stretched so
        the wall keeps its full thickness (``(1,1,0)`` and ``(1,1,1)`` for
        square corners), even where an edge carries extra points. Smooth areas
        give about the average normal; unused points get +Z."""
        around: dict[int, list[Vec]] = {}
        for fi, f in enumerate(self.faces):
            nf = self.face_normal(fi)
            for v in f:
                around.setdefault(v, []).append(nf)
        out = []
        for v in range(len(self.verts)):
            fs = around.get(v)
            if not fs:
                out.append((0.0, 0.0, 1.0))
                continue
            distinct: list[Vec] = []
            for nf in fs:                                   # coplanar faces count once
                if all(_dot(nf, o) < 0.9999 for o in distinct):
                    distinct.append(nf)
            m = [[1e-7 if i == j else 0.0 for j in range(3)] for i in range(3)]
            rhs = [0.0, 0.0, 0.0]
            for nf in distinct:
                for i in range(3):
                    rhs[i] += nf[i]
                    for j in range(3):
                        m[i][j] += nf[i] * nf[j]
            d = _solve3(m, rhs)
            if d is None:
                d = _unit(tuple(rhs))
            length = math.sqrt(_dot(d, d))
            if length > 2.5:                                # a very sharp spike: cap it
                d = _mul(d, 2.5 / length)
            out.append(d)
        return out

    def components(self) -> list[list[int]]:
        """Face indices grouped into pieces that share no point (the pieces a
        Join put side by side, before a Bridge links them)."""
        parent = {}

        def find(x):
            while parent.setdefault(x, x) != x:
                parent[x] = parent[parent[x]]
                x = parent[x]
            return x

        for f in self.faces:
            for v in f[1:]:
                parent[find(v)] = find(f[0])
        groups: dict = {}
        for fi, f in enumerate(self.faces):
            groups.setdefault(find(f[0]), []).append(fi)
        return list(groups.values())

    def extract(self, face_indices: Iterable[int]) -> "Cage":
        """A new cage made of just these faces (points renumbered; creases,
        colours and the symmetry plane come along)."""
        keep = sorted(set(face_indices))
        used = sorted({v for fi in keep for v in self.faces[fi]})
        remap = {old: new for new, old in enumerate(used)}
        return Cage([self.verts[v] for v in used],
                    [tuple(remap[v] for v in self.faces[fi]) for fi in keep],
                    {(remap[a], remap[b]): sh for (a, b), sh in self.creases.items()
                     if a in remap and b in remap},
                    [self.colors[fi] for fi in keep], self.sym)

    def merge(self, other: "Cage") -> tuple[int, int]:
        """Append another cage's points, faces, colours and creases to this
        one (its indices are shifted). Returns ``(first new vertex, first new
        face)``. The two pieces stay separate until Bridge joins them."""
        v0, f0 = len(self.verts), len(self.faces)
        self.verts.extend(other.verts)
        self.faces.extend(tuple(v + v0 for v in f) for f in other.faces)
        self.colors.extend(other.colors)
        for (a, b), sharp in other.creases.items():
            self.creases[ekey(a + v0, b + v0)] = sharp
        return v0, f0

    def smooth_detailed(self, levels: int = 2, line_level: int = 0) -> Detailed:
        """Smoothed surface plus the cage face behind each output face and the
        edges to draw as lines (see :func:`subdiv.subdivide.subdivide_detailed`)."""
        return subdivide_detailed(self.verts, self.faces, levels, self.creases, line_level)

    def set_color(self, face_indices: Iterable[int], rgb) -> None:
        """Paint cage faces; ``rgb`` is (r, g, b) in 0..1, or None to clear."""
        for fi in face_indices:
            self.colors[fi] = None if rgb is None else tuple(rgb)

    # ---- internals ----------------------------------------------------------------
    def _new_vert(self, p: Vec) -> int:
        self.verts.append((float(p[0]), float(p[1]), float(p[2])))
        return len(self.verts) - 1

    def _require_edge(self, a: int, b: int) -> None:
        if ekey(a, b) not in self.edge_faces():
            raise ValueError(f"({a}, {b}) is not an edge of the cage")

    # ---- creases ------------------------------------------------------------------
    def set_crease(self, edges: Iterable[tuple[int, int]], sharpness: float = 1.0) -> None:
        """Make edges sharp for ``sharpness`` subdivision levels (0 clears them)."""
        for a, b in edges:
            self._require_edge(a, b)
            if sharpness > 0:
                self.creases[ekey(a, b)] = float(sharpness)
            else:
                self.creases.pop(ekey(a, b), None)

    # ---- moving points ------------------------------------------------------------
    def move(self, vids: Iterable[int], delta: Vec) -> None:
        """Translate the given vertices."""
        for v in set(vids):
            self.verts[v] = _add(self.verts[v], delta)

    def rotate(self, vids: Iterable[int], pivot: Vec, axis: Vec, angle: float) -> None:
        """Turn the given vertices by ``angle`` (radians, right-hand rule)
        around the line through ``pivot`` along ``axis``."""
        n = math.sqrt(_dot(axis, axis))
        if n < 1e-12 or abs(angle) < 1e-15:
            return
        k = (axis[0] / n, axis[1] / n, axis[2] / n)
        c, s = math.cos(angle), math.sin(angle)
        for v in set(vids):
            r = _sub(self.verts[v], pivot)
            kr = _dot(k, r)
            cr = (k[1] * r[2] - k[2] * r[1], k[2] * r[0] - k[0] * r[2],
                  k[0] * r[1] - k[1] * r[0])
            self.verts[v] = _add(pivot, (
                r[0] * c + cr[0] * s + k[0] * kr * (1 - c),
                r[1] * c + cr[1] * s + k[1] * kr * (1 - c),
                r[2] * c + cr[2] * s + k[2] * kr * (1 - c)))

    def stretch(self, vids: Sequence[int], factor: float, axis: Vec,
                origin: Vec | None = None) -> None:
        """Scale the selection along ``axis`` only (Stretch)."""
        ids = list(dict.fromkeys(vids))
        o = origin if origin is not None else _centroid([self.verts[v] for v in ids])
        u = _unit(axis)
        for v in ids:
            d = _sub(self.verts[v], o)
            self.verts[v] = _add(self.verts[v], _mul(u, _dot(d, u) * (factor - 1.0)))

    def squeeze(self, vids: Sequence[int], factor: float, axis: Vec | None = None,
                origin: Vec | None = None) -> None:
        """Scale the selection across ``axis`` (towards it for factor < 1):
        pinch a ring of points. ``axis`` defaults to the ring's own normal."""
        ids = list(dict.fromkeys(vids))
        pts = [self.verts[v] for v in ids]
        o = origin if origin is not None else _centroid(pts)
        u = _unit(axis) if axis is not None else _unit(_newell(pts))
        for v in ids:
            d = _sub(self.verts[v], o)
            along = _mul(u, _dot(d, u))
            across = _sub(d, along)
            self.verts[v] = _add(o, _add(along, _mul(across, factor)))

    # ---- faces: grow / offset -----------------------------------------------------
    def _extrude_core(self, fi: int, shrink: float, height: float) -> list[int]:
        f = self.faces[fi]
        c = self.face_centroid(fi)
        n = self.face_normal(fi)
        new = []
        for vi in f:
            p = self.verts[vi]
            q = _add(_add(c, _mul(_sub(p, c), 1.0 - shrink)), _mul(n, height))
            new.append(self._new_vert(q))
        k = len(f)
        # A sharp face stays sharp: the new outline takes the sharpness of the
        # edge it grows from, and a side edge is as sharp as the corner it rises
        # from (both of the corner's outline edges sharp), so a box pushed out
        # stays a box instead of rounding off.
        for i in range(k):
            s_here = self.creases.get(ekey(f[i], f[(i + 1) % k]), 0.0)
            s_prev = self.creases.get(ekey(f[i - 1], f[i]), 0.0)
            if s_here > 0:
                self.creases[ekey(new[i], new[(i + 1) % k])] = s_here
            if min(s_here, s_prev) > 0:
                self.creases[ekey(f[i], new[i])] = min(s_here, s_prev)
        sides = [(f[i], f[(i + 1) % k], new[(i + 1) % k], new[i]) for i in range(k)]
        self.faces[fi] = tuple(new)
        self.faces.extend(sides)
        self.colors.extend([self.colors[fi]] * len(sides))
        return new

    def extrude_face(self, fi: int, height: float) -> list[int]:
        """Grow F: push a face out along its normal, adding the side walls.
        Returns the new vertices (the face keeps its index)."""
        return self._extrude_core(fi, 0.0, height)

    def inset_face(self, fi: int, amount: float, height: float = 0.0) -> list[int]:
        """Offset F: an inner copy of the face, ``amount`` (0..1) of the way to
        its centre, optionally raised by ``height``."""
        if not 0.0 <= amount < 1.0:
            raise ValueError("amount must be in [0, 1)")
        return self._extrude_core(fi, amount, height)

    # ---- edges: grow / offset -----------------------------------------------------
    def _grow_chain(self, chain: Sequence[int], place) -> list[int]:
        chain = list(chain)
        closed = len(chain) > 2 and chain[0] == chain[-1]
        if closed:
            chain = chain[:-1]
        if len(chain) < 2:
            raise ValueError("need at least one edge")
        ef = self.edge_faces()
        used = {(f[i], f[(i + 1) % len(f)]) for f in self.faces for i in range(len(f))}

        def pairs(c):
            m = len(c) if closed else len(c) - 1
            return [(c[i], c[(i + 1) % len(c)]) for i in range(m)]

        ps = pairs(chain)
        if ps[0] not in used:
            chain.reverse()
            ps = pairs(chain)
        for a, b in ps:
            if (a, b) not in used or len(ef[ekey(a, b)]) != 1:
                raise ValueError("edges must form an open (boundary) chain")
        c = _centroid([self.verts[v] for v in chain])
        new = {v: self._new_vert(place(self.verts[v], c)) for v in chain}
        for a, b in ps:
            self.faces.append((b, a, new[a], new[b]))
            self.colors.append(None)
        return [new[v] for v in chain]

    def extrude_edges(self, chain: Sequence[int], vector: Vec) -> list[int]:
        """Grow E: extend an open edge (or chain of open edges, as a vertex
        list) by ``vector``, adding a band of faces. Returns the new vertices."""
        return self._grow_chain(chain, lambda p, c: _add(p, vector))

    def offset_edges(self, chain: Sequence[int], amount: float,
                     vector: Vec = (0.0, 0.0, 0.0)) -> list[int]:
        """Offset E: a copy of an open edge chain pulled ``amount`` (0..1)
        towards the chain's centre, optionally shifted by ``vector``."""
        return self._grow_chain(
            chain, lambda p, c: _add(_add(c, _mul(_sub(p, c), 1.0 - amount)), vector))

    # ---- splitting ----------------------------------------------------------------
    def split_edge(self, a: int, b: int, t: float = 0.5, _skip: int | None = None) -> int:
        """Insert a vertex at ``t`` along a→b in every face using the edge.
        A crease on the edge is inherited by both halves."""
        self._require_edge(a, b)
        pa, pb = self.verts[a], self.verts[b]
        m = self._new_vert(_add(pa, _mul(_sub(pb, pa), t)))
        for gi, g in enumerate(self.faces):
            if gi == _skip:
                continue
            for i in range(len(g)):
                if {g[i], g[(i + 1) % len(g)]} == {a, b}:
                    self.faces[gi] = g[:i + 1] + (m,) + g[i + 1:]
                    break
        s = self.creases.pop(ekey(a, b), None)
        if s:
            self.creases[ekey(a, m)] = s
            self.creases[ekey(m, b)] = s
        return m

    def edge_ring(self, a: int, b: int):
        """The ring of quads that edge ``a``-``b`` cuts across: ``(edges, faces,
        closed)`` where ``edges`` are the (a, b) pairs the ring crosses, in
        order, and ``faces`` the quads between them. The walk goes through
        the opposite edge of every quad and stops at a border or at a face
        that is not a quad."""
        emap: dict = {}
        for gi, g in enumerate(self.faces):
            for i in range(len(g)):
                emap.setdefault(ekey(g[i], g[(i + 1) % len(g)]), []).append(gi)

        def walk(first_edge, fi):
            edges, faces = [], []
            e = first_edge
            while True:
                g = self.faces[fi]
                if len(g) != 4 or fi in faces:
                    return edges, faces, fi in faces
                i = next((k for k in range(4)
                          if {g[k], g[(k + 1) % 4]} == {e[0], e[1]}), None)
                if i is None:
                    return edges, faces, False
                if g[i] == e[0]:
                    nxt = (g[(i + 3) % 4], g[(i + 2) % 4])
                else:
                    nxt = (g[(i + 2) % 4], g[(i + 3) % 4])
                faces.append(fi)
                edges.append(nxt)
                others = [x for x in emap.get(ekey(*nxt), []) if x != fi]
                if not others:
                    return edges, faces, False
                fi = others[0]
                e = nxt
                if ekey(*e) == ekey(a, b):
                    return edges[:-1], faces, True

        start = (a, b)
        adj = emap.get(ekey(a, b), [])
        if not adj:
            raise ValueError("no such edge")
        fw_e, fw_f, closed = walk(start, adj[0])
        if closed or len(adj) < 2:
            return [start] + fw_e, fw_f, closed
        bw_e, bw_f, _ = walk(start, adj[1])
        edges = list(reversed(bw_e)) + [start] + fw_e
        faces = list(reversed(bw_f)) + fw_f
        return edges, faces, False

    def _local_ring(self, a: int, b: int):
        """Like :meth:`edge_ring` but only the quads that touch edge ``a``-``b``."""
        edges, faces = [(a, b)], []
        for gi, g in enumerate(self.faces):
            if len(g) != 4:
                continue
            for i in range(4):
                if {g[i], g[(i + 1) % 4]} == {a, b}:
                    faces.append(gi)
                    edges.append((g[(i + 3) % 4], g[(i + 2) % 4]) if g[i] == a
                                 else (g[(i + 2) % 4], g[(i + 3) % 4]))
                    break
        if not faces:
            raise ValueError("no quad touches that edge")
        return edges, faces, False

    def loop_cut(self, a: int, b: int, whole: bool = True) -> dict:
        """Cut the whole ring of quads across edge ``a``-``b`` in two, joining the
        midpoints of the edges it crosses. Faces that are not quads at the
        end of the ring just gain the midpoint. Sharp edges stay sharp, and
        the new cut is sharp when the quad it crosses is sharp all round (a
        flat panel). With ``whole`` False only the quads touching the edge are cut:
        the faces beyond just gain the midpoint. Returns ``{old face: [new faces]}``."""
        edges, ring, _closed = self.edge_ring(a, b) if whole else self._local_ring(a, b)
        ring_set = set(ring)
        mids = {}
        for (u, v) in edges:
            k = ekey(u, v)
            if k in mids:
                continue
            m = self._new_vert(_mul(_add(self.verts[u], self.verts[v]), 0.5))
            mids[k] = m
        # sharpness of each quad's four sides, before the edges are split
        rim = {}
        for fi in ring:
            g = self.faces[fi]
            rim[fi] = min(self.creases.get(ekey(g[i], g[(i + 1) % 4]), 0.0) for i in range(4))
        for (u, v), m in ((e, mids[ekey(*e)]) for e in edges):
            s = self.creases.pop(ekey(u, v), None)
            if s:
                self.creases[ekey(u, m)] = s
                self.creases[ekey(m, v)] = s
        out: dict = {}
        for fi in ring:
            g = self.faces[fi]
            i = next(k for k in range(4) if ekey(g[k], g[(k + 1) % 4]) in mids
                     and ekey(g[(k + 2) % 4], g[(k + 3) % 4]) in mids)
            m1 = mids[ekey(g[i], g[(i + 1) % 4])]
            m2 = mids[ekey(g[(i + 2) % 4], g[(i + 3) % 4])]
            first = (g[i], m1, m2, g[(i + 3) % 4])
            second = (m1, g[(i + 1) % 4], g[(i + 2) % 4], m2)
            self.faces[fi] = first
            self.faces.append(second)
            self.colors.append(self.colors[fi])
            out[fi] = [fi, len(self.faces) - 1]
            if rim[fi] > 0:
                self.creases[ekey(m1, m2)] = rim[fi]
        for gi, g in enumerate(self.faces):             # faces beside the ring's open end
            if gi in ring_set or gi in {x for v in out.values() for x in v}:
                continue
            for i in range(len(g)):
                k = ekey(g[i], g[(i + 1) % len(g)])
                if k in mids:
                    self.faces[gi] = g = g[:i + 1] + (mids[k],) + g[i + 1:]
                    break
        return out

    def divide_face_only(self, fi: int) -> list[int]:
        """Divide just this face: one quad per corner around a new centre point,
        the neighbouring faces gaining the edge midpoints (they stop being
        quads). Sharp all round -> the cuts are sharp. Returns the pieces."""
        f = self.faces[fi]
        k = len(f)
        rim = min(self.creases.get(ekey(f[i], f[(i + 1) % k]), 0.0) for i in range(k))
        mids = [self.split_edge(f[i], f[(i + 1) % k], _skip=fi) for i in range(k)]
        c = self._new_vert(self.face_centroid(fi))
        if rim > 0:
            for m in mids:
                self.creases[ekey(m, c)] = rim
        quads = [(f[i], mids[i], c, mids[i - 1]) for i in range(k)]
        self.faces[fi] = quads[0]
        first = len(self.faces)
        self.faces.extend(quads[1:])
        self.colors.extend([self.colors[fi]] * (k - 1))
        return [fi] + list(range(first, first + k - 1))

    def divide_face(self, fi: int) -> list[int]:
        """Divide: cut a quad into four with two loop cuts, one across each pair
        of opposite edges; every cut carries on through the quads beyond, so
        the cage stays all quads. A face with another number of sides is cut
        into one quad per corner around a new centre point, the neighbours
        gaining the edge midpoints. When every edge of the face is sharp the
        new cuts are sharp too. Returns the face indices of the pieces."""
        f = self.faces[fi]
        k = len(f)
        if k == 4:
            region = {fi}
            for (u, v) in ((f[0], f[1]), (f[1], f[2])):
                try:
                    mp = self.loop_cut(u, v)
                except ValueError:                  # that edge was split by the first cut
                    continue
                nxt = set()
                for gi in region:
                    nxt.update(mp.get(gi, [gi]))
                region = nxt
            return sorted(region)
        return self.divide_face_only(fi)

    # ---- holes and bridges --------------------------------------------------------
    def close_hole(self, loop: Sequence[int]) -> int:
        """Close: fill a boundary loop (from :meth:`boundary_loops`) with one face."""
        if len(loop) < 3:
            raise ValueError("a hole needs at least 3 vertices")
        self.faces.append(tuple(reversed(loop)))
        self.colors.append(None)
        return len(self.faces) - 1

    def bridge(self, loop_a: Sequence[int], loop_b: Sequence[int],
               shift: int | None = None, twist: int = 0) -> list[int]:
        """Bridge: join two boundary loops of equal size with a ring of quads.
        ``shift`` picks which vertex of B meets A[0]; by default the pairing
        with the smallest total distance is used. ``twist`` then turns the
        ring by that many vertices (either way). Returns the new faces."""
        A, B = list(loop_a), list(loop_b)
        n = len(A)
        if n != len(B) or n < 3:
            raise ValueError("both loops need the same number of vertices (>= 3)")
        if shift is None:
            def cost(s):
                return sum(_length(_sub(self.verts[A[i]], self.verts[B[(s - i) % n]]))
                           for i in range(n))
            shift = min(range(n), key=cost)
        shift = (shift + int(twist)) % n
        out = []
        for i in range(n):
            a0, a1 = A[i], A[(i + 1) % n]
            b0, b1 = B[(shift - i) % n], B[(shift - i - 1) % n]
            self.faces.append((a1, a0, b0, b1))
            self.colors.append(None)
            out.append(len(self.faces) - 1)
        return out

    # ---- clean-up -----------------------------------------------------------------
    def remove_faces(self, indices: Iterable[int]) -> None:
        """Delete faces. Later faces are renumbered; vertices are kept."""
        drop = set(indices)
        self.colors = [c for i, c in enumerate(self.colors) if i not in drop]
        self.faces = [f for i, f in enumerate(self.faces) if i not in drop]

    def prune(self) -> None:
        """Drop vertices no face uses and renumber (creases follow)."""
        used = sorted({v for f in self.faces for v in f})
        remap = {old: new for new, old in enumerate(used)}
        self.verts = [self.verts[v] for v in used]
        self.faces = [tuple(remap[v] for v in f) for f in self.faces]
        self.creases = {ekey(remap[a], remap[b]): s for (a, b), s in self.creases.items()
                        if a in remap and b in remap}
