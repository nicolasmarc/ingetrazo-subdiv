# SPDX-License-Identifier: GPL-3.0-or-later
"""The NumPy subdivision must give the same surface as the plain-Python reference."""
import random

import pytest

from subdiv import subdivide as sd
from subdiv.edit import Cage


def _ref(verts, faces, levels, creases):
    v, f = list(verts), [tuple(x) for x in faces]
    c = {sd._edge_key(*e): s for e, s in (creases or {}).items() if s > 0}
    for _ in range(levels):
        v, f, c = sd._step_py(v, f, c)[:3]
    return v, f


def _same(a, b):
    (va, fa), (vb, fb) = a, b
    assert fa == fb
    assert len(va) == len(vb)
    for p, q in zip(va, vb):
        assert p == pytest.approx(q, abs=1e-12)


def _cages():
    box = Cage.box((1, 2, 3))
    open_box = Cage.box((1, 1, 1))
    open_box.remove_faces([0])
    ngon = Cage([(0, 0, 0), (1, 0, 0), (1.5, 1, 0), (0.5, 1.7, 0.2), (-0.5, 1, 0)], [(0, 1, 2, 3, 4)])
    tri = Cage([(0, 0, 0), (1, 0, 0), (0, 1, 0), (0, 0, 1)], [(0, 2, 1), (0, 1, 3), (1, 2, 3), (2, 0, 3)])
    mixed = Cage([(0, 0, 0), (1, 0, 0), (1, 1, 0), (0, 1, 0), (0.5, 2, 0.3)], [(0, 1, 2, 3), (3, 2, 4)])
    # non-manifold: three faces on one edge
    nm = Cage([(0, 0, 0), (1, 0, 0), (0, 1, 0), (0, -1, 0), (0, 0, 1)],
              [(0, 1, 2), (1, 0, 3), (0, 1, 4)])
    return {"box": box, "open": open_box, "ngon": ngon, "tri": tri, "mixed": mixed, "nonmanifold": nm}


@pytest.mark.parametrize("name", list(_cages()))
@pytest.mark.parametrize("levels", [0, 1, 2, 3])
def test_matches_reference(name, levels):
    c = _cages()[name]
    _same(sd.subdivide(c.verts, c.faces, levels), _ref(c.verts, c.faces, levels, None))


@pytest.mark.parametrize("name", ["box", "open", "mixed"])
def test_matches_reference_with_creases(name):
    c = _cages()[name]
    rnd = random.Random(7)
    edges = c.edges()
    for trial in range(6):
        cr = {e: float(rnd.choice([0, 1, 2, 3, 5])) for e in rnd.sample(edges, min(len(edges), 6))}
        for lv in (1, 2, 3):
            _same(sd.subdivide(c.verts, c.faces, lv, cr), _ref(c.verts, c.faces, lv, cr))


def test_matches_reference_random_shapes():
    rnd = random.Random(3)
    c = Cage.box((1, 1, 1))
    c.divide_face(0)
    c.loop_cut(*c.edges()[0])
    c.verts = [tuple(x + rnd.uniform(-0.2, 0.2) for x in p) for p in c.verts]
    for lv in (1, 2, 3):
        _same(sd.subdivide(c.verts, c.faces, lv), _ref(c.verts, c.faces, lv, None))


def test_detailed_matches_step_by_step():
    c = _cages()["mixed"]
    cr = {(0, 1): 2.0}
    d = sd.subdivide_detailed(c.verts, c.faces, 3, cr, line_level=0)
    v, f = _ref(c.verts, c.faces, 3, cr)
    _same((d.verts, d.faces), (v, f))
    assert len(d.source) == len(d.faces)
    assert d.lines and all(a < b for a, b in d.lines)


def test_empty_cage():
    assert sd.subdivide([], [], 2) == ([], [])
