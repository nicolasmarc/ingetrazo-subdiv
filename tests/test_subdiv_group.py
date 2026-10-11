# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 IngeTrazo contributors.
import json

import pytest

from subdiv import group as subdiv_group
from subdiv.edit import Cage


class _Edge:
    def __init__(self, v0, v1):
        self.v0, self.v1, self.faces, self.soft = v0, v1, [], False


class _Mesh:
    def __init__(self):
        self.faces, self._e = [], {}

    @property
    def edges(self):
        return list(self._e.values())

    def add_face(self, pts):
        f = type("F", (), {})()
        f.loop, f.attrs = list(pts), {}
        self.faces.append(f)
        for i, a in enumerate(pts):
            k = frozenset((a, pts[(i + 1) % len(pts)]))
            self._e.setdefault(k, _Edge(pts[i], pts[(i + 1) % len(pts)])).faces.append(f)
        return f


class _Group:
    def __init__(self, mesh, name="G"):
        self.mesh, self.name, self.ext, self.layer = mesh, name, None, None


def _vec3(x, y, z):
    return (round(x, 9), round(y, 9), round(z, 9))


def test_cage_dict_round_trip_is_json_safe():
    c = Cage.box((2, 2, 2))
    c.set_crease(c.edges()[:3], 2)
    back = Cage.from_dict(json.loads(json.dumps(c.to_dict())))
    assert back.verts == c.verts and back.faces == c.faces
    assert back.creases == c.creases


def test_build_group_stores_cage_and_closed_soft_surface():
    cage = Cage.box((2, 2, 2))
    g = subdiv_group.build_group(cage, 2, _Group, _Mesh, _vec3, name="T")
    assert g.name == "T" and len(g.mesh.faces) == 6 * 16 * 2
    assert all(len(e.faces) == 2 for e in g.mesh.edges)
    json.dumps(g.ext)                       # the document can save it


def test_read_gives_back_the_cage():
    cage = Cage.box((2, 2, 2))
    g = subdiv_group.build_group(cage, 3, _Group, _Mesh, _vec3, lines="all")
    back, levels, lines = subdiv_group.read(g)
    assert back.verts == cage.verts and levels == 3 and lines == "all"
    assert subdiv_group.is_subdiv(g)
    assert not subdiv_group.is_subdiv(_Group(_Mesh()))


def test_editing_the_stored_cage_rebuilds_a_taller_surface():
    g = subdiv_group.build_group(Cage.box((2, 2, 2)), 2, _Group, _Mesh, _vec3)
    cage, levels, lines = subdiv_group.read(g)
    top = [i for i, v in enumerate(cage.verts) if v[2] > 0]
    cage.move(top, (0, 0, 1.0))
    g2 = subdiv_group.build_group(cage, levels, _Group, _Mesh, _vec3, lines=lines)
    height = lambda grp: max(p[2] for f in grp.mesh.faces for p in f.loop)
    assert height(g2) > height(g) + 0.5


def _visible(g):
    return [e for e in g.mesh.edges if not e.soft]


def test_lines_modes_cage_all_none():
    cage = Cage.box((2, 2, 2))
    n = {}
    for mode in ("cage", "all", "none"):
        g = subdiv_group.build_group(cage, 2, _Group, _Mesh, _vec3, lines=mode)
        n[mode] = len(_visible(g))
    # a box cage has 12 edges, each cut into 4 segments at level 2
    assert n["none"] == 0 and n["cage"] == 12 * 4
    assert n["all"] > n["cage"]        # all quad edges, but never the diagonals


def test_diagonals_are_never_drawn():
    cage = Cage.box((2, 2, 2))
    g = subdiv_group.build_group(cage, 1, _Group, _Mesh, _vec3, lines="all")
    # level 1 = 24 quads -> 48 triangles; 24 diagonals hidden, 48 quad edges shown
    assert len(g.mesh.edges) == 72 and len(_visible(g)) == 48


def test_cage_colours_reach_the_surface():
    cage = Cage.box((2, 2, 2))
    cage.set_color([1], (1.0, 0.5, 0.0))
    g = subdiv_group.build_group(cage, 2, _Group, _Mesh, _vec3)
    painted = [f for f in g.mesh.faces if f.attrs.get("color") == (1.0, 0.5, 0.0)]
    assert len(painted) == 16 * 2          # one cage face -> 16 quads -> 32 triangles


def test_colour_follows_extrusion_and_survives_json():
    cage = Cage.box((2, 2, 2))
    cage.set_color([1], (0.1, 0.2, 0.3))
    cage.extrude_face(1, 1.0)
    assert cage.colors[1] == cage.colors[-1] == (0.1, 0.2, 0.3)
    back = Cage.from_dict(json.loads(json.dumps(cage.to_dict())))
    assert back.colors == cage.colors


def test_triangle_count_matches_what_is_built():
    cage = Cage.box((2, 2, 2))
    for lv in (0, 1, 2, 3):
        g = subdiv_group.build_group(cage, lv, _Group, _Mesh, _vec3)
        assert len(g.mesh.faces) == subdiv_group.triangle_count(cage, lv)


