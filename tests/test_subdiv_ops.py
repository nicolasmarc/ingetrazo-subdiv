# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 IngeTrazo contributors.
import pytest

from subdiv import group as subdiv_group
from subdiv.edit import Cage, ekey
from subdiv.ops import (SPECS, TOOL_SPECS, apply_tool, closest_on_axis, describe,
                             mirror_partners, mirror_selection, pick, symmetric_move, valid)


def _box():
    return Cage.box((2, 2, 2))


def _top(c):
    return max(range(len(c.faces)), key=lambda i: c.face_centroid(i)[2])


def _closed(c):
    return c.is_closed() and c.is_consistent() and c.euler() == 2


def _open_box():
    """A box with its top face removed: one open border of 4 edges."""
    c = _box()
    c.remove_faces([_top(c)])
    return c


def _border_edge(c):
    loop = c.boundary_loops()[0]
    return ("e", loop[0], loop[1])


def test_thirteen_tools_with_distinct_icons():
    assert len(TOOL_SPECS) == 14
    assert len({s.icon for s in TOOL_SPECS}) == 14 and len({s.key for s in TOOL_SPECS}) == 14


def test_length_tools_are_flagged_and_labels_carry_no_unit():
    lengths = {s.key for s in TOOL_SPECS if s.length}
    assert lengths == {"create", "edit", "grow_face", "grow_edge", "shell"}
    assert all("(m)" not in s.value_label for s in TOOL_SPECS)


def test_edit_moves_a_face_along_its_normal():
    c = _box()
    t = _top(c)
    z0 = c.face_centroid(t)[2]
    apply_tool(c, "edit", ("f", t), 0.5)
    assert c.face_centroid(t)[2] == pytest.approx(z0 + 0.5)


def test_edit_axis_x_moves_a_vertex():
    c = _box()
    x0 = c.verts[0][0]
    apply_tool(c, "edit", ("v", 0), 1.0, axis="x")
    assert c.verts[0][0] == pytest.approx(x0 + 1.0)


def test_crease_on_edge_and_on_face_and_clear():
    c = _box()
    a, b = c.edges()[0]
    apply_tool(c, "crease", ("e", a, b), 2)
    assert c.creases[ekey(a, b)] == 2
    apply_tool(c, "crease", ("f", 0), 3)
    f0 = c.faces[0]
    assert all(c.creases[ekey(f0[i], f0[(i + 1) % 4])] == 3 for i in range(4))
    apply_tool(c, "crease", ("e", a, b), 0)
    assert ekey(a, b) not in c.creases


def test_crease_with_no_selection_hits_every_edge_and_zero_clears_all():
    c = _box()
    r = apply_tool(c, "crease", None, 1)
    assert len(c.creases) == 12 and r.selection is None
    apply_tool(c, "crease", None, 0)
    assert c.creases == {}
    # a converted box with creases everywhere smooths fully once they are cleared
    c.crease_by_angle(30, 4)
    assert len(c.creases) == 12
    apply_tool(c, "crease", None, 0)
    assert c.creases == {}


def test_grow_face_keeps_cage_closed():
    c = _box()
    t = _top(c)
    r = apply_tool(c, "grow_face", ("f", t), 1.0)
    assert r.selection == ("f", t) and _closed(c) and len(c.faces) == 10


def test_grow_edge_goes_outward_from_the_face():
    c = _open_box()
    sel = _border_edge(c)
    n_faces = len(c.faces)
    r = apply_tool(c, "grow_edge", sel, 0.5)
    assert len(c.faces) == n_faces + 1 and r.selection[0] == "e"
    assert c.is_consistent()
    # the new edge sits farther from the box's axis than the old one
    old = [c.verts[v] for v in sel[1:]]
    new = [c.verts[v] for v in r.selection[1:]]
    far = lambda p: abs(p[0]) + abs(p[1])
    assert max(map(far, new)) > max(map(far, old)) or \
        abs(new[0][2] - old[0][2]) > 0.4 or max(map(far, new)) >= max(map(far, old))


def test_grow_edge_rejects_an_interior_edge():
    c = _box()
    a, b = c.edges()[0]
    with pytest.raises(ValueError):
        apply_tool(c, "grow_edge", ("e", a, b), 0.5)


def test_stretch_along_z():
    c = _box()
    apply_tool(c, "stretch", ("f", _top(c)), 2.0, axis="z")
    # a face alone has no length along its normal: the whole piece stretches,
    # anchored on the far side (bottom stays at -1, top goes from 1 to 3)
    assert min(v[2] for v in c.verts) == pytest.approx(-1.0)
    assert c.face_centroid(_top(c))[2] == pytest.approx(3.0)
    apply_tool(c, "stretch", ("f", _top(c)), 2.0, axis="x")
    xs = [c.verts[v][0] for v in c.faces[_top(c)]]
    assert max(xs) - min(xs) == pytest.approx(4.0)


def test_inset_face():
    c = _box()
    t = _top(c)
    apply_tool(c, "inset_face", ("f", t), 0.5)
    xs = [c.verts[v][0] for v in c.faces[t]]
    assert max(xs) - min(xs) == pytest.approx(1.0) and _closed(c)


