# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 IngeTrazo contributors.
"""Catmull-Clark subdivision surfaces (pure Python, no NumPy).

Clean-room implementation of the rules published by Catmull & Clark (1978).
The module is UI-independent: it works on plain tuples so it can be wired to
IngeTrazo's own mesh/group classes by a thin adapter.

A control cage is ``(verts, faces)``:
  verts: list of (x, y, z) floats
  faces: list of tuples of vertex indices (any polygon size >= 3)

Boundary edges (used by one face only) follow the standard boundary rules,
so open surfaces keep their outline. Non-manifold edges (3+ faces) are
treated like boundary edges for the point rule and their vertices stay fixed.

Creases (semi-sharp edges) are an optional ``{(a, b): sharpness}`` dict with
integer-valued sharpness: an edge of sharpness ``s`` is treated as sharp for
``s`` subdivision levels, then relaxes into the smooth surface. A vertex with
two sharp edges follows the crease rule, with three or more it is a corner.
"""
from __future__ import annotations

from typing import NamedTuple

Vec = tuple[float, float, float]
Face = tuple[int, ...]


def _avg(points: list[Vec]) -> Vec:
    n = len(points)
    return (
        sum(p[0] for p in points) / n,
        sum(p[1] for p in points) / n,
        sum(p[2] for p in points) / n,
    )


def _lin(a: Vec, wa: float, b: Vec, wb: float) -> Vec:
    return (a[0] * wa + b[0] * wb, a[1] * wa + b[1] * wb, a[2] * wa + b[2] * wb)


def _edge_key(a: int, b: int) -> tuple[int, int]:
    return (a, b) if a < b else (b, a)


def _step(verts, faces, creases):
    """One Catmull-Clark step.

    Returns (verts, faces, creases, edge_idx, parents): ``edge_idx`` maps each
    input edge to the index of its new edge point (so its two children are
    (a, m) and (m, b)); ``parents[i]`` is the input face output face i came from.
    """
    creases = creases or {}
    edge_faces: dict[tuple[int, int], list[int]] = {}
    vert_faces: list[list[int]] = [[] for _ in verts]
    for fi, f in enumerate(faces):
        for i, a in enumerate(f):
            b = f[(i + 1) % len(f)]
            edge_faces.setdefault(_edge_key(a, b), []).append(fi)
            vert_faces[a].append(fi)

    face_pts = [_avg([verts[i] for i in f]) for f in faces]

    edge_pts: dict[tuple[int, int], Vec] = {}
    for (a, b), fl in edge_faces.items():
        if len(fl) == 2 and creases.get((a, b), 0) <= 0:
            edge_pts[(a, b)] = _avg([verts[a], verts[b], face_pts[fl[0]], face_pts[fl[1]]])
        else:  # boundary, non-manifold or creased: plain midpoint
            edge_pts[(a, b)] = _avg([verts[a], verts[b]])

    vert_edges: list[list[tuple[int, int]]] = [[] for _ in verts]
    for e in edge_faces:
        vert_edges[e[0]].append(e)
        vert_edges[e[1]].append(e)

    new_verts: list[Vec] = []
    for vi, p in enumerate(verts):
        edges = vert_edges[vi]
        if not edges or any(len(edge_faces[e]) > 2 for e in edges):
            new_verts.append(p)  # isolated or non-manifold: stays put
            continue
        sharp = [e for e in edges if len(edge_faces[e]) == 1 or creases.get(e, 0) > 0]
        if not sharp or (len(sharp) == 1 and len(edge_faces[sharp[0]]) == 2):
            n = len(edges)
            f_avg = _avg([face_pts[fi] for fi in vert_faces[vi]])
            r_avg = _avg([_avg([verts[e[0]], verts[e[1]]]) for e in edges])
            new_verts.append(
                (
                    (f_avg[0] + 2 * r_avg[0] + (n - 3) * p[0]) / n,
                    (f_avg[1] + 2 * r_avg[1] + (n - 3) * p[1]) / n,
                    (f_avg[2] + 2 * r_avg[2] + (n - 3) * p[2]) / n,
                )
            )
        elif len(sharp) == 2:  # boundary or crease vertex: (6P + A + B) / 8
            others = [e[0] if e[1] == vi else e[1] for e in sharp]
            nb = _lin(verts[others[0]], 1.0, verts[others[1]], 1.0)
            new_verts.append(_lin(p, 6 / 8, nb, 1 / 8))
        else:  # corner
            new_verts.append(p)

    out_verts = list(new_verts)
    face_idx = []
    for fp in face_pts:
        face_idx.append(len(out_verts))
        out_verts.append(fp)
    edge_idx: dict[tuple[int, int], int] = {}
    for e, ep in edge_pts.items():
        edge_idx[e] = len(out_verts)
        out_verts.append(ep)

    out_faces: list[Face] = []
    parents: list[int] = []
    for fi, f in enumerate(faces):
        k = len(f)
        for i in range(k):
            prev_v, v, next_v = f[i - 1], f[i], f[(i + 1) % k]
            out_faces.append(
                (v, edge_idx[_edge_key(v, next_v)], face_idx[fi], edge_idx[_edge_key(prev_v, v)])
            )
            parents.append(fi)

    out_creases: dict[tuple[int, int], float] = {}
    for (a, b), s in creases.items():
        if s > 1 and (a, b) in edge_idx:
            m = edge_idx[(a, b)]
            out_creases[_edge_key(a, m)] = s - 1
            out_creases[_edge_key(m, b)] = s - 1
    return out_verts, out_faces, out_creases, edge_idx, parents