def test_auto_levels_follows_the_budget():
    box = Cage.box((2, 2, 2))
    assert subdiv_group.auto_levels(box) == 4                  # 3 072 triangles
    assert subdiv_group.auto_levels(box, budget=500) == 2      # 192 fits, 768 does not
    assert subdiv_group.auto_levels(box, budget=10) == 0
    big = Cage([(0, 0, 0)] * 4, [(0, 1, 2, 3)] * 200)
    assert subdiv_group.auto_levels(big) == 2                  # level 3 would be 25 600


# ---- converting meshes that did not come from the plugin ------------------------------------
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
    def __init__(self, loop, color=None, holes=None):
        self.loop, self.hole_loops = loop, holes or []
        self.attrs = {"color": color} if color else {}


class _SrcMesh:
    def __init__(self, faces):
        self.faces = faces


def _cube_mesh(flip=(), color=None):
    cage = Cage.box((2, 2, 2))
    vs = [_V(*p) for p in cage.verts]
    faces = []
    for i, f in enumerate(cage.faces):
        loop = [vs[k] for k in f]
        if i in flip:
            loop.reverse()
        faces.append(_F(loop, color if i == 1 else None))
    return _SrcMesh(faces)


def test_cage_from_mesh_welds_orients_and_keeps_colours():
    cage, holes = subdiv_group.cage_from_mesh(_cube_mesh(flip=(0, 4), color=(1, 0, 0, 1)))
    assert len(cage.verts) == 8 and len(cage.faces) == 6 and holes == 0
    assert cage.is_closed() and cage.is_consistent() and cage.euler() == 2
    assert cage.colors[1] == (1, 0, 0) and cage.colors.count(None) == 5


def test_cage_from_mesh_counts_holes_and_rejects_bad_input():
    m = _cube_mesh()
    m.faces[0].hole_loops = [[_V(0, 0, 0), _V(1, 0, 0), _V(0, 1, 0)]]
    assert subdiv_group.cage_from_mesh(m)[1] == 1
    with pytest.raises(ValueError):
        subdiv_group.cage_from_mesh(_SrcMesh([]))
    with pytest.raises(ValueError) as e:
        subdiv_group.cage_from_mesh(_cube_mesh(), max_faces=5)
    assert "coarse" in str(e.value)


def test_converted_box_stays_boxy_with_angle_creases_and_builds():
    cage, _ = subdiv_group.cage_from_mesh(_cube_mesh())
    assert cage.crease_by_angle(30, 4) == 12
    g = subdiv_group.build_group(cage, 3, _Group, _Mesh, _vec3)
    # sharp edges keep the corners at the original cube corners
    corners = [p for f in g.mesh.faces for p in f.loop if all(abs(abs(c) - 1) < 1e-9 for c in p)]
    assert corners


# ---- settings and joins as undoable commands ------------------------------------------------------
class _Scene:
    def __init__(self):
        self.groups, self.version = [], 0


class _G:
    ext = None

def test_set_ext_is_undoable():
    s = _Scene()
    g = _G()
    g.ext = {"subdiv": {"v": 1}}
    cmd = subdiv_group.SetExt(g, {"subdiv": {"v": 2}})
    cmd.do(s)
    assert g.ext["subdiv"]["v"] == 2
    cmd.undo(s)
    assert g.ext["subdiv"]["v"] == 1
    cmd.do(s)
    assert g.ext["subdiv"]["v"] == 2 and s.version == 3


def test_join_groups_undo_restores_both_pieces_in_place():
    s = _Scene()
    a, b, c, merged = _G(), _G(), _G(), _G()
    s.groups = [a, c, b]
    cmd = subdiv_group.JoinGroups(a, b, merged)
    cmd.do(s)
    assert s.groups == [merged, c]
    cmd.undo(s)
    assert s.groups == [a, c, b]
    cmd.do(s)
    assert s.groups == [merged, c]


def test_join_groups_when_the_second_comes_first():
    s = _Scene()
    a, b, c, merged = _G(), _G(), _G(), _G()
    s.groups = [b, c, a]
    cmd = subdiv_group.JoinGroups(a, b, merged)
    cmd.do(s)
    assert s.groups == [c, merged]
    cmd.undo(s)
    assert s.groups == [b, c, a]


def test_converting_another_group_leaves_existing_subd_groups_alone():
    """Regression: a second group turned into SubD must not touch the first."""
    class G(_Group):
        def __init__(self, mesh, name, uid):
            super().__init__(mesh, name)
            self.uid, self.xform, self.hidden, self.material, self.ifc = uid, None, False, None, None

    s = _Scene()
    a = subdiv_group.build_group(Cage.box(), 2, _mk(G, "a"), _Mesh, _vec3, name="A")
    s.groups.append(a)
    cache = subdiv_group.StateCache()
    before = cache.get(a, 0)
    assert before is not None
    plain = G(_Mesh(), "plain", "u-plain")
    s.groups.append(plain)
    b = subdiv_group.build_group(Cage.box(), 2, _mk(G, "b2"), _Mesh, _vec3, name="B")
    subdiv_group.carry_over(plain, b)
    subdiv_group.SwapGroup(plain, b).do(s)
    assert subdiv_group.is_subdiv(a) and cache.get(a, 1) is not None
    assert [g.uid for g in s.groups] == [a.uid, b.uid] and a.uid != b.uid


