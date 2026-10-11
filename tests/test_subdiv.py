# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 IngeTrazo contributors.
from subdiv.subdivide import subdivide

CUBE_V = [(x, y, z) for z in (-1.0, 1.0) for y in (-1.0, 1.0) for x in (-1.0, 1.0)]
CUBE_F = [(0, 2, 3, 1), (4, 5, 7, 6), (0, 1, 5, 4), (2, 6, 7, 3), (0, 4, 6, 2), (1, 3, 7, 5)]


def _edges(faces):
    s = set()
    for f in faces:
        for i, a in enumerate(f):
            b = f[(i + 1) % len(f)]
            s.add((min(a, b), max(a, b)))
    return s


def test_level0_is_copy():
    v, f = subdivide(CUBE_V, CUBE_F, 0)
    assert v == CUBE_V and f == [tuple(x) for x in CUBE_F]


def test_cube_counts_and_euler():
    v, f = subdivide(CUBE_V, CUBE_F, 1)
    assert (len(v), len(f)) == (26, 24)
    assert len(v) - len(_edges(f)) + len(f) == 2
    v2, f2 = subdivide(CUBE_V, CUBE_F, 2)
    assert len(f2) == 96


def test_cube_shrinks_and_stays_symmetric():
    v, _ = subdivide(CUBE_V, CUBE_F, 2)
    assert max(abs(c) for p in v for c in p) < 1.0
    cx = sum(p[0] for p in v) / len(v)
    assert abs(cx) < 1e-12


def test_planar_grid_stays_planar_and_keeps_boundary():
    gv = [(float(x), float(y), 0.0) for y in range(3) for x in range(3)]
    gf = [(0, 1, 4, 3), (1, 2, 5, 4), (3, 4, 7, 6), (4, 5, 8, 7)]
    v, f = subdivide(gv, gf, 2)
    assert all(abs(p[2]) < 1e-12 for p in v)
    xs = [p[0] for p in v]
    assert min(xs) == 0.0 and max(xs) == 2.0


def test_triangle_and_ngon_become_quads():
    v, f = subdivide([(0, 0, 0), (1, 0, 0), (0, 1, 0)], [(0, 1, 2)], 1)
    assert len(f) == 3 and all(len(q) == 4 for q in f)


def test_detailed_reports_sources_and_lines():
    from subdiv.subdivide import subdivide_detailed
    d = subdivide_detailed(CUBE_V, CUBE_F, 2)
    assert len(d.source) == len(d.faces) == 96
    assert sorted(set(d.source)) == list(range(6)) and d.source.count(0) == 16
    assert len(d.lines) == 12 * 4              # cage edges, each cut in 4
    mid = subdivide_detailed(CUBE_V, CUBE_F, 2, line_level=1)
    assert len(mid.lines) == 48 * 2