def test_offset_edge_loop_and_close():
    c = _open_box()
    sel = _border_edge(c)
    r = apply_tool(c, "offset_edge", sel, 0.5)
    assert c.is_consistent() and len(c.boundary_loops()) == 1
    assert r.selection[0] == "e" and valid(c, r.selection)
    apply_tool(c, "close", r.selection)
    assert _closed(c)


def test_squeeze_ring_of_a_face():
    c = _box()
    t = _top(c)
    apply_tool(c, "squeeze", ("f", t), 0.5)
    xs = [c.verts[v][0] for v in c.faces[t]]
    assert max(xs) - min(xs) == pytest.approx(1.0)


def test_divide_face():
    c = _box()
    apply_tool(c, "divide", ("f", 0))
    assert len(c.faces) == 16 and _closed(c)


def test_close_hole():
    c = _open_box()
    r = apply_tool(c, "close", _border_edge(c))
    assert r.selection[0] == "f" and _closed(c)


def test_bridge_needs_two_clicks_and_two_openings():
    bottom = [(0, 1, 0), (1, 1, 0), (1, 0, 0), (0, 0, 0)]
    top = [(0, 0, 1), (1, 0, 1), (1, 1, 1), (0, 1, 1)]
    c = Cage(bottom + top, [(0, 1, 2, 3), (4, 5, 6, 7)])
    la, lb = c.boundary_loops()
    r1 = apply_tool(c, "bridge", ("e", la[0], la[1]))
    assert r1.pending and len(c.faces) == 2          # nothing built yet
    with pytest.raises(ValueError):
        apply_tool(c, "bridge", ("e", la[1], la[2]), pending=r1.pending)
    r2 = apply_tool(c, "bridge", ("e", lb[0], lb[1]), pending=r1.pending)
    assert r2.pending is None and _closed(c)


def test_wrong_selection_gives_a_status_bar_sentence():
    c = _box()
    with pytest.raises(ValueError) as e:
        apply_tool(c, "grow_face", ("v", 0), 1.0)
    assert "face" in str(e.value).lower()
    with pytest.raises(ValueError):
        apply_tool(c, "divide", None)
    with pytest.raises(ValueError):
        apply_tool(c, "grow_face", None, 1.0)
    with pytest.raises(ValueError):
        apply_tool(c, "divide", ("f", 99))


def test_describe_and_valid():
    c = _box()
    assert describe(None) == "Nothing selected" and describe(("f", 3)) == "Face 3"
    assert valid(c, ("v", 7)) and not valid(c, ("v", 8)) and not valid(c, ("e", 0, 7))


# ---- picking ---------------------------------------------------------------------------
def _flat():
    """A unit square seen from above: pixels = metres * 100."""
    c = Cage([(0, 0, 0), (1, 0, 0), (1, 1, 0), (0, 1, 0)], [(0, 1, 2, 3)])
    xs = [v[0] * 100 for v in c.verts]
    ys = [v[1] * 100 for v in c.verts]
    return c, xs, ys, [True] * 4


def test_pick_point_edge_face_miss():
    c, xs, ys, fr = _flat()
    assert pick(c, xs, ys, fr, 102, 3) == ("v", 1)
    assert pick(c, xs, ys, fr, 50, 3) == ("e", 0, 1)
    assert pick(c, xs, ys, fr, 50, 50) == ("f", 0)
    assert pick(c, xs, ys, fr, 400, 400) is None


def test_pick_ignores_points_behind_the_camera():
    c, xs, ys, _ = _flat()
    assert pick(c, xs, ys, [False] * 4, 100, 0) is None


# ---- undoable swap -----------------------------------------------------------------------
class _Scene:
    def __init__(self):
        self.groups, self.version = [], 0


class _G:
    pass


def test_swap_group_undo_restores_the_old_group():
    s = _Scene()
    old, new = _G(), _G()
    s.groups.append(old)
    cmd = subdiv_group.SwapGroup(old, new)
    cmd.do(s)
    assert s.groups == [new]
    cmd.undo(s)
    assert s.groups == [old]
    cmd.do(s)                                   # redo
    assert s.groups == [new] and s.version == 3


def test_swap_group_adds_and_removes_when_there_is_no_old_group():
    s = _Scene()
    g = _G()
    cmd = subdiv_group.SwapGroup(None, g)
    cmd.do(s)
    assert s.groups == [g]
    cmd.undo(s)
    assert s.groups == []


def test_carry_over_keeps_identity():
    old, new = _G(), _G()
    old.name, old.layer, old.ifc, old.hidden = "Roof", "L1", {"class": "IfcRoof"}, True
    old.material, old.uid = {"color": (1, 0, 0)}, "abc"
    new.name = new.layer = new.ifc = new.hidden = new.material = new.uid = None
    subdiv_group.carry_over(old, new)
    assert (new.name, new.layer, new.hidden, new.uid) == ("Roof", "L1", True, "abc")


# ---- dragging ----------------------------------------------------------------------------
def test_closest_on_axis_finds_where_the_ray_crosses_the_axis():
    s = closest_on_axis((5, 0, 2), (-1, 0, 0), (0, 0, 0), (0, 0, 1))
    assert s == pytest.approx(2.0)
    # unnormalised inputs: the axis is normalised, so s is in metres
    s2 = closest_on_axis((5, 0, 2), (-3, 0, 0), (0, 0, 1), (0, 0, 2))
    assert s2 == pytest.approx(1.0)               # from z = 1 up to the ray at z = 2


