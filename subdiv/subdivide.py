# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 IngeTrazo contributors.
"""Catmull-Clark subdivision surfaces (NumPy; a plain-Python reference is kept for tests).

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
sharpness: an edge of sharpness ``s`` is treated as sharp for ``s`` subdivision
levels, then relaxes into the smooth surface; a fractional part blends the sharp
and smooth rules (DeRose, Kass and Truong, 1998). An optional ``{vertex: s}``
dict makes a point a corner of that sharpness. A vertex with
two sharp edges follows the crease rule, with three or more it is a corner.
"""
from __future__ import annotations

from typing import NamedTuple

import numpy as np

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


def _step_py(verts, faces, creases, vcreases=None):
    """One Catmull-Clark step, plain Python: the reference the NumPy version is tested against.

    Returns (verts, faces, creases, edge_idx, parents): ``edge_idx`` maps each
    input edge to the index of its new edge point (so its two children are
    (a, m) and (m, b)); ``parents[i]`` is the input face output face i came from.
    """
    creases = creases or {}
    vcreases = vcreases or {}
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
        mid = _avg([verts[a], verts[b]])
        w = min(max(creases.get((a, b), 0.0), 0.0), 1.0)
        if len(fl) == 2:
            smooth = _avg([verts[a], verts[b], face_pts[fl[0]], face_pts[fl[1]]])
            edge_pts[(a, b)] = _lin(smooth, 1.0 - w, mid, w)
        else:  # boundary or non-manifold: plain midpoint
            edge_pts[(a, b)] = mid

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
        n = len(edges)
        f_avg = _avg([face_pts[fi] for fi in vert_faces[vi]])
        r_avg = _avg([_avg([verts[e[0]], verts[e[1]]]) for e in edges])
        smooth = (
            (f_avg[0] + 2 * r_avg[0] + (n - 3) * p[0]) / n,
            (f_avg[1] + 2 * r_avg[1] + (n - 3) * p[1]) / n,
            (f_avg[2] + 2 * r_avg[2] + (n - 3) * p[2]) / n,
        )
        ws = [1.0 if len(edge_faces[e]) == 1 else min(creases[e], 1.0) for e in sharp]
        if not sharp or (len(sharp) == 1 and len(edge_faces[sharp[0]]) == 2):
            res = smooth
        elif len(sharp) == 2:  # boundary or crease vertex: (6P + A + B) / 8
            others = [e[0] if e[1] == vi else e[1] for e in sharp]
            nb = _lin(verts[others[0]], 1.0, verts[others[1]], 1.0)
            sg = sum(ws) / 2.0
            res = _lin(smooth, 1.0 - sg, _lin(p, 6 / 8, nb, 1 / 8), sg)
        else:  # corner
            sg = 1.0 if len(sharp) == 1 else sum(ws) / len(ws)
            res = _lin(smooth, 1.0 - sg, p, sg)
        vs = min(max(vcreases.get(vi, 0.0), 0.0), 1.0)
        if vs > 0:
            res = _lin(res, 1.0 - vs, p, vs)
        new_verts.append(res)

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
    out_vc = {v: s - 1 for v, s in vcreases.items() if s > 1}
    return out_verts, out_faces, out_creases, edge_idx, parents, out_vc


def _flatten(faces):
    """Corner arrays of a polygon list: vertex, face id, and the face's first
    corner (so the next/previous corner of each is a cheap lookup)."""
    sizes = np.fromiter((len(f) for f in faces), dtype=np.int64, count=len(faces))
    start = np.zeros(len(faces), dtype=np.int64)
    np.cumsum(sizes[:-1], out=start[1:])
    flat = np.fromiter((x for f in faces for x in f), dtype=np.int64, count=int(sizes.sum()))
    fid = np.repeat(np.arange(len(faces), dtype=np.int64), sizes)
    return flat, fid, sizes, start


