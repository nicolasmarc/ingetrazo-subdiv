# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 IngeTrazo contributors.
"""Cage modelling operations beyond the basics: Revolve, Bevel, Slice, Merge,
Dissolve and Slide. Plain functions on a :class:`Cage` (no Qt); each raises
``ValueError`` with a status-bar sentence when it cannot act, and leaves the
cage untouched in that case.

Written from scratch from the usual definitions of these operations.
"""
from __future__ import annotations

import math
from typing import Sequence

from .edit import Cage, ekey
from .lang import T as _T


# ---- small vector helpers ---------------------------------------------------------------
def _sub(a, b):
    return (a[0] - b[0], a[1] - b[1], a[2] - b[2])


def _add(a, b):
    return (a[0] + b[0], a[1] + b[1], a[2] + b[2])


def _mul(a, s):
    return (a[0] * s, a[1] * s, a[2] * s)


def _dot(a, b):
    return a[0] * b[0] + a[1] * b[1] + a[2] * b[2]


def _cross(a, b):
    return (a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0])


def _len(a):
    return math.sqrt(_dot(a, a))


def _unit(a):
    n = _len(a)
    return _mul(a, 1.0 / n) if n > 1e-15 else (0.0, 0.0, 0.0)


def _lerp(a, b, t):
    return _add(a, _mul(_sub(b, a), t))


def _tolerance(cage: Cage) -> float:
    if not cage.verts:
        return 1e-9
    lo, hi = cage.bounds()
    return 1e-6 * (math.dist(lo, hi) or 1.0) + 1e-12


AXES = {"x": (1.0, 0.0, 0.0), "y": (0.0, 1.0, 0.0), "z": (0.0, 0.0, 1.0)}


def _snapshot(cage: Cage):
    return (list(cage.verts), list(cage.faces), dict(cage.creases), list(cage.colors),
            dict(getattr(cage, "vcreases", {})))


def _restore(cage: Cage, snap) -> None:
    cage.verts, cage.faces, cage.creases, cage.colors = snap[0], snap[1], snap[2], snap[3]
    if hasattr(cage, "vcreases"):
        cage.vcreases = snap[4]


# ---- the fan of faces around a point ----------------------------------------------------
def fan(cage: Cage, v: int):
    """Faces and neighbours around point ``v`` in winding order, for a point
    inside the surface: ``(faces, nbrs)`` where face ``i`` runs from ``nbrs[i-1]``
    to ``nbrs[i]`` through ``v``. Returns None for a border, non-manifold or
    badly wound point."""
    around = []
    for fi, f in enumerate(cage.faces):
        for i, x in enumerate(f):
            if x == v:
                around.append((fi, f[i - 1], f[(i + 1) % len(f)]))
    if len(around) < 3:
        return None
    by_prev = {}
    for fi, p, n in around:
        if p in by_prev:
            return None
        by_prev[p] = (fi, n)
    fi, p, n = around[0]
    faces, nbrs = [fi], [n]
    while True:
        if n not in by_prev:
            return None
        fj, n2 = by_prev[n]
        if fj == faces[0]:
            break
        if fj in faces:
            return None
        faces.append(fj)
        nbrs.append(n2)
        n = n2
    if len(faces) != len(around) or nbrs[-1] != p:
        return None
    return faces, nbrs


# ---- Revolve ----------------------------------------------------------------------------
def _rotate_about(p, axis, ang):
    c, s = math.cos(ang), math.sin(ang)
    k = _unit(axis)
    return _add(_add(_mul(p, c), _mul(_cross(k, p), s)), _mul(k, _dot(k, p) * (1.0 - c)))