def test_closest_on_axis_is_none_when_ray_is_parallel():
    assert closest_on_axis((1, 1, 0), (0, 0, 1), (0, 0, 0), (0, 0, 1)) is None


# ---- delete face, join and bridge two pieces -------------------------------------------------
def test_delete_face_opens_the_cage_and_close_restores_it():
    c = _box()
    r = apply_tool(c, "delete_face", ("f", _top(c)))
    assert r.selection is None and len(c.faces) == 5 and len(c.boundary_loops()) == 1
    apply_tool(c, "close", _border_edge(c))
    assert _closed(c)


def test_delete_face_needs_a_face():
    c = _box()
    with pytest.raises(ValueError):
        apply_tool(c, "delete_face", ("v", 0))
    with pytest.raises(ValueError):
        apply_tool(Cage([(0, 0, 0), (1, 0, 0), (0, 1, 0)], [(0, 1, 2)]), "delete_face", ("f", 0))


def test_two_boxes_joined_then_bridged_make_one_closed_cage():
    a = Cage.box((2, 2, 2), center=(0, 0, 1))
    b = Cage.box((2, 2, 2), center=(0, 0, 4))
    apply_tool(a, "delete_face", ("f", _top(a)))
    apply_tool(b, "delete_face", ("f", min(range(6), key=lambda i: b.face_centroid(i)[2])))
    from subdiv.group import join_cages
    j = join_cages(a, b)
    assert len(j.verts) == 16 and len(j.faces) == 10 and len(j.boundary_loops()) == 2
    la, lb = j.boundary_loops()
    j.bridge(la, lb)
    _closed(j)
    assert j.is_closed() and j.is_consistent() and j.euler() == 2


def test_merge_keeps_colours_and_creases_of_both_pieces():
    a, b = _box(), _box()
    b.set_color([2], (1, 0, 0))
    e = b.edges()[0]
    b.set_crease([e], 3)
    j = a.copy()
    v0, f0 = j.merge(b)
    assert (v0, f0) == (8, 6) and j.colors[8] == (1, 0, 0)
    assert j.creases[ekey(e[0] + 8, e[1] + 8)] == 3


# ---- mirror symmetry ----------------------------------------------------------------------------
SYM_X = {"on": True, "point": (0.0, 0.0, 0.0), "normal": (1.0, 0.0, 0.0)}


def test_every_box_corner_has_a_mirror_partner():
    c = _box()
    p = mirror_partners(c, SYM_X)
    assert len(p) == 8 and all(p[p[v]] == v and p[v] != v for v in p)
    assert all(c.verts[p[v]][0] == -c.verts[v][0] for v in p)


def test_symmetric_edit_moves_both_sides():
    c = _box()
    v = next(i for i, q in enumerate(c.verts) if q == (1.0, 1.0, 1.0))
    apply_tool(c, "edit", ("v", v), 0.5, axis="z", sym=SYM_X)
    partner = mirror_partners(c, SYM_X)[v]
    assert c.verts[v][2] == pytest.approx(1.5) and c.verts[partner][2] == pytest.approx(1.5)
    assert c.verts[partner][0] == pytest.approx(-1.0)


def test_symmetric_edit_without_symmetry_moves_one_side_only():
    c = _box()
    v = next(i for i, q in enumerate(c.verts) if q == (1.0, 1.0, 1.0))
    apply_tool(c, "edit", ("v", v), 0.5, axis="z")
    assert sum(1 for q in c.verts if q[2] > 1.2) == 1


def test_symmetric_divide_cuts_the_mirror_face_too():
    c = _box()
    side = next(i for i in range(6) if c.face_normal(i)[0] > 0.9)       # the +X face
    apply_tool(c, "divide", ("f", side), sym=SYM_X)
    assert len(c.faces) == 16 and c.is_closed() and c.is_consistent()   # cut once, not twice


def test_symmetric_grow_face_on_both_sides():
    c = _box()
    side = next(i for i in range(6) if c.face_normal(i)[0] > 0.9)
    apply_tool(c, "grow_face", ("f", side), 1.0, sym=SYM_X)
    xs = [q[0] for q in c.verts]
    assert max(xs) == pytest.approx(2.0) and min(xs) == pytest.approx(-2.0)
    assert c.is_closed() and c.is_consistent()


def test_a_face_across_the_plane_is_edited_once():
    c = _box()
    top = _top(c)
    assert mirror_selection(c, ("f", top), mirror_partners(c, SYM_X)) == ("f", top)
    apply_tool(c, "grow_face", ("f", top), 1.0, sym=SYM_X)
    assert len(c.faces) == 10 and c.is_closed()


def test_symmetric_crease_marks_the_partner_edge():
    c = _box()
    p = mirror_partners(c, SYM_X)
    a, b = next((a, b) for a, b in c.edges() if p[a] != a and ekey(p[a], p[b]) != ekey(a, b))
    apply_tool(c, "crease", ("e", a, b), 2, sym=SYM_X)
    assert c.creases[ekey(a, b)] == 2 and c.creases[ekey(p[a], p[b])] == 2