def _step_np(V, flat, fid, sizes, start, creases, vcreases=None):
    """One Catmull-Clark step on arrays. Same rules, same output order as
    :func:`_step_py`. Returns (V2, flat2, fid2, creases2, ekeys, parents) where
    ``ekeys`` is the (E, 2) array of input edges, in first-seen order: input
    edge ``i`` gets output point ``len(V) + len(faces) + i``."""
    nV, nF = len(V), len(sizes)
    nC = len(flat)
    idx = np.arange(nC, dtype=np.int64)
    local = idx - start[fid]
    nxt = flat[start[fid] + (local + 1) % sizes[fid]]
    prv = flat[start[fid] + (local - 1) % sizes[fid]]

    fsum = np.zeros((nF, 3))
    np.add.at(fsum, fid, V[flat])
    FP = fsum / sizes[:, None]

    lo, hi = np.minimum(flat, nxt), np.maximum(flat, nxt)
    key = lo * nV + hi
    uniq, first, inv, cnt = np.unique(key, return_index=True, return_inverse=True, return_counts=True)
    order = np.argsort(first, kind="stable")             # first-seen order, like the dict
    rank = np.empty_like(order)
    rank[order] = np.arange(len(order))
    e_of = rank[inv]                                      # edge id of each corner's edge
    ecount = cnt[order]
    ekey_ = uniq[order]
    ea, eb = ekey_ // nV, ekey_ % nV
    nE = len(ekey_)

    cr = np.zeros(nE)
    if creases:
        pos = {int(k): i for i, k in enumerate(ekey_.tolist())}
        for (a, b), sh in creases.items():
            i = pos.get(a * nV + b)
            if i is not None:
                cr[i] = sh

    fp_edge = np.zeros((nE, 3))
    np.add.at(fp_edge, e_of, FP[fid])                     # sum of the face points around each edge
    mid = (V[ea] + V[eb]) / 2.0
    w_e = np.clip(cr, 0.0, 1.0)
    smooth_pt = (V[ea] + V[eb] + fp_edge) / 4.0
    EP = np.where((ecount == 2)[:, None], smooth_pt * (1.0 - w_e)[:, None] + mid * w_e[:, None], mid)

    # vertex rules
    n_edges = np.bincount(ea, minlength=nV) + np.bincount(eb, minlength=nV)
    n_corners = np.bincount(flat, minlength=nV)
    nonman_e = ecount > 2
    nonman_v = (np.bincount(ea[nonman_e], minlength=nV) + np.bincount(eb[nonman_e], minlength=nV)) > 0
    sharp_e = (ecount == 1) | (cr > 0)
    sharp_e &= ~nonman_e
    n_sharp = np.bincount(ea[sharp_e], minlength=nV) + np.bincount(eb[sharp_e], minlength=nV)
    bnd_e = ecount == 1
    n_bnd = np.bincount(ea[bnd_e], minlength=nV) + np.bincount(eb[bnd_e], minlength=nV)

    fsum_v = np.zeros((nV, 3))
    np.add.at(fsum_v, flat, FP[fid])
    rsum = np.zeros((nV, 3))
    np.add.at(rsum, ea, mid)
    np.add.at(rsum, eb, mid)
    nb_sum = np.zeros((nV, 3))
    np.add.at(nb_sum, ea[sharp_e], V[eb[sharp_e]])
    np.add.at(nb_sum, eb[sharp_e], V[ea[sharp_e]])

    newV = V.copy()
    free = (n_edges > 0) & ~nonman_v
    n = np.maximum(n_edges, 1)[:, None]
    f_avg = fsum_v / np.maximum(n_corners, 1)[:, None]
    r_avg = rsum / n
    sm = (f_avg + 2.0 * r_avg + (n - 3) * V) / n
    wsum = np.zeros(nV)                                   # sharpness of each sharp edge, 1 on borders
    ws_e = np.where(bnd_e, 1.0, np.minimum(cr, 1.0))
    np.add.at(wsum, ea[sharp_e], ws_e[sharp_e])
    np.add.at(wsum, eb[sharp_e], ws_e[sharp_e])
    smooth_v = free & ((n_sharp == 0) | ((n_sharp == 1) & (n_bnd == 0)))
    crease_v = free & (n_sharp == 2)
    corner_v = free & (n_sharp >= 3) | (free & (n_sharp == 1) & (n_bnd == 1))
    sg = np.where(n_sharp == 1, 1.0, wsum / np.maximum(n_sharp, 1))[:, None]
    cv = 0.75 * V + 0.125 * nb_sum
    newV[smooth_v] = sm[smooth_v]
    newV[crease_v] = (sm * (1.0 - sg) + cv * sg)[crease_v]
    newV[corner_v] = (sm * (1.0 - sg) + V * sg)[corner_v]
    if vcreases:
        vs = np.zeros(nV)
        for v, sh in vcreases.items():
            if 0 <= v < nV:
                vs[v] = min(max(sh, 0.0), 1.0)
        m = (vs > 0) & free
        newV[m] = newV[m] * (1.0 - vs[m])[:, None] + V[m] * vs[m][:, None]

    V2 = np.concatenate([newV, FP, EP])
    base_f, base_e = nV, nV + nF
    flat2 = np.empty((nC, 4), dtype=np.int64)
    flat2[:, 0] = flat
    flat2[:, 1] = base_e + e_of
    flat2[:, 2] = base_f + fid
    prev_corner = start[fid] + (local - 1) % sizes[fid]
    flat2[:, 3] = base_e + e_of[prev_corner]

    creases2 = {}
    if creases:
        pos_e = {int(k): i for i, k in enumerate(ekey_.tolist())}
        for (a, b), sh in creases.items():
            i = pos_e.get(a * nV + b)
            if sh > 1 and i is not None:
                m = base_e + i
                creases2[_edge_key(a, m)] = sh - 1
                creases2[_edge_key(m, b)] = sh - 1
    vc2 = {v: sh - 1 for v, sh in (vcreases or {}).items() if sh > 1}
    return V2, flat2, fid, creases2, np.stack([ea, eb], axis=1), fid, vc2