def revolve(cage: Cage, face: int, axis: str, segments: int = 8, angle: float = 360.0,
            profile=None, closed: bool = True) -> int:
    """Turn the profile face round the X, Y or Z axis through the origin into a
    surface of revolution made of ``segments`` steps. The profile stays in
    place unless it is the whole cage (then it is used up). A full turn closes
    the ring; a partial turn leaves the two ends open. Points on the axis
    become single points (triangles at the poles). Returns the number of faces added."""
    if axis not in AXES:
        raise ValueError(_T("Choose X, Y or Z: the axis the profile turns around"))
    segments = int(round(segments))
    if segments < 3:
        raise ValueError(_T("A revolution needs at least 3 segments"))
    if not 0.0 < angle <= 360.0:
        raise ValueError(_T("The angle must be between 0 and 360 degrees"))
    prof = list(profile) if profile is not None else list(cage.faces[face])
    ax = AXES[axis]
    tol = _tolerance(cage)
    full = angle >= 359.999
    steps = segments if full else segments + 1
    pts = [cage.verts[v] for v in prof]
    on_axis = [_len(_cross(ax, p)) <= tol for p in pts]
    if all(on_axis):
        raise ValueError(_T("The profile lies on the axis: move it away first"))
    snap = _snapshot(cage)
    try:
        ring = []
        for k in range(steps):
            a = math.radians(angle) * k / segments
            row = []
            for p, ona in zip(pts, on_axis):
                if ona:
                    q = _mul(ax, _dot(ax, p))
                    row.append(None if k else ("axis", q))
                else:
                    row.append(_rotate_about(p, ax, a))
            ring.append(row)
        ids: list[list[int]] = []
        axis_id: dict[int, int] = {}
        for k, row in enumerate(ring):
            r = []
            for j, q in enumerate(row):
                if on_axis[j]:
                    if j not in axis_id:
                        axis_id[j] = cage._new_vert(ring[0][j][1])
                    r.append(axis_id[j])
                else:
                    r.append(cage._new_vert(q))
            ids.append(r)
        n = len(prof)
        added = 0
        for k in range(segments):
            k2 = (k + 1) % steps if full else k + 1
            for j in range(n):
                if not closed and j == n - 1:
                    continue                          # an open profile does not wrap round
                j2 = (j + 1) % n
                u0, v0, v1, u1 = ids[k][j], ids[k][j2], ids[k2][j2], ids[k2][j]
                if on_axis[j] and on_axis[j2]:
                    continue
                quad = [u0, v0, v1, u1]
                quad = [x for i, x in enumerate(quad) if x != quad[i - 1]]
                cage.faces.append(tuple(quad))
                cage.colors.append(None)
                added += 1
        if not full and closed:                       # close the two ends with copies of the profile
            for k in (0, steps - 1):
                cage.faces.append(tuple(dict.fromkeys(ids[k])))
                cage.colors.append(None)
                added += 1
        if profile is None and len(cage.faces) - added == 1:   # the profile was the whole cage: used up
            cage.faces.pop(face)
            cage.colors.pop(face)
            cage.prune()
        else:
            _use_new_faces(cage, added)
        cage.orient()
        return added
    except Exception:
        _restore(cage, snap)
        raise


def _use_new_faces(cage: Cage, added: int) -> None:
    """Nothing to do for now: kept as the one place to hook face bookkeeping."""
    return None