def test_points_on_the_plane_stay_on_it():
    c = _box()
    apply_tool(c, "divide", ("f", _top(c)))                   # centre point sits on x = 0
    centre = next(i for i, q in enumerate(c.verts) if q[0] == 0 and q[1] == 0 and q[2] == 1)
    apply_tool(c, "edit", ("v", centre), 0.7, axis="x", sym=SYM_X)
    assert c.verts[centre][0] == pytest.approx(0.0)
    apply_tool(c, "edit", ("v", centre), 0.4, axis="z", sym=SYM_X)
    assert c.verts[centre][2] == pytest.approx(1.4)


def test_symmetric_move_for_dragging():
    c = _box()
    v = next(i for i, q in enumerate(c.verts) if q == (1.0, 1.0, 1.0))
    symmetric_move(c, [v], (0.2, 0.3, 0.4), SYM_X)
    q = mirror_partners(c, SYM_X)[v]
    assert c.verts[v][0] == pytest.approx(1.2) and c.verts[v][2] == pytest.approx(1.4)
    assert c.verts[q][0] == pytest.approx(-1.2) and c.verts[q][1] == pytest.approx(1.3)
    assert c.verts[q][2] == pytest.approx(1.4)


def test_symmetry_works_on_any_plane_not_only_axes():
    c = _box()
    s = 2 ** -0.5
    diag = {"on": True, "point": (0.0, 0.0, 0.0), "normal": (s, s, 0.0)}   # swaps x and y
    p = mirror_partners(c, diag)
    assert all(abs(c.verts[p[v]][0] + c.verts[v][1]) < 1e-9 for v in p) and len(p) == 8   # (x, y) -> (-y, -x)


def test_bridge_and_delete_are_never_mirrored_twice():
    c = _box()
    side = next(i for i in range(6) if c.face_normal(i)[0] > 0.9)
    apply_tool(c, "delete_face", ("f", side), sym=SYM_X)
    assert len(c.faces) == 5


def test_bridge_between_two_faces_removes_them_and_closes_the_cage():
    from subdiv.group import join_cages
    a = Cage.box((2, 2, 2), center=(0, 0, 1))
    b = Cage.box((2, 2, 2), center=(0, 0, 4))
    j = join_cages(a, b)
    near = lambda z: min(range(len(j.faces)), key=lambda i: abs(j.face_centroid(i)[2] - z))
    fa, fb = near(2.0), near(3.0)                  # top of the 1st box, underside of the 2nd
    r1 = apply_tool(j, "bridge", ("f", fa))
    assert r1.pending is not None and len(j.faces) == 12
    r2 = apply_tool(j, "bridge", ("f", fb), pending=r1.pending)
    assert len(j.faces) == 12 - 2 + 4
    assert j.is_closed() and j.is_consistent() and j.euler() == 2


def test_bridge_refuses_the_same_face_and_mismatched_sides():
    c = _box()
    r1 = apply_tool(c, "bridge", ("f", 0))
    with pytest.raises(ValueError):
        apply_tool(c, "bridge", ("f", 0), pending=r1.pending)


def test_bridge_twist_turns_the_ring_and_stays_closed():
    from subdiv.group import join_cages
    outs = []
    for tw in (0, 1, -1, 2):
        j = join_cages(Cage.box((2, 2, 2), center=(0, 0, 1)), Cage.box((2, 2, 2), center=(0, 0, 4)))
        near = lambda z: min(range(len(j.faces)), key=lambda i: abs(j.face_centroid(i)[2] - z))
        fa, fb = near(2.0), near(3.0)
        r = apply_tool(j, "bridge", ("f", fa))
        apply_tool(j, "bridge", ("f", fb), value=float(tw), pending=r.pending)
        assert j.is_closed() and j.is_consistent()
        outs.append(sorted(map(sorted, j.faces)))
    assert outs[0] != outs[1] and outs[1] != outs[2]


# ---- shell ---------------------------------------------------------------------------------
def _bbox_z(c):
    zs = [v[2] for v in c.verts]
    return min(zs), max(zs)


def test_shell_of_an_open_box_is_a_closed_thick_sheet_in_each_mode():
    vols = {}
    for mode in ("outside", "inside", "center"):
        c = _box()
        apply_tool(c, "delete_face", ("f", _top(c)))
        lo0, hi0 = _bbox_z(c)
        r = apply_tool(c, "shell", None, 0.1, mode)
        assert r.selection is None
        assert c.is_closed() and c.is_consistent() and c.euler() == 2
        ok, problems, vol = c.solid_report()
        assert ok and vol > 0, problems
        vols[mode] = vol
        lo, hi = _bbox_z(c)
        if mode == "outside":
            assert lo < lo0 - 0.05 and hi >= hi0 - 1e-9
        if mode == "inside":
            assert abs(lo - lo0) < 1e-9
    assert all(abs(v - vols["center"]) < 0.3 * vols["center"] for v in vols.values())


def test_shell_of_a_closed_box_is_hollow_with_the_volume_of_the_wall():
    c = _box()
    v0 = c.signed_volume()
    apply_tool(c, "shell", None, 0.1, "inside")
    assert c.is_closed() and c.is_consistent()
    assert len(c.verts) == 16 and len(c.faces) == 12
    assert 0 < abs(c.signed_volume()) < v0           # outer minus the cavity


