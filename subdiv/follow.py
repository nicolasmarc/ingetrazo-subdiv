# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 IngeTrazo contributors.
"""Keep a control cage in step with the group that carries it.

The cage lives in ``group.ext`` while the group's mesh holds the smooth
surface. When the user moves, rotates or scales the group, only the mesh
moves, so the cage has to be carried along. At build time we remember four
well-spread vertices of the mesh (their order in the mesh and their
positions) plus the mesh centroid. Later, the same four vertices tell us
where the surface went: the affine map taking the old positions to the new
ones is applied to the cage. The fit is only trusted when the four points
kept their mutual distances (a rigid motion, a uniform scale, or a mirror)
and the centroid lands where it should; otherwise we fall back to a plain
translation of the centroid, and when even that shows nothing we leave the
cage alone.

Pure Python, no Qt: positions are ``(x, y, z)`` tuples.
"""
from __future__ import annotations

import math
from typing import Sequence

Vec = tuple[float, float, float]
Matrix = tuple[Vec, Vec, Vec]          # rows
Affine = tuple[Matrix, Vec]            # p' = M p + t

IDENTITY: Matrix = ((1.0, 0.0, 0.0), (0.0, 1.0, 0.0), (0.0, 0.0, 1.0))


# ---- small helpers ---------------------------------------------------------------------
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


def centroid(points: Sequence[Vec]) -> Vec:
    n = len(points)
    return (sum(p[0] for p in points) / n, sum(p[1] for p in points) / n,
            sum(p[2] for p in points) / n)


def mat_vec(m: Matrix, v: Vec) -> Vec:
    return (_dot(m[0], v), _dot(m[1], v), _dot(m[2], v))


def inverse(m: Matrix) -> Matrix | None:
    (a, b, c), (d, e, f), (g, h, i) = m
    det = a * (e * i - f * h) - b * (d * i - f * g) + c * (d * h - e * g)
    if abs(det) < 1e-14:
        return None
    k = 1.0 / det
    return (
        ((e * i - f * h) * k, (c * h - b * i) * k, (b * f - c * e) * k),
        ((f * g - d * i) * k, (a * i - c * g) * k, (c * d - a * f) * k),
        ((d * h - e * g) * k, (b * g - a * h) * k, (a * e - b * d) * k),
    )


def transpose(m: Matrix) -> Matrix:
    return ((m[0][0], m[1][0], m[2][0]), (m[0][1], m[1][1], m[2][1]),
            (m[0][2], m[1][2], m[2][2]))


def apply_point(aff: Affine, p: Vec) -> Vec:
    return _add(mat_vec(aff[0], p), aff[1])


def apply_normal(aff: Affine, n: Vec) -> Vec:
    """A plane normal through the map (inverse transpose), re-normalised."""
    inv = inverse(aff[0])
    if inv is None:
        return n
    out = mat_vec(transpose(inv), n)
    ln = _len(out)
    return n if ln < 1e-12 else _mul(out, 1.0 / ln)


# ---- choosing and fitting reference points ---------------------------------------------
def spread_indices(points: Sequence[Vec]) -> list[int]:
    """Up to four indices of well-spread points: a start, the farthest from
    it, the farthest from that line, the farthest from that plane."""
    n = len(points)
    if n < 4:
        return list(range(n))
    i0 = 0
    i1 = max(range(n), key=lambda i: _len(_sub(points[i], points[i0])))
    a = _sub(points[i1], points[i0])
    i2 = max(range(n), key=lambda i: _len(_cross(a, _sub(points[i], points[i0]))))
    nrm = _cross(a, _sub(points[i2], points[i0]))
    i3 = max(range(n), key=lambda i: abs(_dot(nrm, _sub(points[i], points[i0]))))
    return [i0, i1, i2, i3]


def _complete(pts: Sequence[Vec]) -> list[Vec]:
    """Four points from three or four: a flat set gets a fourth point lifted
    along its normal, so the affine map is still fully determined."""
    pts = list(pts)
    if len(pts) == 3:
        n = _cross(_sub(pts[1], pts[0]), _sub(pts[2], pts[0]))
        ln = _len(n)
        if ln < 1e-14:
            return pts
        pts.append(_add(pts[0], _mul(n, _len(_sub(pts[1], pts[0])) / ln)))
    return pts