# ---- Bevel (chamfer) --------------------------------------------------------------------
def bevel(cage: Cage, edges: Sequence[tuple[int, int]], width: float) -> list[int]:
    """Replace each edge by a narrow strip of faces ``width`` wide (a chamfer).
    The edges must lie inside the surface (two faces each) and their end points
    too. At a point where several beveled edges meet a small face closes the
    corner. Returns the indices of the new faces."""
    if width <= 0:
        raise ValueError(_T("The bevel width must be above zero"))
    ef = cage.edge_faces()
    keys = []
    for a, b in edges:
        k = ekey(a, b)
        if k not in ef:
            raise ValueError(_T("That is not an edge of the cage"))
        if len(ef[k]) != 2:
            raise ValueError(_T("Bevel needs an edge inside the surface, not on a border"))
        if k not in keys:
            keys.append(k)
    if not keys:
        raise ValueError(_T("Select an edge to bevel"))
    if not cage.is_consistent():
        cage.orient()
    bev_nbrs: dict[int, set[int]] = {}
    for a, b in keys:
        bev_nbrs.setdefault(a, set()).add(b)
        bev_nbrs.setdefault(b, set()).add(a)

    P = cage.verts
    plan = {}                                 # point -> (fan, nbrs, beveled indices)
    for v, bn in bev_nbrs.items():
        fn = fan(cage, v)
        if fn is None:
            raise ValueError(_T("Bevel needs the edge's end points to be inside the surface"))
        faces, nbrs = fn
        idx = [i for i, n in enumerate(nbrs) if n in bn]
        plan[v] = (faces, nbrs, idx)
        shortest = min(_len(_sub(P[n], P[v])) for n in nbrs)
        if width > 0.5 * shortest + 1e-12:
            raise ValueError(_T("The bevel is too wide for this edge: use a smaller width"))

    snap = _snapshot(cage)
    try:
        created: dict[int, list[int]] = {}          # old point -> its new points
        vf: dict[tuple[int, int], int] = {}          # (old point, face) -> new point
        extra: dict[tuple[int, int], list[int]] = {}  # (old point, face) -> points to put instead
        caps = []
        for v, (faces, nbrs, idx) in plan.items():
            d = len(faces)
            pv = P[v]
            k = len(idx)
            new = []
            if k == 1:
                j = idx[0]
                a1 = cage._new_vert(_add(pv, _mul(_unit(_sub(P[nbrs[j - 1]], pv)), width)))
                a2 = cage._new_vert(_add(pv, _mul(_unit(_sub(P[nbrs[(j + 1) % d]], pv)), width)))
                new = [a1, a2]
                # face j ends at the beveled edge, face j+1 starts there
                vf[(v, faces[j])] = a1
                vf[(v, faces[(j + 1) % d])] = a2
                rest = [(j + 2 + t) % d for t in range(d - 2)]
                if len(rest) == 1:
                    extra[(v, faces[rest[0]])] = [a2, a1]
                else:
                    extra[(v, faces[rest[0]])] = [a2, v]
                    extra[(v, faces[rest[-1]])] = [v, a1]
                    caps.append((a2, a1, v))
            else:
                order = sorted(idx)
                sect = []
                for t, i0 in enumerate(order):
                    i1 = order[(t + 1) % k]
                    span = list(range(i0, i1 + 1)) if i1 > i0 else \
                        list(range(i0, i0 + ((i1 - i0) % d or d) + 1))
                    s_dir = (0.0, 0.0, 0.0)
                    for m in span:
                        s_dir = _add(s_dir, _unit(_sub(P[nbrs[m % d]], pv)))
                    s = cage._new_vert(_add(pv, _mul(_unit(s_dir), width)))
                    new.append(s)
                    sect.append(s)
                    for m in range(i0 + 1, i0 + 1 + ((i1 - i0) % d or d)):
                        vf[(v, faces[m % d])] = s
                if k >= 3:
                    caps.append(tuple(sect))
            created[v] = new

        # rebuild the faces around the beveled points
        for fi, f in enumerate(cage.faces):
            if not any(x in plan for x in f):
                continue
            out = []
            for x in f:
                if x in plan:
                    if (x, fi) in extra:
                        out.extend(extra[(x, fi)])
                    else:
                        out.append(vf.get((x, fi), x))
                else:
                    out.append(x)
            cage.faces[fi] = tuple(y for i, y in enumerate(out) if y != out[i - 1])
        for v in plan:                                # the old point is gone when nothing uses it
            pass

        first = len(cage.faces)
        for a, b in keys:                             # the strips
            f1, f2 = ef[(a, b)]
            quad = (vf[(a, f1)], vf[(b, f1)], vf[(b, f2)], vf[(a, f2)])
            cage.faces.append(quad)
            cage.colors.append(None)
        for cap in caps:
            cage.faces.append(tuple(cap))
            cage.colors.append(None)
        # creases: bevelled edges disappear; others follow their end points
        old = dict(cage.creases)
        cage.creases = {}
        new_edges = {ekey(f[i], f[(i + 1) % len(f)]) for f in cage.faces for i in range(len(f))}
        near = {v: {v, *created.get(v, [])} for v in range(len(P))}
        for (a, b), s in old.items():
            if (a, b) in keys:
                continue
            for (p, q) in new_edges:
                if (p in near[a] and q in near[b]) or (p in near[b] and q in near[a]):
                    cage.creases[ekey(p, q)] = s
        cage.orient()
        _drop_unused(cage)
        return list(range(first, len(cage.faces)))
    except Exception:
        _restore(cage, snap)
        raise


def _drop_unused(cage: Cage) -> None:
    """Remove points no face uses (the old corner points after a bevel)."""
    if len({v for f in cage.faces for v in f}) != len(cage.verts):
        cage.prune()


# ---- Slice ------------------------------------------------------------------------------
def slice_plane(cage: Cage, point, normal, tol: float | None = None) -> list[tuple[int, int]]:
    """Cut the cage with a plane: a point is added where the plane crosses an
    edge, and every face the plane runs through is split in two along it.
    Faces must be convex where they are cut. Returns the new edges lying in
    the plane (empty when the plane misses the cage)."""
    n = _unit(normal)
    if _len(n) == 0:
        raise ValueError(_T("Choose X, Y or Z: the plane is perpendicular to that axis"))
    tol = _tolerance(cage) if tol is None else tol
    d = [_dot(_sub(p, point), n) for p in cage.verts]
    side = [0 if abs(x) <= tol else (1 if x > 0 else -1) for x in d]
    snap = _snapshot(cage)
    try:
        cut_pt: dict[tuple[int, int], int] = {}

        def cross(a, b):
            k = ekey(a, b)
            if k not in cut_pt:
                t = d[a] / (d[a] - d[b])
                cut_pt[k] = cage._new_vert(_lerp(cage.verts[a], cage.verts[b], t))
            return cut_pt[k]

        old_faces = list(cage.faces)
        for f in old_faces:                           # first, make every crossing point
            for i, a in enumerate(f):
                b = f[(i + 1) % len(f)]
                if side[a] * side[b] < 0:
                    cross(a, b)
        new_edges = []
        out_faces, out_cols = [], []
        for fi, f in enumerate(old_faces):
            k = len(f)
            ring = []                                  # the face with crossing points inserted
            for i, a in enumerate(f):
                b = f[(i + 1) % k]
                ring.append(a)
                if side[a] * side[b] < 0:
                    ring.append(cut_pt[ekey(a, b)])
            on = [i for i, x in enumerate(ring) if (x >= len(snap[0]) or side[x] == 0)]
            sides = {side[x] for x in f}
            if len(on) < 2 or sides <= {0, 1} or sides <= {0, -1}:
                out_faces.append(tuple(ring))
                out_cols.append(cage.colors[fi])
                continue
            if len(on) != 2:
                raise ValueError(_T("A face is not convex where the plane cuts it: divide it first"))
            i, j = on
            if (j - i) % len(ring) in (1, len(ring) - 1):
                out_faces.append(tuple(ring))
                out_cols.append(cage.colors[fi])
                continue
            first = tuple(ring[i:j + 1])
            second = tuple(ring[j:] + ring[:i + 1])
            out_faces.extend([first, second])
            out_cols.extend([cage.colors[fi]] * 2)
            new_edges.append(ekey(ring[i], ring[j]))
        cage.faces, cage.colors = out_faces, out_cols
        # creased edges that were cut keep their sharpness on both halves
        old = dict(cage.creases)
        cage.creases = {}
        for (a, b), s in old.items():
            m = cut_pt.get(ekey(a, b))
            if m is None:
                cage.creases[(a, b)] = s
            else:
                cage.creases[ekey(a, m)] = s
                cage.creases[ekey(m, b)] = s
        cage.orient() if not cage.is_consistent() else None
        return sorted(set(new_edges))
    except Exception:
        _restore(cage, snap)
        raise