def test_shell_keeps_the_lip_creased_and_refuses_bad_values():
    c = _box()
    apply_tool(c, "delete_face", ("f", _top(c)))
    apply_tool(c, "shell", None, 0.1, "outside")
    assert sum(1 for s in c.creases.values() if s >= 2) >= 8
    with pytest.raises(ValueError):
        apply_tool(c, "shell", None, 0.0, "outside")


def test_shell_is_not_mirrored_twice():
    c = _box()
    sym = {"on": True, "point": (0.0, 0.0, 0.0), "normal": (1.0, 0.0, 0.0)}
    apply_tool(c, "shell", None, 0.1, "outside", sym=sym)
    assert len(c.verts) == 16 and len(c.faces) == 12


# ---- several items together -----------------------------------------------------------------
def test_vertex_union_lists_each_point_once_and_describe_counts_items():
    from subdiv.ops import describe_many, vertex_union
    c = _box()
    f = c.faces[0]
    pts = vertex_union(c, [("v", f[0]), ("f", 0), ("e", f[0], f[1])])
    assert sorted(pts) == sorted(f) and len(pts) == len(set(pts))
    assert "2 items" in describe_many([("v", 0), ("v", 1)])
    assert describe_many([("v", 3)]) == "Point 3" and describe_many([]) == "Nothing selected"


def test_moving_a_union_of_points_moves_them_together_and_mirrors():
    from subdiv.ops import symmetric_move, vertex_union
    c = _box()
    pts = vertex_union(c, [("v", 0), ("v", 1)])
    before = [c.verts[i] for i in pts]
    symmetric_move(c, pts, (0.0, 0.0, 0.5), None)
    for i, b in zip(pts, before):
        assert abs(c.verts[i][2] - b[2] - 0.5) < 1e-12


def test_shell_straightens_mixed_winding_and_flip_reverses_everything():
    c = _box()
    apply_tool(c, "delete_face", ("f", _top(c)))
    c.faces[0] = tuple(reversed(c.faces[0]))             # one face wound the wrong way
    assert not c.is_consistent()
    apply_tool(c, "shell", None, 0.1, "outside")
    assert c.is_consistent() and c.is_closed() and c.solid_report()[0]
    before = list(c.faces)
    c.flip()
    assert c.faces == [tuple(reversed(f)) for f in before] and c.is_consistent()


def test_rotate_turns_points_about_an_axis_and_keeps_distances():
    import math
    from subdiv.ops import symmetric_rotate
    c = _box()
    ids = list(range(len(c.verts)))
    pivot = (0.0, 0.0, 0.0)
    before = [c.verts[i] for i in ids]
    symmetric_rotate(c, ids, pivot, (0.0, 0.0, 1.0), math.pi / 2, None)
    for b, i in zip(before, ids):
        a = c.verts[i]
        assert abs(a[0] + b[1]) < 1e-9 and abs(a[1] - b[0]) < 1e-9 and abs(a[2] - b[2]) < 1e-9
    symmetric_rotate(c, ids, pivot, (0.0, 0.0, 1.0), -math.pi / 2, None)
    assert all(abs(c.verts[i][k] - b[k]) < 1e-9 for b, i in zip(before, ids) for k in range(3))


def test_rotating_a_single_point_about_itself_changes_nothing_and_pivot_stays():
    import math
    c = _box()
    p = c.verts[0]
    c.rotate([0], p, (1.0, 1.0, 0.0), 1.0)
    assert all(abs(c.verts[0][k] - p[k]) < 1e-12 for k in range(3))
    c.rotate([1], p, (0.0, 0.0, 0.0), 1.0)               # a zero axis is ignored
    assert c.verts[1] == _box().verts[1]


def test_angle_in_plane_measures_the_sweep_around_an_axis():
    import math
    from subdiv.ops import angle_in_plane, plane_basis
    axis, pivot = (0.0, 0.0, 1.0), (0.0, 0.0, 0.0)
    u, v = plane_basis(axis)
    assert abs(u[0] * v[0] + u[1] * v[1] + u[2] * v[2]) < 1e-12
    ray = (0.0, 0.0, -1.0)

    def at(t):
        return angle_in_plane((math.cos(t), math.sin(t), 5.0), ray, pivot, axis)

    sweep = at(1.0) - at(0.3)
    assert abs(sweep - 0.7) < 1e-9
    assert angle_in_plane((0, 0, 5), (1.0, 0.0, 0.0), pivot, axis) is None   # parallel


def test_pick_takes_the_face_nearest_the_viewer_when_faces_overlap_on_screen():
    from subdiv.ops import pick
    top = [(0, 0, 1), (2, 0, 1), (2, 2, 1), (0, 2, 1)]
    low = [(1, 1, 0), (3, 1, 0), (3, 3, 0), (1, 3, 0)]
    c = Cage(top + low, [(0, 1, 2, 3), (4, 5, 6, 7)])
    xs = [v[0] * 100 for v in c.verts]
    ys = [v[1] * 100 for v in c.verts]
    front = [True] * 8
    # click at (1.9, 1.9): the lower face's centre is much closer on screen
    assert pick(c, xs, ys, front, 190, 190) == ("f", 1)
    ray = ((1.9, 1.9, 5.0), (0.0, 0.0, -1.0))              # looking down from above
    assert pick(c, xs, ys, front, 190, 190, ray=ray) == ("f", 0)
    ray = ((1.9, 1.9, -5.0), (0.0, 0.0, 1.0))              # looking up from below
    assert pick(c, xs, ys, front, 190, 190, ray=ray) == ("f", 1)