def _arrays(verts, faces):
    V = np.asarray(verts, dtype=float).reshape(-1, 3)
    return V, _flatten(faces)


def _quads(flat2):
    return flat2.reshape(-1, 4)


def _to_lists(V, F4):
    return list(map(tuple, V.tolist())), list(map(tuple, F4.tolist()))


def _step(verts, faces, creases, vcreases=None):
    """One Catmull-Clark step on lists (same contract as :func:`_step_py`)."""
    if not faces:
        return list(verts), [], {}, {}, [], {}
    V, (flat, fid, sizes, start) = _arrays(verts, faces)
    V2, F4, fid2, c2, ek, parents, vc2 = _step_np(V, flat, fid, sizes, start, creases or {}, vcreases or {})
    vl, fl = _to_lists(V2, F4)
    base = len(verts) + len(faces)
    eidx = {(int(a), int(b)): base + i for i, (a, b) in enumerate(ek.tolist())}
    return vl, fl, c2, eidx, parents.tolist(), vc2


def subdivide_once(verts: list[Vec], faces: list[Face]) -> tuple[list[Vec], list[Face]]:
    """Apply one Catmull-Clark step. Returns a new (verts, faces), all quads."""
    v, f = _step(verts, faces, None)[:2]
    return v, f


def subdivide(
    verts: list[Vec],
    faces: list[Face],
    levels: int = 1,
    creases: dict[tuple[int, int], float] | None = None,
    vcreases: dict[int, float] | None = None,
) -> tuple[list[Vec], list[Face]]:
    """Apply ``levels`` Catmull-Clark steps (0 returns a copy of the cage).

    ``creases`` maps an edge ``(a, b)`` to its sharpness (levels it stays sharp).
    """
    if levels < 0:
        raise ValueError("levels must be >= 0")
    if levels == 0 or not faces:
        return list(verts), [tuple(x) for x in faces]
    c = {_edge_key(*e): s for e, s in (creases or {}).items() if s > 0}
    vc = {v: s for v, s in (vcreases or {}).items() if s > 0}
    V, (flat, fid, sizes, start) = _arrays(verts, faces)
    for _ in range(levels):
        V, F4, fid, c, _ek, _p, vc = _step_np(V, flat, fid, sizes, start, c, vc)
        nF = len(F4)
        flat = F4.reshape(-1)
        sizes = np.full(nF, 4, dtype=np.int64)
        start = np.arange(nF, dtype=np.int64) * 4
        fid = np.repeat(np.arange(nF, dtype=np.int64), 4)
    return _to_lists(V, flat.reshape(-1, 4))


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
    vcreases: dict[int, float] | None = None,
) -> Detailed:
    """Like :func:`subdivide`, and also report for every output face which cage
    face it descends from, and which output edges lie on the edges of the mesh
    at ``line_level`` (0 = the cage's own edges, which then read as curved
    panel lines on the smooth surface)."""
    if levels < 0:
        raise ValueError("levels must be >= 0")
    v, f = list(verts), [tuple(x) for x in faces]
    c = {_edge_key(*e): s for e, s in (creases or {}).items() if s > 0}
    vc = {v: s for v, s in (vcreases or {}).items() if s > 0}

    def all_edges(fs):
        return {_edge_key(x, fx[(i + 1) % len(fx)]) for fx in fs for i, x in enumerate(fx)}

    source = list(range(len(f)))
    lines = all_edges(f) if line_level <= 0 else None
    for step in range(levels):
        v, f, c, eidx, parents, vc = _step(v, f, c, vc)
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