# ---- Merge ------------------------------------------------------------------------------
def _replace_points(cage: Cage, mapping: dict[int, int]) -> None:
    """Rename points everywhere (faces and creases); faces left with fewer than
    three distinct points are dropped; the cage is then pruned."""
    faces, cols = [], []
    for fi, f in enumerate(cage.faces):
        g = [mapping.get(x, x) for x in f]
        g = [x for i, x in enumerate(g) if x != g[i - 1]]
        if len(g) >= 3 and len(set(g)) == len(g):
            faces.append(tuple(g))
            cols.append(cage.colors[fi])
    old = dict(cage.creases)
    cage.faces, cage.colors, cage.creases = faces, cols, {}
    for (a, b), s in old.items():
        a, b = mapping.get(a, a), mapping.get(b, b)
        if a != b:
            cage.creases[ekey(a, b)] = max(s, cage.creases.get(ekey(a, b), 0.0))
    if hasattr(cage, "vcreases"):
        cage.vcreases = {mapping.get(v, v): s for v, s in cage.vcreases.items()}
    cage.prune()


def collapse_edge(cage: Cage, a: int, b: int) -> int:
    """Merge the two ends of an edge at its middle. Faces that were triangles
    on it disappear. Returns the merged point's index (after clean-up)."""
    cage._require_edge(a, b)
    snap = _snapshot(cage)
    try:
        cage.verts[a] = _lerp(cage.verts[a], cage.verts[b], 0.5)
        pos = cage.verts[a]
        _replace_points(cage, {b: a})
        if not cage.faces:
            raise ValueError(_T("A cage needs at least one face"))
        return min(range(len(cage.verts)), key=lambda i: _len(_sub(cage.verts[i], pos)))
    except Exception:
        _restore(cage, snap)
        raise


def collapse_face(cage: Cage, fi: int) -> int:
    """Merge all the points of a face into one at its centre."""
    f = cage.faces[fi]
    snap = _snapshot(cage)
    try:
        c = cage.face_centroid(fi)
        keep = f[0]
        cage.verts[keep] = c
        _replace_points(cage, {x: keep for x in f[1:]})
        if not cage.faces:
            raise ValueError(_T("A cage needs at least one face"))
        return min(range(len(cage.verts)), key=lambda i: _len(_sub(cage.verts[i], c)))
    except Exception:
        _restore(cage, snap)
        raise


def weld(cage: Cage, v: int, distance: float) -> int:
    """Merge point ``v`` with every point within ``distance`` of it (at their
    average). Returns how many points were merged into it."""
    if distance <= 0:
        raise ValueError(_T("The distance must be above zero"))
    p = cage.verts[v]
    near = [i for i, q in enumerate(cage.verts) if i != v and _len(_sub(q, p)) <= distance]
    if not near:
        raise ValueError(_T("No other point lies within that distance"))
    group = [v] + near
    snap = _snapshot(cage)
    try:
        c = tuple(sum(cage.verts[i][k] for i in group) / len(group) for k in range(3))
        cage.verts[v] = c
        _replace_points(cage, {i: v for i in near})
        if not cage.faces:
            raise ValueError(_T("A cage needs at least one face"))
        return len(near)
    except Exception:
        _restore(cage, snap)
        raise