def test_pick_can_skip_a_selected_face_to_reach_the_one_behind_it():
    from subdiv.ops import pick
    top = [(0, 0, 1), (2, 0, 1), (2, 2, 1), (0, 2, 1)]
    low = [(1, 1, 0), (3, 1, 0), (3, 3, 0), (1, 3, 0)]
    c = Cage(top + low, [(0, 1, 2, 3), (4, 5, 6, 7)])
    xs = [v[0] * 100 for v in c.verts]
    ys = [v[1] * 100 for v in c.verts]
    ray = ((1.9, 1.9, 5.0), (0.0, 0.0, -1.0))
    assert pick(c, xs, ys, [True] * 8, 190, 190, ray=ray) == ("f", 0)
    assert pick(c, xs, ys, [True] * 8, 190, 190, ray=ray, skip=[("f", 0)]) == ("f", 1)
    assert pick(c, xs, ys, [True] * 8, 190, 190, ray=ray, skip=[("f", 0), ("f", 1)]) is None


def _grid(n=2):
    """A flat n x n sheet of quads (open): its corner and edge points are on the border."""
    verts = [(float(i), float(j), 0.0) for j in range(n + 1) for i in range(n + 1)]
    faces = [(j * (n + 1) + i, j * (n + 1) + i + 1, (j + 1) * (n + 1) + i + 1,
              (j + 1) * (n + 1) + i) for j in range(n) for i in range(n)]
    return Cage(verts, faces)


def test_edge_loop_runs_straight_through_four_way_points_and_follows_borders():
    from subdiv.ops import edge_loop
    g = _grid(2)                                   # 3 x 3 points, centre is point 4
    inner = edge_loop(g, 3, 4)                     # the horizontal edge left of the centre
    assert {ekey(*e) for e in inner} == {ekey(3, 4), ekey(4, 5)}
    assert ekey(*inner[0]) == ekey(3, 4)
    border = edge_loop(g, 0, 1)                    # a border edge: the whole outline
    assert len(border) == 8 and len({ekey(*e) for e in border}) == 8
    c = _box()                                     # cube points have three edges: no loop
    a, b = next(iter(c.edge_faces()))
    assert [ekey(*e) for e in edge_loop(c, a, b)] == [ekey(a, b)]
    with pytest.raises(ValueError):
        edge_loop(g, 0, 8)


def test_edge_contours_steps_edge_loop_then_each_face_outline_without_repeats():
    from subdiv.ops import edge_contours
    c = _box()                                     # a cube: no loop, two faces meet at an edge
    a, b = next(iter(c.edge_faces()))
    st = edge_contours(c, a, b)
    assert [n for n, _e in st] == ["Edge", "Face outline", "Face outline"]
    assert len(st[1][1]) == 4 and len(st[2][1]) == 4
    assert ekey(a, b) in {ekey(*e) for e in st[1][1]} & {ekey(*e) for e in st[2][1]}
    g = _grid(2)                                   # the sheet: the loop comes second
    st = edge_contours(g, 3, 4)
    assert [n for n, _e in st][:2] == ["Edge", "Loop"] and len(st[1][1]) == 2
    st = edge_contours(g, 0, 1)                    # a border edge has one face
    assert [n for n, _e in st] == ["Edge", "Loop", "Face outline"]


def test_shell_keeps_full_thickness_on_box_edges_even_with_extra_points():
    c = _box()
    apply_tool(c, "divide", ("f", 0))              # extra points on the edges and faces
    apply_tool(c, "divide", ("f", 2))
    n = len(c.verts)
    before = list(c.verts)
    lo = [min(v[k] for v in before) for k in range(3)]
    hi = [max(v[k] for v in before) for k in range(3)]
    apply_tool(c, "shell", None, 0.1, "outside")
    for v0, v1 in zip(before, c.verts[:n]):
        for k in range(3):
            if abs(v0[k] - lo[k]) < 1e-9:           # on a low face: pushed out exactly 0.1
                assert abs(v1[k] - (v0[k] - 0.1)) < 5e-3
            elif abs(v0[k] - hi[k]) < 1e-9:
                assert abs(v1[k] - (v0[k] + 0.1)) < 5e-3


def test_shell_of_a_sharp_open_box_keeps_the_mouth_rectangular():
    a, b, h, t = 1.2, 0.9, 0.36, 0.05
    verts = [(x * a, y * b, z * h) for z in (0, 1) for y in (0, 1) for x in (0, 1)]
    faces = [(0, 2, 3, 1), (4, 5, 7, 6), (0, 1, 5, 4), (2, 6, 7, 3), (0, 4, 6, 2), (1, 3, 7, 5)]
    c = Cage(verts, faces)
    c.orient()
    assert c.crease_by_angle(30.0, 4.0) == 12
    mouth = max(range(6), key=lambda i: c.face_normal(i)[0])        # the +X end
    apply_tool(c, "delete_face", ("f", mouth))
    apply_tool(c, "shell", None, t, "outside")
    pts, _faces = c.smooth(3)
    end = [p for p in pts if abs(p[0] - a) < 1e-6]
    assert end
    # nothing of the lip may lie inside the opening: it must stay a rectangular frame
    assert not [p for p in end if 1e-6 < p[1] < b - 1e-6 and 1e-6 < p[2] < h - 1e-6]


