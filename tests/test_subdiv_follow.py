# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 IngeTrazo contributors.
import math

import pytest

from subdiv import follow as subdiv_follow, group as subdiv_group
from subdiv.edit import Cage


# ---- a mesh with real, movable vertex objects ---------------------------------------------
class _P:
    def __init__(self, x, y, z):
        self.p = (x, y, z)

    def x(self):
        return self.p[0]

    def y(self):
        return self.p[1]

    def z(self):
        return self.p[2]


class _V:
    def __init__(self, x, y, z):
        self.position = _P(x, y, z)


class _F:
    def __init__(self, loop):
        self.loop, self.attrs, self.hole_loops = loop, {}, []


class _E:
    def __init__(self, a, b):
        self.v0, self.v1, self.faces, self.soft = a, b, [], False


class _VMesh:
    def __init__(self):
        self.faces, self._v, self._e = [], {}, {}

    @property
    def vertices(self):
        return list(self._v.values())

    @property
    def edges(self):
        return list(self._e.values())

    def add_face(self, pts):
        loop = []
        for p in pts:
            key = tuple(round(c, 9) for c in p)
            loop.append(self._v.setdefault(key, _V(*p)))
        f = _F(loop)
        self.faces.append(f)
        for i, a in enumerate(loop):
            b = loop[(i + 1) % len(loop)]
            self._e.setdefault(frozenset((id(a), id(b))), _E(a, b)).faces.append(f)
        return f

    def map_positions(self, fn):
        for v in self.vertices:
            v.position = _P(*fn(v.position.p))


class _G:
    def __init__(self, mesh, name="G"):
        self.mesh, self.name, self.ext, self.uid = mesh, name, None, "u1"


def _vec3(x, y, z):
    return (x, y, z)


def _built(cage=None, levels=2):
    cage = cage or Cage.box((2, 3, 4), center=(1, 2, 3))
    return cage, subdiv_group.build_group(cage, levels, _G, _VMesh, _vec3, name="T")


def _same(a, b, tol=1e-4):
    return all(math.dist(p, q) < tol for p, q in zip(a, b))


def _rot_z(deg, about):
    c, s = math.cos(math.radians(deg)), math.sin(math.radians(deg))

    def f(p):
        x, y = p[0] - about[0], p[1] - about[1]
        return (about[0] + c * x - s * y, about[1] + s * x + c * y, p[2])
    return f


# ---- the maths ---------------------------------------------------------------------------
def test_solve_affine_recovers_a_known_map():
    src = [(0, 0, 0), (1, 0, 0), (0, 1, 0), (0, 0, 1)]
    f = _rot_z(30, (0.2, 0.1, 0))
    dst = [tuple(c * 2 + 1 for c in f(p)) for p in src]
    aff = subdiv_follow.solve_affine(src, dst)
    for p, q in zip(src, dst):
        assert _same([subdiv_follow.apply_point(aff, p)], [q], 1e-9)


def test_flat_sets_are_completed_with_a_normal_point():
    src = [(0, 0, 0), (1, 0, 0), (0, 1, 0)]
    dst = [(5, 5, 5), (5, 6, 5), (4, 5, 5)]                 # rotated 90 degrees, moved
    aff = subdiv_follow.solve_affine(src, dst)
    assert _same([subdiv_follow.apply_point(aff, (1, 1, 0))], [(4, 6, 5)], 1e-9)


# ---- following a group --------------------------------------------------------------------
def test_build_group_remembers_how_to_follow():
    _cage, g = _built()
    ref = g.ext["subdiv"]["ref"]
    assert len(ref["idx"]) in (3, 4) and len(ref["pts"]) == len(ref["idx"])


def test_unchanged_group_keeps_its_cage():
    cage, g = _built()
    got = subdiv_group.StateCache().get(g)[0]
    assert _same(got.verts, cage.verts)