# ---- Dissolve ---------------------------------------------------------------------------
def dissolve_edge(cage: Cage, a: int, b: int) -> int:
    """Remove an edge and join the two faces that shared it into one. Returns
    the index of the joined face."""
    k = ekey(a, b)
    fl = cage.edge_faces().get(k)
    if fl is None:
        raise ValueError(_T("That is not an edge of the cage"))
    if len(fl) != 2:
        raise ValueError(_T("Dissolve needs an edge between two faces"))
    f1, f2 = (cage.faces[i] for i in fl)
    # walk f1 from b round to a, then f2 from a round to b (windings agree)
    i = next(t for t in range(len(f1)) if (f1[t], f1[(t + 1) % len(f1)]) in ((a, b), (b, a)))
    x, y = f1[i], f1[(i + 1) % len(f1)]
    ring1 = [f1[(i + 1 + t) % len(f1)] for t in range(len(f1))]       # y ... x
    j = next(t for t in range(len(f2)) if f2[t] == y and f2[(t + 1) % len(f2)] == x)
    ring2 = [f2[(j + 1 + t) % len(f2)] for t in range(len(f2))]       # x ... y
    joined = ring1[:-1] + ring2[:-1]
    if len(set(joined)) != len(joined):
        raise ValueError(_T("Dissolving that edge would pinch the face"))
    keep, drop = fl
    snap = _snapshot(cage)
    cage.faces[keep] = tuple(joined)
    cage.remove_faces([drop])
    cage.creases.pop(k, None)
    if keep > drop:
        keep -= 1
    return keep


def dissolve_vertex(cage: Cage, v: int) -> int | None:
    """Remove a point. A point with two edges just disappears from its faces;
    an interior point with more joins all the faces round it into one. Returns the new face (or None)."""
    users = [fi for fi, f in enumerate(cage.faces) if v in f]
    if not users:
        raise ValueError(_T("That point belongs to no face"))
    nb = set()
    for fi in users:
        f = cage.faces[fi]
        i = f.index(v)
        nb.update((f[i - 1], f[(i + 1) % len(f)]))
    snap = _snapshot(cage)
    try:
        if len(nb) <= 2:
            for fi in users:
                cage.faces[fi] = tuple(x for x in cage.faces[fi] if x != v)
                if len(cage.faces[fi]) < 3:
                    raise ValueError(_T("Dissolving that point would leave a face with two sides"))
            cage.creases = {e: s for e, s in cage.creases.items() if v not in e}
            _drop_unused(cage)
            return None
        fn = fan(cage, v)
        if fn is None:
            raise ValueError(_T("Dissolve a point inside the surface (not on a border)"))
        faces, nbrs = fn
        outline = []
        for t in reversed(range(len(faces))):
            f = cage.faces[faces[t]]
            i = f.index(v)
            part = [f[(i + 1 + s) % len(f)] for s in range(len(f) - 1)]      # next ... prev
            outline.extend(part[:-1])
        if len(set(outline)) != len(outline) or len(outline) < 3:
            raise ValueError(_T("Dissolving that point would pinch the face"))
        keep = faces[0]
        cage.faces[keep] = tuple(outline)
        cage.remove_faces(faces[1:])
        cage.creases = {e: s for e, s in cage.creases.items() if v not in e}
        _drop_unused(cage)
        return 0
    except Exception:
        _restore(cage, snap)
        raise


# ---- Slide ------------------------------------------------------------------------------
def slide_loop(cage: Cage, loop: Sequence[tuple[int, int]], t: float) -> int:
    """Slide an edge loop sideways: every point moves the fraction ``t`` of the
    way towards its neighbour on one side (negative ``t``: the other side).
    ``loop`` is a list of ``(a, b)`` edges (see ``ops.edge_loop``); its first
    edge sets which side is positive. Returns how many points moved."""
    if not -1.0 < t < 1.0:
        raise ValueError(_T("Slide by a fraction between -1 and 1"))
    pts: list[int] = []
    for a, b in loop:
        for x in (a, b):
            if x not in pts:
                pts.append(x)
    # direction along the loop, from the first edge
    first = loop[0]
    towards = {}
    ordered = [first[0], first[1]]
    nbrs_in_loop: dict[int, list[int]] = {}
    for a, b in loop:
        nbrs_in_loop.setdefault(a, []).append(b)
        nbrs_in_loop.setdefault(b, []).append(a)
    while True:
        nxt = [w for w in nbrs_in_loop[ordered[-1]] if w != ordered[-2]]
        if not nxt or nxt[0] in ordered:
            break
        ordered.append(nxt[0])
    while True:
        nxt = [w for w in nbrs_in_loop[ordered[0]] if w != ordered[1]]
        if not nxt or nxt[0] in ordered:
            break
        ordered.insert(0, nxt[0])
    moves = {}
    for i, v in enumerate(ordered):
        fn = fan(cage, v)
        if fn is None:
            raise ValueError(_T("Slide needs a loop inside the surface, not on a border"))
        faces, nbrs = fn
        if i > 0:
            p = ordered[i - 1]
        elif len(ordered) > 1 and ordered[-1] in nbrs and ordered[1] in nbrs and len(ordered) > 2 \
                and ordered[-1] in nbrs_in_loop[v]:
            p = ordered[-1]
        else:
            p = ordered[1]
        if p not in nbrs:
            raise ValueError(_T("Slide needs a loop inside the surface, not on a border"))
        j = nbrs.index(p)
        left = nbrs[(j + 1) % len(nbrs)]
        right = nbrs[(j - 1) % len(nbrs)]
        if i == 0 and p == ordered[1]:
            left, right = right, left                # walking backwards: the sides swap
        target = left if t >= 0 else right
        moves[v] = _lerp(cage.verts[v], cage.verts[target], abs(t))
    for v, q in moves.items():
        cage.verts[v] = q
    return len(moves)