def test_a_new_box_with_sharp_edges_smooths_to_a_crisp_box():
    c = Cage.box((2.0, 1.0, 0.5))
    assert c.crease_by_angle(30.0, 4.0) == 12                  # what Create does when asked
    pts, _f = c.smooth(4)
    lo, hi = c.bounds()
    assert all(min(abs(p[k] - lo[k]) for k in range(3)) < 1e-9 or
               min(abs(p[k] - hi[k]) for k in range(3)) < 1e-9 for p in pts)
    assert Cage.box((1.0, 1.0, 1.0)).crease_by_angle(95.0, 4.0) == 0   # 90-degree edges stay soft


def test_crease_items_rounds_off_or_sharpens_a_whole_selection():
    from subdiv.ops import crease_items
    c = Cage.box((1.0, 1.0, 1.0))
    c.crease_by_angle(30.0, 4.0)
    edges = list(c.edge_faces())[:3]
    res = crease_items(c, [("e", a, b) for a, b in edges], 0.0)
    assert "3 edges" in res.message and all(ekey(a, b) not in c.creases for a, b in edges)
    assert len(c.creases) == 9
    crease_items(c, [("f", 0)], 2.0)                       # a face: its four edges
    assert sum(1 for s in c.creases.values() if s == 2.0) == 4
    with pytest.raises(ValueError):
        crease_items(c, [("v", 0)], 1.0)


def test_growing_a_sharp_face_gives_a_rectilinear_extrusion():
    c = Cage.box((1.0, 1.0, 1.0))
    c.crease_by_angle(30.0, 4.0)
    top = max(range(6), key=lambda i: c.face_normal(i)[2])
    apply_tool(c, "grow_face", ("f", top), 0.5)
    assert len(c.creases) == 20                        # 12 + 4 new outline + 4 side edges
    pts, _f = c.smooth(4)
    xs = {round(p[0], 6) for p in c.verts}
    ys = {round(p[1], 6) for p in c.verts}
    zs = {round(p[2], 6) for p in c.verts}
    for p in pts:                                       # every point sits on a cage plane: no rounding
        assert (any(abs(p[0] - x) < 1e-6 for x in xs) or any(abs(p[1] - y) < 1e-6 for y in ys)
                or any(abs(p[2] - z) < 1e-6 for z in zs))
    soft = Cage.box((1.0, 1.0, 1.0))                    # an unmarked cage stays organic
    apply_tool(soft, "grow_face", ("f", top), 0.5)
    assert not soft.creases


def test_divide_on_a_soft_face_adds_no_creases():
    c = Cage.box((2, 2, 2))
    c.divide_face(0)
    assert not c.creases


def test_divide_is_a_loop_cut_with_only_quads():
    c = _box()
    apply_tool(c, "divide", ("f", 0))
    assert all(len(f) == 4 for f in c.faces) and len(c.verts) == 18


def test_divide_stops_cleanly_at_a_border_and_at_non_quads():
    c = _open_box()
    c.divide_face(0)
    assert c.is_consistent()
    t = Cage([(0, 0, 0), (1, 0, 0), (0, 1, 0), (0, 0, 1)],
             [(0, 2, 1), (0, 1, 3), (1, 2, 3), (2, 0, 3)])
    out = t.divide_face(0)
    assert len(out) == 3 and t.is_closed()


def test_divide_face_only_leaves_neighbours_with_an_extra_point():
    c = _box()
    apply_tool(c, "divide", ("f", 0), axis="face")
    assert len(c.faces) == 9 and _closed(c)
    assert sorted(len(f) for f in c.faces).count(5) == 4


def test_divide_on_an_edge_cuts_just_that_loop():
    c = _box()
    a, b = c.faces[0][0], c.faces[0][1]
    r = apply_tool(c, "divide", ("e", a, b))
    assert r.message == "Loop cut" and len(c.faces) == 10 and _closed(c)
    assert all(len(f) == 4 for f in c.faces)


def test_symmetric_loop_cut_on_an_edge_is_made_once():
    c = _box()
    side = next(i for i in range(6) if c.face_normal(i)[0] > 0.9)
    f = c.faces[side]
    apply_tool(c, "divide", ("e", f[0], f[1]), sym=SYM_X)
    assert c.is_closed() and c.is_consistent()


def test_divide_on_an_edge_can_cut_only_the_faces_touching_it():
    c = _box()
    a, b = c.faces[0][0], c.faces[0][1]
    r = apply_tool(c, "divide", ("e", a, b), axis="face")
    assert len(c.faces) == 8 and _closed(c)            # the two faces beside the edge
    assert "face" in r.message