def _mk(cls, uid):
    return lambda mesh, name="G": cls(mesh, name, uid)


def test_split_group_is_undoable_and_keeps_order():
    s = _Scene()
    a, b, c, d = _G(), _G(), _G(), _G()
    s.groups = [a, b, d]
    cmd = subdiv_group.SplitGroup(b, [c, _G()])
    news = cmd.news
    cmd.do(s)
    assert s.groups == [a, c, news[1], d]
    cmd.undo(s)
    assert s.groups == [a, b, d]


def _built(cage, levels, merge):
    return subdiv_group.build_group(cage, levels, _Group, _Mesh, _vec3, name="x",
                                    merge_flat=merge)


def test_merge_flat_turns_each_box_face_into_one_polygon():
    c = Cage.box((2, 2, 2))
    c.crease_by_angle(30.0, 4.0)
    full = _built(c, 4, False)
    lean = _built(c, 4, True)
    assert len(full.mesh.faces) == 3072
    assert len(lean.mesh.faces) == 6 and {len(f.loop) for f in lean.mesh.faces} == {4}
    assert all(len(e.faces) == 2 for e in lean.mesh.edges)          # still watertight


def test_merge_flat_keeps_curved_surfaces_as_triangles_and_stays_closed():
    soft = Cage.box((2, 2, 2))
    assert len(_built(soft, 2, True).mesh.faces) == len(_built(soft, 2, False).mesh.faces)
    mixed = Cage.box((2, 2, 2))
    mixed.set_crease(mixed.edges()[:6], 4.0)                        # part sharp, part round
    g = _built(mixed, 3, True)
    assert all(len(e.faces) == 2 for e in g.mesh.edges)
    assert len(g.mesh.faces) < len(_built(mixed, 3, False).mesh.faces)


def test_merge_flat_on_a_pushed_out_and_shelled_box_stays_a_clean_solid():
    from subdiv import ops as subdiv_ops
    c = Cage.box((1.0, 1.0, 1.0))
    c.crease_by_angle(30.0, 4.0)
    top = max(range(6), key=lambda i: c.face_normal(i)[2])
    subdiv_ops.apply_tool(c, "grow_face", ("f", top), 0.5)
    g = _built(c, 4, True)
    # the new walls are coplanar with the old ones: the result is just a taller box
    assert len(g.mesh.faces) == 6 and all(len(e.faces) == 2 for e in g.mesh.edges)
    s = Cage.box((1.2, 0.9, 0.36))
    s.crease_by_angle(30.0, 4.0)
    mouth = max(range(6), key=lambda i: s.face_normal(i)[0])
    subdiv_ops.apply_tool(s, "delete_face", ("f", mouth))
    subdiv_ops.apply_tool(s, "shell", None, 0.05, "outside")
    h = _built(s, 4, True)
    assert len(h.mesh.faces) == 14 and all(len(e.faces) == 2 for e in h.mesh.edges)


def test_merge_flat_joins_coplanar_neighbours_after_divide():
    c = Cage.box((2, 2, 2))
    c.crease_by_angle(30.0, 4.0)
    top = max(range(6), key=lambda i: c.face_normal(i)[2])
    c.divide_face(top)
    assert len(c.faces) > 6
    g = _built(c, 3, True)
    assert len(g.mesh.faces) == 6
    assert all(len(e.faces) == 2 for e in g.mesh.edges)


def test_merge_flat_does_not_join_differently_coloured_neighbours():
    c = Cage.box((2, 2, 2))
    c.crease_by_angle(30.0, 4.0)
    top = max(range(6), key=lambda i: c.face_normal(i)[2])
    new = c.divide_face(top)
    c.set_color([new[0]], (1.0, 0.0, 0.0))
    g = _built(c, 3, True)
    assert len(g.mesh.faces) > 6
    assert all(len(e.faces) == 2 for e in g.mesh.edges)


def test_divide_then_grow_on_a_sharp_face_keeps_straight_walls():
    c = Cage.box((2, 2, 2))
    c.crease_by_angle(30.0, 4.0)
    top = max(range(6), key=lambda i: c.face_normal(i)[2])
    from subdiv import ops as subdiv_ops
    new = c.divide_face(top)
    subdiv_ops.apply_tool(c, "grow_face", ("f", new[0]), 0.5)
    # every edge of the new block is sharp: the walls stay flat
    block = c.faces[-4:]
    for f in block:
        assert all(c.creases.get(__import__('subdiv.edit',fromlist=['ekey']).ekey(f[i], f[(i + 1) % 4]), 0.0) > 0 for i in range(4))
    g = subdiv_group.build_group(c, 3, _Group, _Mesh, _vec3, name="x", merge_flat=True)
    # the block sits in a corner: two of its walls are flush with the box sides
    assert len(g.mesh.faces) == 9 and all(len(e.faces) == 2 for e in g.mesh.edges)