def make_ref(positions: Sequence[Vec]) -> dict | None:
    """What to remember about a mesh so its cage can follow it later."""
    if len(positions) < 3:
        return None
    idx = spread_indices(positions)
    pts = [positions[i] for i in idx]
    size = max(_len(_sub(p, pts[0])) for p in pts) or 1.0
    if len(pts) == 4:
        h = abs(_dot(_cross(_sub(pts[1], pts[0]), _sub(pts[2], pts[0])), _sub(pts[3], pts[0])))
        base = _len(_cross(_sub(pts[1], pts[0]), _sub(pts[2], pts[0]))) or 1.0
        if h / base < 1e-3 * size:                       # (nearly) flat: three are enough
            idx, pts = idx[:3], pts[:3]
    return {"idx": idx, "pts": [list(p) for p in pts], "c": list(centroid(positions))}


def solve_affine(src: Sequence[Vec], dst: Sequence[Vec]) -> Affine | None:
    """The affine map taking ``src`` points to ``dst`` points (3 or 4 each)."""
    s, d = _complete(src), _complete(dst)
    if len(s) < 4 or len(d) < 4:
        return None
    S = [_sub(s[k], s[0]) for k in (1, 2, 3)]            # columns of S
    D = [_sub(d[k], d[0]) for k in (1, 2, 3)]
    Sm = ((S[0][0], S[1][0], S[2][0]), (S[0][1], S[1][1], S[2][1]), (S[0][2], S[1][2], S[2][2]))
    Dm = ((D[0][0], D[1][0], D[2][0]), (D[0][1], D[1][1], D[2][1]), (D[0][2], D[1][2], D[2][2]))
    inv = inverse(Sm)
    if inv is None:
        return None
    M = tuple(tuple(sum(Dm[r][k] * inv[k][c] for k in range(3)) for c in range(3))
              for r in range(3))
    t = _sub(d[0], mat_vec(M, s[0]))
    return (M, t)  # type: ignore[return-value]


def _distances(pts: Sequence[Vec]) -> list[float]:
    return [_len(_sub(pts[i], pts[j])) for i in range(len(pts)) for j in range(i + 1, len(pts))]


def _similar(a: Sequence[Vec], b: Sequence[Vec], tol: float) -> bool:
    """Same shape up to a uniform scale (rigid motion, mirror, scaling)?"""
    da, db = _distances(a), _distances(b)
    if not da or da[0] < 1e-12:
        return False
    s = db[0] / da[0]
    return all(abs(y - s * x) <= tol * max(db) for x, y in zip(da, db))


def _close(a: Vec, b: Vec, tol: float) -> bool:
    return _len(_sub(a, b)) <= tol


def fit(ref: dict, positions: Sequence[Vec]) -> Affine | None:
    """How the mesh moved since ``ref`` was made: None when it did not (or
    when nothing trustworthy can be said), else the affine map to apply to
    the cage. ``positions`` are the mesh's current vertex positions, in the
    mesh's own order."""
    if not ref or not positions:
        return None
    pts = [tuple(p) for p in ref["pts"]]
    c0 = tuple(ref["c"])
    scale = max(_len(_sub(p, pts[0])) for p in pts) or 1.0
    tol = 1e-4 * scale + 1e-9
    cur_c = centroid(positions)
    idx = ref["idx"]
    if max(idx) < len(positions):
        cur = [positions[i] for i in idx]
        if all(_close(a, b, tol) for a, b in zip(pts, cur)) and _close(c0, cur_c, tol):
            return None                                   # nothing moved
        if _similar(pts, cur, 1e-4):
            aff = solve_affine(pts, cur)
            if aff is not None and _close(apply_point(aff, c0), cur_c, 10 * tol):
                return aff
    d = _sub(cur_c, c0)                                  # fallback: a pure translation
    if _len(d) > tol:
        return (IDENTITY, d)
    return None