def subdivide_once(verts: list[Vec], faces: list[Face]) -> tuple[list[Vec], list[Face]]:
    """Apply one Catmull-Clark step. Returns a new (verts, faces), all quads."""
    v, f = _step(verts, faces, None)[:2]
    return v, f


def subdivide(
    verts: list[Vec],
    faces: list[Face],
    levels: int = 1,
    creases: dict[tuple[int, int], float] | None = None,
) -> tuple[list[Vec], list[Face]]:
    """Apply ``levels`` Catmull-Clark steps (0 returns a copy of the cage).

    ``creases`` maps an edge ``(a, b)`` to its sharpness (levels it stays sharp).
    """
    if levels < 0:
        raise ValueError("levels must be >= 0")
    v, f = list(verts), [tuple(x) for x in faces]
    c = {_edge_key(*e): s for e, s in (creases or {}).items() if s > 0}
    for _ in range(levels):
        v, f, c = _step(v, f, c)[:3]
    return v, f


class Detailed(NamedTuple):
    """A smoothed cage plus what the display needs to dress it."""
    verts: list[Vec]
    faces: list[Face]
    source: list[int]                       # cage face each output face came from
    lines: set[tuple[int, int]]             # output edges to draw as lines


def subdivide_detailed(
    verts: list[Vec],
    faces: list[Face],
    levels: int = 1,
    creases: dict[tuple[int, int], float] | None = None,
    line_level: int = 0,
) -> Detailed:
    """Like :func:`subdivide`, and also report for every output face which cage
    face it descends from, and which output edges lie on the edges of the mesh
    at ``line_level`` (0 = the cage's own edges, which then read as curved
    panel lines on the smooth surface)."""
    if levels < 0:
        raise ValueError("levels must be >= 0")
    v, f = list(verts), [tuple(x) for x in faces]
    c = {_edge_key(*e): s for e, s in (creases or {}).items() if s > 0}

    def all_edges(fs):
        return {_edge_key(x, fx[(i + 1) % len(fx)]) for fx in fs for i, x in enumerate(fx)}

    source = list(range(len(f)))
    lines = all_edges(f) if line_level <= 0 else None
    for step in range(levels):
        v, f, c, eidx, parents = _step(v, f, c)
        source = [source[p] for p in parents]
        if lines is not None:
            nxt = set()
            for a, b in lines:
                m = eidx.get((a, b))
                if m is not None:
                    nxt.add(_edge_key(a, m))
                    nxt.add(_edge_key(m, b))
            lines = nxt
        if step + 1 == line_level:
            lines = all_edges(f)
    if lines is None:
        lines = all_edges(f)
    return Detailed(v, f, source, lines)