def test_cage_follows_a_translation():
    cage, g = _built()
    g.mesh.map_positions(lambda p: (p[0] + 5, p[1] - 2, p[2] + 0.5))
    got = subdiv_group.StateCache().get(g)[0]
    assert _same(got.verts, [(x + 5, y - 2, z + 0.5) for x, y, z in cage.verts])


def test_cage_follows_a_rotation_and_a_scale_and_a_mirror():
    cage, g = _built()
    f = _rot_z(37, (1, 2, 0))
    g.mesh.map_positions(f)
    got = subdiv_group.StateCache().get(g)[0]
    assert _same(got.verts, [f(p) for p in cage.verts])

    cage, g = _built()
    g.mesh.map_positions(lambda p: tuple(c * 2.5 for c in p))
    got = subdiv_group.StateCache().get(g)[0]
    assert _same(got.verts, [tuple(c * 2.5 for c in p) for p in cage.verts], 1e-3)

    cage, g = _built()
    g.mesh.map_positions(lambda p: (-p[0], p[1], p[2]))
    got = subdiv_group.StateCache().get(g)[0]
    assert _same(got.verts, [(-x, y, z) for x, y, z in cage.verts])


def test_symmetry_plane_follows_too():
    cage = Cage.box((2, 2, 2))
    cage.sym = {"on": True, "point": (0.0, 0.0, 0.0), "normal": (1.0, 0.0, 0.0)}
    cage, g = _built(cage)
    g.mesh.map_positions(lambda p: (p[0] + 4, p[1], p[2]))
    sym = subdiv_group.StateCache().get(g)[0].sym
    assert sym["on"] and _same([sym["point"]], [(4, 0, 0)]) and _same([sym["normal"]], [(1, 0, 0)])


def test_falls_back_to_translation_when_the_vertex_order_changed():
    cage, g = _built()
    items = list(g.mesh._v.items())
    items.reverse()                                          # the mesh reloaded in another order
    g.mesh._v = dict(items)
    g.mesh.map_positions(lambda p: (p[0] + 1, p[1] + 1, p[2]))
    got = subdiv_group.StateCache().get(g)[0]
    assert _same(got.verts, [(x + 1, y + 1, z) for x, y, z in cage.verts])


def test_reordered_but_unmoved_group_is_left_alone():
    cage, g = _built()
    g.mesh._v = dict(reversed(list(g.mesh._v.items())))
    got = subdiv_group.StateCache().get(g)[0]
    assert _same(got.verts, cage.verts)


def test_rebuilding_from_the_followed_cage_does_not_move_it_twice():
    cage, g = _built()
    g.mesh.map_positions(lambda p: (p[0] + 3, p[1], p[2]))
    cache = subdiv_group.StateCache()
    moved, levels, lines = cache.get(g)
    g2 = subdiv_group.build_group(moved.copy(), levels, _G, _VMesh, _vec3, name="T")
    assert _same(cache.get(g2)[0].verts, moved.verts)
    assert _same(cache.get(g2)[0].verts, [(x + 3, y, z) for x, y, z in cage.verts])


def test_a_flat_cage_still_follows():
    flat = Cage([(0, 0, 0), (2, 0, 0), (2, 2, 0), (0, 2, 0)], [(0, 1, 2, 3)])
    _c, g = _built(flat, levels=2)
    f = _rot_z(90, (0, 0))
    g.mesh.map_positions(f)
    got = subdiv_group.StateCache().get(g)[0]
    assert _same(got.verts, [f(p) for p in flat.verts])


def test_cache_recomputes_only_when_the_stamp_changes():
    cage, g = _built()
    cache = subdiv_group.StateCache()
    a = cache.get(g, stamp=1)[0]
    g.mesh.map_positions(lambda p: (p[0] + 1, p[1], p[2]))
    assert cache.get(g, stamp=1)[0] is a                     # same stamp: untouched
    assert _same(cache.get(g, stamp=2)[0].verts, [(x + 1, y, z) for x, y, z in cage.verts])