# ---- Loft and Sweep ---------------------------------------------------------------------
def _newell(pts):
    nx = ny = nz = 0.0
    for i, p in enumerate(pts):
        q = pts[(i + 1) % len(pts)]
        nx += (p[1] - q[1]) * (p[2] + q[2])
        ny += (p[2] - q[2]) * (p[0] + q[0])
        nz += (p[0] - q[0]) * (p[1] + q[1])
    return (nx, ny, nz)


def _centroid(pts):
    n = len(pts)
    return tuple(sum(p[k] for p in pts) / n for k in range(3))


def _grow_ring(pts, m):
    """The closed polygon ``pts`` with extra points on its longest sides until
    it has ``m`` points; every original point is kept."""
    pts = list(pts)
    if len(pts) >= m:
        return pts
    # number of pieces each side is cut into, shared out by length
    n = len(pts)
    lens = [_len(_sub(pts[(i + 1) % n], pts[i])) for i in range(n)]
    pieces = [1] * n
    for _ in range(m - n):
        i = max(range(n), key=lambda k: lens[k] / pieces[k])
        pieces[i] += 1
    out = []
    for i in range(n):
        a, b = pts[i], pts[(i + 1) % n]
        for s in range(pieces[i]):
            out.append(_lerp(a, b, s / pieces[i]))
    return out


def _align(prev, ring, twist=0):
    """``ring`` turned (and flipped if need be) to sit over ``prev`` with the
    shortest total distance, then shifted by ``twist`` points."""
    n = len(ring)
    best, best_c = None, None
    for cand in (ring, list(reversed(ring))):
        for s in range(n):
            c = sum(_len(_sub(prev[i], cand[(i + s) % n])) for i in range(n))
            if best_c is None or c < best_c - 1e-12:
                best, best_c = [cand[(i + s) % n] for i in range(n)], c
    t = int(twist) % n
    return best[t:] + best[:t]


def _catmull(p0, p1, p2, p3, u):
    u2, u3 = u * u, u * u * u
    return tuple(0.5 * ((2 * p1[k]) + (-p0[k] + p2[k]) * u + (2 * p0[k] - 5 * p1[k] + 4 * p2[k] - p3[k]) * u2
                        + (-p0[k] + 3 * p1[k] - 3 * p2[k] + p3[k]) * u3) for k in range(3))


def _key(p):
    return (round(p[0], 9), round(p[1], 9), round(p[2], 9))


def _make_surface(cage: Cage, rings, closed_ends: bool, closed_path: bool = False,
                  reuse=None, caps=None, first=None) -> int:
    """Quads between consecutive rings (lists of points, equal size), new points
    added to the cage (``reuse`` maps a position to an existing point to use
    instead, so the surface is welded to it); optional caps (``caps`` = start, end).
    Returns the number of faces added."""
    def vid(p):
        if reuse:
            i = reuse.get(_key(p))
            if i is not None:
                return i
        return cage._new_vert(p)
    ids = [[vid(p) for p in r] for r in rings]
    if first is not None:                       # the first ring IS these existing points
        ids[0] = list(first)
    n = len(rings[0])
    added = 0
    last = len(ids) if closed_path else len(ids) - 1
    for k in range(last):
        a, b = ids[k], ids[(k + 1) % len(ids)]
        for j in range(n):
            j2 = (j + 1) % n
            cage.faces.append((a[j], a[j2], b[j2], b[j]))
            cage.colors.append(None)
            added += 1
    if not closed_path:
        cs, ce = caps if caps is not None else (closed_ends, closed_ends)
        for r, on in ((ids[0], cs), (ids[-1], ce)):
            if on:
                cage.faces.append(tuple(r))
                cage.colors.append(None)
                added += 1
    return added