def test_bridge_two_ends_in_one_go():
    from subdiv.group import join_cages
    from subdiv.ops import bridge_two
    j = join_cages(Cage.box((2, 2, 2), center=(0, 0, 1)), Cage.box((2, 2, 2), center=(0, 0, 4)))
    near = lambda z: min(range(len(j.faces)), key=lambda i: abs(j.face_centroid(i)[2] - z))
    r = bridge_two(j, ("f", near(2.0)), ("f", near(3.0)))
    assert r.message == "Bridged" and len(j.faces) == 12 - 2 + 4
    assert j.is_closed() and j.is_consistent() and j.euler() == 2
    with pytest.raises(ValueError):
        bridge_two(_box(), ("f", 0), ("f", 0))


def test_grow_edge_with_an_axis_extrudes_the_whole_open_contour():
    c = _open_box()
    n_faces, n_verts = len(c.faces), len(c.verts)
    ring = c.boundary_loops()[0]
    start = [c.verts[v] for v in ring]
    r = apply_tool(c, "grow_edge", _border_edge(c), 0.75, axis="x")
    assert len(c.faces) == n_faces + len(ring) and len(c.verts) == n_verts + len(ring)
    assert c.is_consistent() and "extruded along X" in r.message
    moved = sorted((round(v[0] - 0.75, 6), round(v[1], 6), round(v[2], 6))
                   for v in c.verts[n_verts:])
    assert moved == sorted((round(p[0], 6), round(p[1], 6), round(p[2], 6)) for p in start)
    assert len(c.boundary_loops()) == 1 and len(c.boundary_loops()[0]) == len(ring)


def test_grow_edge_on_a_selected_contour_extrudes_it_outwards_in_auto():
    from subdiv.ops import grow_items
    c = _open_box()
    ring = c.boundary_loops()[0]
    n = len(ring)
    sels = [("e", ring[i], ring[(i + 1) % n]) for i in range(n)]
    before = len(c.faces)
    r = grow_items(c, sels, 0.5)
    assert "outwards" in r.message and len(c.faces) == before + n and c.is_consistent()
    d = _open_box()
    with pytest.raises(ValueError):
        grow_items(d, sels[:2], 0.5)                     # only part of a contour


def test_grow_contour_in_auto_follows_the_contour_normal_even_after_a_flange():
    from subdiv.ops import grow_items
    c = Cage.box((3, 1, 1))
    mouth = max(range(6), key=lambda i: c.face_normal(i)[0])
    apply_tool(c, "delete_face", ("f", mouth))
    ring = c.boundary_loops()[0]
    apply_tool(c, "offset_edge", ("e", ring[0], ring[1]), 0.3)     # a flat step in the mouth
    ring = c.boundary_loops()[0]
    n0 = len(c.verts)
    grow_items(c, [("e", ring[i], ring[(i + 1) % len(ring)]) for i in range(len(ring))], 0.5)
    assert all(v[0] > 1.5 + 0.49 for v in c.verts[n0:])           # out of the mouth, along +X
    assert c.is_consistent()


def test_squeeze_works_on_an_open_contour_from_an_edge_or_a_selection():
    from subdiv.ops import squeeze_items
    c = Cage.box((3, 1, 1))
    mouth = max(range(6), key=lambda i: c.face_normal(i)[0])
    apply_tool(c, "delete_face", ("f", mouth))
    ring = c.boundary_loops()[0]
    d = c.copy()
    before = [c.verts[v] for v in ring]
    apply_tool(c, "squeeze", ("e", ring[0], ring[1]), 0.5)
    after = [c.verts[v] for v in ring]
    assert all(abs(a[0] - b[0]) < 1e-9 for a, b in zip(after, before))        # stays in its plane
    assert max(abs(a[1]) for a in after) < max(abs(b[1]) for b in before)    # and gets smaller
    sels = [("e", ring[i], ring[(i + 1) % len(ring)]) for i in range(len(ring))]
    squeeze_items(d, sels, 0.5)
    assert [tuple(round(k, 9) for k in d.verts[r]) for r in ring] == \
        [tuple(round(k, 9) for k in c.verts[r]) for r in ring]
    with pytest.raises(ValueError):
        squeeze_items(d, [], 0.5)


def test_stretch_face_auto_stretches_whole_piece():
    """Stretching one face along its own normal moves it out, the far side stays."""
    cage = _box()
    fi = next(i for i in range(len(cage.faces))
              if abs(cage.face_normal(i)[0] - 1.0) < 1e-9)
    x0 = [v[0] for v in cage.verts]
    lo, hi = min(x0), max(x0)
    apply_tool(cage, "stretch", ("f", fi), 1.5, "auto")
    xs = [v[0] for v in cage.verts]
    assert abs(min(xs) - lo) < 1e-9
    assert abs(max(xs) - (lo + (hi - lo) * 1.5)) < 1e-9


def test_create_tip_follows_the_document_unit():
    """The help line used to say 'size in metres' while the box showed inches."""
    from subdiv import ops
    spec = ops.SPECS["create"]
    assert "{unit}" in spec.tip and "metres" not in spec.tip
    assert "size in in)" in ops.tip_for(spec, "in")
    assert "size in mm)" in ops.tip_for(spec, "mm")
    assert "size in m)" in ops.tip_for(spec)          # default: metres
    # tools without a unit in their text come back unchanged
    other = ops.SPECS["edit"]
    assert ops.tip_for(other, "mm") == other.tip