def loft(cage: Cage, sections: Sequence[Sequence[int]], segments: int = 1,
         closed_ends: bool = True, twist: int = 0, faces=None) -> int:
    """A new surface through several closed sections, in the order given:
    ``sections`` are loops of points (a face's corners, or a closed edge loop).
    Rings with fewer points get extra ones, each ring is lined up with the one
    before it, and ``segments`` quads run between two sections (the rings in
    between follow a smooth curve through the sections when there are three or
    more). The sections themselves are left alone. Returns the faces added."""
    if len(sections) < 2:
        raise ValueError(_T("Loft needs at least two sections"))
    segments = int(round(segments))
    if segments < 1:
        raise ValueError(_T("Segments between sections must be at least 1"))
    loops = [[cage.verts[v] for v in s] for s in sections]
    if any(len(p) < 3 for p in loops):
        raise ValueError(_T("A section needs at least 3 points"))
    m = max(len(p) for p in loops)
    snap = _snapshot(cage)
    try:
        rings = [_grow_ring(loops[0], m)]
        for lp in loops[1:]:
            rings.append(_align(rings[-1], _grow_ring(lp, m), twist if len(rings) == 1 else 0))
        # the first ring keeps its own order; later ones are lined up on it
        full = []
        k = len(rings)
        for i in range(k - 1):
            full.append(rings[i])
            for s in range(1, segments):
                u = s / segments
                if k == 2:
                    full.append([_lerp(a, b, u) for a, b in zip(rings[0], rings[1])])
                else:
                    r0, r1 = rings[i], rings[i + 1]
                    rm = rings[i - 1] if i > 0 else None
                    rp = rings[i + 2] if i + 2 < k else None
                    full.append([
                        _catmull(rm[j] if rm else _sub(_mul(r0[j], 2), r1[j]), r0[j], r1[j],
                                 rp[j] if rp else _sub(_mul(r1[j], 2), r0[j]), u)
                        for j in range(m)])
        full.append(rings[-1])
        reuse, caps, drop = None, None, []
        if faces is not None and any(f is not None for f in faces):
            reuse = {}
            ef = cage.edge_faces()
            last = len(sections) - 1
            for i, f in enumerate(faces):
                if f is None:
                    continue
                loop = cage.faces[f]
                for v in loop:
                    reuse[_key(cage.verts[v])] = v
                attached = any(len(ef.get(ekey(loop[q], loop[(q + 1) % len(loop)]), ())) > 1
                               for q in range(len(loop)))
                if i not in (0, last) or attached or not closed_ends:
                    drop.append(f)
            caps = (closed_ends and faces[0] is None, closed_ends and faces[-1] is None)
        added = _make_surface(cage, full, closed_ends, reuse=reuse, caps=caps)
        if drop:
            cage.remove_faces(drop)
            added -= 0
        cage.orient()
        return added
    except Exception:
        _restore(cage, snap)
        raise


def _rmf_rotations(points, tangents):
    """Rotation-minimising frames along a path (the double-reflection method of
    Wang, Juttler, Zheng and Liu, 2008): for each path point the 3x3 rotation
    that carries the first tangent onto that point's tangent with the least twist."""
    def reflect_mat(n):
        return [[(1.0 if i == j else 0.0) - 2.0 * n[i] * n[j] for j in range(3)] for i in range(3)]

    def mul(A, B):
        return [[sum(A[i][k] * B[k][j] for k in range(3)) for j in range(3)] for i in range(3)]

    R = [[1.0, 0, 0], [0, 1.0, 0], [0, 0, 1.0]]
    out = [R]
    for i in range(len(points) - 1):
        chord = _sub(points[i + 1], points[i])
        if _dot(chord, chord) < 1e-18:
            out.append(R)
            continue
        H1 = reflect_mat(_unit(chord))
        t_l = _apply(H1, tangents[i])
        v2 = _sub(tangents[i + 1], t_l)
        R = mul(H1, R)
        if _dot(v2, v2) > 1e-18:
            R = mul(reflect_mat(_unit(v2)), R)
        out.append(R)
    return out


def _apply(M, v):
    return tuple(sum(M[i][k] * v[k] for k in range(3)) for i in range(3))


def _rot_axis_matrix(axis, ang):
    k = _unit(axis)
    c, s = math.cos(ang), math.sin(ang)
    x, y, z = k
    return [[c + x * x * (1 - c), x * y * (1 - c) - z * s, x * z * (1 - c) + y * s],
            [y * x * (1 - c) + z * s, c + y * y * (1 - c), y * z * (1 - c) - x * s],
            [z * x * (1 - c) - y * s, z * y * (1 - c) + x * s, c + z * z * (1 - c)]]


def chain_from_edges(edges) -> tuple[list[int], bool]:
    """Order a set of edges forming one path: ``(points, closed)``."""
    adj: dict[int, list[int]] = {}
    for a, b in edges:
        adj.setdefault(a, []).append(b)
        adj.setdefault(b, []).append(a)
    if not adj or any(len(x) > 2 for x in adj.values()):
        raise ValueError(_T("The path must be one chain of edges, without branches"))
    ends = [v for v, x in adj.items() if len(x) == 1]
    closed = not ends
    start = ends[0] if ends else next(iter(adj))
    path, seen = [start], {start}
    while True:
        nxt = [w for w in adj[path[-1]] if w not in seen]
        if not nxt:
            break
        path.append(nxt[0])
        seen.add(nxt[0])
    if len(path) != len(adj):
        raise ValueError(_T("The path must be one chain of edges, without branches"))
    return path, closed


def sweep(cage: Cage, profile: Sequence[int], path: Sequence[int], closed_path: bool = False,
          closed_ends: bool = True, twist_deg: float = 0.0, face=None) -> int:
    """Carry a closed profile along a path of points: a copy of the profile
    rides each path point, turned to follow the path (with the least possible
    twist, plus ``twist_deg`` spread along it), and quads join them. The profile
    keeps its offset from the path's first point. At bends each copy stands
    on the bisector, so the tube mitres. Returns the faces added."""
    if len(path) < 2:
        raise ValueError(_T("The path needs at least two points"))
    if len(profile) < 3:
        raise ValueError(_T("The profile needs at least 3 points"))
    P = [cage.verts[v] for v in path]
    prof = [cage.verts[v] for v in profile]
    n = len(P)
    seg = [_unit(_sub(P[(i + 1) % n], P[i])) for i in range(n if closed_path else n - 1)]
    if any(_len(s) == 0 for s in seg):
        raise ValueError(_T("The path has two points in the same place"))
    tans = []
    for i in range(n):
        if closed_path:
            t = _add(seg[i - 1], seg[i])
        elif i == 0:
            t = seg[0]
        elif i == n - 1:
            t = seg[-1]
        else:
            t = _add(seg[i - 1], seg[i])
        tans.append(_unit(t) if _len(t) > 1e-9 else seg[min(i, len(seg) - 1)])
    rots = _rmf_rotations(P, tans)
    rings = []
    total = math.radians(twist_deg)
    for i in range(n):
        ang = total * (i / (n - 1 if not closed_path else n))
        T = rots[i]
        if abs(ang) > 1e-12:
            twist_m = _rot_axis_matrix(tans[i], ang)
            ring = [_add(_apply(twist_m, _apply(T, _sub(q, P[0]))), P[i]) for q in prof]
        else:
            ring = [_add(_apply(T, _sub(q, P[0])), P[i]) for q in prof]
        interior = closed_path or 0 < i < n - 1
        if interior:                                  # keep the tube's width at a mitred bend
            a, b = seg[i - 1], seg[i % len(seg)]
            m = _cross(a, b)
            c_half = _dot(tans[i], b)
            if _len(m) > 1e-9 and c_half > 0.25:
                w = _unit(_cross(_unit(m), tans[i]))
                k = 1.0 / c_half - 1.0
                ring = [_add(q, _mul(w, _dot(_sub(q, P[i]), w) * k)) for q in ring]
        rings.append(ring)
    snap = _snapshot(cage)
    try:
        if face is None:
            added = _make_surface(cage, rings, closed_ends, closed_path)
        else:
            # The profile is a face of the piece: the tube grows out of it and is welded
            # to its points (the face goes when it is inside the piece, so it is not cut in two).
            ef = cage.edge_faces()
            loop = cage.faces[face]
            attached = any(len(ef.get(ekey(loop[q], loop[(q + 1) % len(loop)]), ())) > 1
                           for q in range(len(loop)))
            caps = (False, bool(closed_ends) and not closed_path)
            added = _make_surface(cage, rings, closed_ends, closed_path,
                                  caps=caps, first=list(profile))
            if attached or not closed_ends:
                cage.remove_faces([face])
        cage.orient()
        return added
    except Exception:
        _restore(cage, snap)
        raise


def duplicate_faces(cage: Cage, faces) -> tuple[list[int], list[int]]:
    """Add a detached copy of ``faces`` (with their own new points, colours and
    creases). Returns the new point numbers and the new face numbers."""
    faces = sorted(set(faces))
    vmap: dict[int, int] = {}
    new_faces = []
    for fi in faces:
        loop = []
        for v in cage.faces[fi]:
            if v not in vmap:
                vmap[v] = cage._new_vert(cage.verts[v])
            loop.append(vmap[v])
        cage.faces.append(tuple(loop))
        cage.colors.append(cage.colors[fi] if fi < len(cage.colors) else None)
        new_faces.append(len(cage.faces) - 1)
    for (a, b), sharp in list(cage.creases.items()):
        if a in vmap and b in vmap:
            cage.creases[(min(vmap[a], vmap[b]), max(vmap[a], vmap[b]))] = sharp
    for v, sharp in list(cage.vcreases.items()):
        if v in vmap:
            cage.vcreases[vmap[v]] = sharp
    return list(vmap.values()), new_faces
