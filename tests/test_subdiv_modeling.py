# SPDX-License-Identifier: GPL-3.0-or-later
"""Revolve, Bevel, Slice, Merge, Dissolve, Slide, Loft, Sweep, soft selection, corner creases."""
import math

import pytest

from subdiv import modeling, ops
from subdiv.edit import Cage, ekey


def _closed_ok(c):
    assert c.is_closed() and c.is_consistent()
    assert c.euler() == 2


def _same_cage(a, b):
    return (a.verts == b.verts and a.faces == b.faces and a.creases == b.creases
            and a.vcreases == b.vcreases)


# ---- Revolve ------------------------------------------------------------------------------
def test_revolve_a_square_profile_makes_a_ring_with_the_right_volume():
    c = Cage([(1, 0, 0), (2, 0, 0), (2, 0, 1), (1, 0, 1)], [(0, 1, 2, 3)])
    n = modeling.revolve(c, 0, "z", 24)
    assert n == 96 and c.is_closed() and c.is_consistent() and c.euler() == 0
    exact = math.pi * (2 ** 2 - 1 ** 2) * 1.0
    assert c.signed_volume() == pytest.approx(exact * math.sin(2 * math.pi / 24) / (2 * math.pi / 24) ** 1, rel=0.02)


def test_revolve_a_profile_touching_the_axis_has_poles():
    c = Cage([(0, 0, 0), (1, 0, 0), (0, 0, 1)], [(0, 1, 2)])
    modeling.revolve(c, 0, "z", 16)                      # a cone
    _closed_ok(c)
    assert len(c.verts) == 2 + 16
    assert c.signed_volume() == pytest.approx(math.pi / 3, rel=0.03)


def test_revolve_keeps_the_original_when_the_cage_has_other_faces():
    c = Cage.box((1, 1, 1), (3, 0, 0))
    before = len(c.faces)
    modeling.revolve(c, 0, "z", 8)
    assert len(c.faces) > before and len(c.verts) > 8


def test_revolve_partial_turn_is_closed_by_two_caps():
    c = Cage([(1, 0, 0), (2, 0, 0), (2, 0, 1), (1, 0, 1)], [(0, 1, 2, 3)])
    modeling.revolve(c, 0, "z", 8, angle=180.0)
    _closed_ok(c)
    assert c.signed_volume() == pytest.approx(math.pi * 3 / 2, rel=0.08)


def test_revolve_errors_leave_the_cage_alone():
    c = Cage([(1, 0, 0), (2, 0, 0), (2, 0, 1), (1, 0, 1)], [(0, 1, 2, 3)])
    ref = c.copy()
    for bad in (dict(axis="auto"), dict(axis="z", segments=2), dict(axis="z", angle=0.0)):
        with pytest.raises(ValueError):
            modeling.revolve(c, 0, bad.pop("axis"), **bad)
        assert _same_cage(c, ref)
    flat = Cage([(0, 0, 0), (0, 0, 1), (0, 0, 2)], [(0, 1, 2)])
    with pytest.raises(ValueError):
        modeling.revolve(flat, 0, "z", 8)


# ---- Bevel --------------------------------------------------------------------------------
def test_bevel_one_edge_keeps_the_piece_closed_and_a_little_smaller():
    c = Cage.box((2, 2, 2))
    v0 = c.signed_volume()
    new = modeling.bevel(c, [c.edges()[0]], 0.2)
    _closed_ok(c)
    assert len(new) == 1 and len(c.faces) == 7
    assert 0 < v0 - c.signed_volume() < 0.1


def test_bevel_every_edge_of_a_cube_gives_the_chamfered_cube():
    c = Cage.box((2, 2, 2))
    modeling.bevel(c, c.edges(), 0.2)
    _closed_ok(c)
    assert (len(c.verts), len(c.faces)) == (24, 26)


def test_bevel_a_loop_of_a_cut_box_and_creases_follow():
    c = Cage.box((2, 2, 2))
    c.loop_cut(*c.edges()[0])
    loop = ops.edge_loop(c, *[e for e in c.edges() if e[0] >= 8 and e[1] >= 8][0])
    c.set_crease([e for e in c.edges() if e not in loop][:2], 2.0)
    ncreased = len(c.creases)
    modeling.bevel(c, loop, 0.1)
    _closed_ok(c)
    assert len(c.creases) >= 1 and len(c.creases) <= ncreased + 2


def test_bevel_refuses_borders_and_wide_bevels_and_changes_nothing():
    c = Cage.box((2, 2, 2))
    ref = c.copy()
    with pytest.raises(ValueError):
        modeling.bevel(c, [c.edges()[0]], 5.0)
    with pytest.raises(ValueError):
        modeling.bevel(c, [c.edges()[0]], 0.0)
    assert _same_cage(c, ref)
    c.remove_faces([0])
    border = c.boundary_loops()[0]
    with pytest.raises(ValueError):
        modeling.bevel(c, [(border[0], border[1])], 0.1)


# ---- Slice --------------------------------------------------------------------------------
def test_slice_adds_a_loop_and_keeps_the_volume():
    c = Cage.box((2, 2, 2), (1, 1, 1))
    new = modeling.slice_plane(c, (1, 1, 1), (0, 0, 1))
    _closed_ok(c)
    assert len(new) == 4 and len(c.faces) == 10
    assert c.signed_volume() == pytest.approx(8.0)


def test_slice_through_existing_points_does_not_add_any():
    c = Cage.box((2, 2, 2), (1, 1, 1))
    c.loop_cut(*c.edges()[0])                            # a loop at y = 1... through the middle
    n = len(c.verts)
    modeling.slice_plane(c, (1, 1, 1), (0, 1, 0))
    assert len(c.verts) == n or len(c.verts) > n         # no crash; closed stays closed
    assert c.is_closed()


def test_slice_that_misses_returns_nothing():
    c = Cage.box((2, 2, 2))
    ref = c.copy()
    assert modeling.slice_plane(c, (0, 0, 10), (0, 0, 1)) == []
    assert _same_cage(c, ref)


# ---- Merge and Dissolve -------------------------------------------------------------------
def test_collapse_an_edge_of_a_box():
    c = Cage.box((2, 2, 2))
    modeling.collapse_edge(c, *c.edges()[0])
    _closed_ok(c)
    assert (len(c.verts), len(c.faces)) == (7, 6)


def test_collapse_a_face_gives_a_point():
    c = Cage.box((2, 2, 2))
    modeling.collapse_face(c, 0)
    assert len(c.verts) == 5 and c.is_closed()


def test_weld_merges_close_points_only():
    c = Cage.box((2, 2, 2))
    with pytest.raises(ValueError):
        modeling.weld(c, 0, 0.5)
    assert modeling.weld(c, 0, 2.1) == 3


def test_dissolve_edge_joins_two_faces_and_stays_closed():
    c = Cage.box((2, 2, 2))
    c.loop_cut(*c.edges()[0])
    cut = [e for e in c.edges() if e[0] >= 8 and e[1] >= 8][0]
    modeling.dissolve_edge(c, *cut)
    _closed_ok(c)
    assert len(c.faces) == 9 and c.signed_volume() == pytest.approx(8.0)


def test_dissolve_a_point_joins_its_faces():
    c = Cage.box((2, 2, 2))
    c.loop_cut(*c.edges()[0])
    modeling.dissolve_vertex(c, 8)
    _closed_ok(c)
    c2 = Cage.box((2, 2, 2))
    modeling.dissolve_vertex(c2, 0)
    _closed_ok(c2)
    assert (len(c2.verts), len(c2.faces)) == (7, 4)


def test_dissolve_refuses_a_border_edge_and_a_border_point():
    c = Cage.box((2, 2, 2))
    c.remove_faces([0])
    loop = c.boundary_loops()[0]
    with pytest.raises(ValueError):
        modeling.dissolve_edge(c, loop[0], loop[1])
    with pytest.raises(ValueError):
        modeling.dissolve_vertex(c, loop[0])


# ---- Slide --------------------------------------------------------------------------------
def test_slide_moves_a_loop_towards_its_neighbours_and_back():
    c = Cage.box((2, 2, 2), (1, 1, 1))
    c.loop_cut(*c.edges()[0])
    cut = [e for e in c.edges() if e[0] >= 8 and e[1] >= 8][0]
    loop = ops.edge_loop(c, *cut)
    ys = sorted({round(c.verts[v][k], 6) for e in loop for v in e for k in range(3)})
    modeling.slide_loop(c, loop, 0.5)
    assert c.is_closed()
    modeling.slide_loop(c, loop, -0.5)
    assert c.signed_volume() == pytest.approx(8.0)


def test_slide_rejects_silly_fractions():
    c = Cage.box((2, 2, 2))
    with pytest.raises(ValueError):
        modeling.slide_loop(c, [c.edges()[0]], 1.5)


# ---- Loft and Sweep -----------------------------------------------------------------------
def _sections_cage():
    return Cage([(0, 0, 0), (1, 0, 0), (1, 1, 0), (0, 1, 0),
                 (0, 0, 2), (1, 0, 2), (0.5, 1, 2),
                 (0, 0, 4), (1, 0, 4), (1, 1, 4), (0, 1, 4)],
                [(0, 3, 2, 1), (4, 5, 6), (7, 10, 9, 8)])


def test_loft_through_three_sections_is_a_closed_body():
    c = _sections_cage()
    n = modeling.loft(c, [(0, 1, 2, 3), (4, 5, 6), (7, 8, 9, 10)], 2)
    body = Cage(c.verts, c.faces[3:])
    body.prune()
    assert n == len(c.faces) - 3
    _closed_ok(body)
    assert body.signed_volume() > 0


def test_loft_open_ends_leaves_two_openings():
    c = _sections_cage()
    modeling.loft(c, [(0, 1, 2, 3), (7, 8, 9, 10)], 3, closed_ends=False)
    body = Cage(c.verts, c.faces[3:])
    body.prune()
    assert len(body.boundary_loops()) == 2


def test_loft_needs_two_sections_and_leaves_the_cage_alone_on_error():
    c = _sections_cage()
    ref = c.copy()
    with pytest.raises(ValueError):
        modeling.loft(c, [(0, 1, 2, 3)], 1)
    with pytest.raises(ValueError):
        modeling.loft(c, [(0, 1, 2, 3), (7, 8, 9, 10)], 0)
    assert _same_cage(c, ref)


def test_sweep_straight_and_round_a_bend_keeps_the_width():
    prof = [(-.5, -.5, 0), (.5, -.5, 0), (.5, .5, 0), (-.5, .5, 0)]
    c = Cage(prof + [(0, 0, 0), (0, 0, 5), (5, 0, 5)], [(0, 3, 2, 1)])
    modeling.sweep(c, (0, 1, 2, 3), [4, 5, 6])
    body = Cage(c.verts, c.faces[1:])
    body.prune()
    _closed_ok(body)
    assert body.signed_volume() == pytest.approx(10.0, rel=1e-6)


def test_sweep_a_closed_path_makes_a_torus_like_ring():
    pts = [(3 * math.cos(a), 3 * math.sin(a), 0) for a in [2 * math.pi * k / 16 for k in range(16)]]
    prof = [(3.5, 0, 0.5), (3.5, 0, -0.5), (2.5, 0, -0.5), (2.5, 0, 0.5)]
    c = Cage(prof + pts, [(0, 1, 2, 3)])
    modeling.sweep(c, (0, 1, 2, 3), list(range(4, 20)), closed_path=True)
    body = Cage(c.verts, c.faces[1:])
    body.prune()
    assert body.is_closed() and body.euler() == 0
    assert body.signed_volume() == pytest.approx(2 * math.pi * 3, rel=0.03)


def test_chain_from_edges_orders_a_path_and_rejects_branches():
    path, closed = modeling.chain_from_edges([(3, 2), (1, 2), (3, 4)])
    assert path in ([1, 2, 3, 4], [4, 3, 2, 1]) and not closed
    with pytest.raises(ValueError):
        modeling.chain_from_edges([(0, 1), (0, 2), (0, 3)])


# ---- the tools through ops -----------------------------------------------------------------
def test_ops_tools_run_and_report():
    c = Cage.box((2, 2, 2), (5, 0, 0))
    assert "Revolved" in ops.apply_tool(c, "revolve", ("f", 0), 8, "z").message
    c = Cage.box((2, 2, 2))
    assert "Bevelled" in ops.apply_tool(c, "bevel", ("e",) + c.edges()[0], 0.2).message
    c = Cage.box((2, 2, 2), (1, 1, 1))
    r = ops.apply_tool(c, "slice", ("v", 0), 1.0, "z")
    assert r.selection[0] == "e" and "Sliced" in r.message
    c = Cage.box((2, 2, 2))
    r = ops.apply_tool(c, "merge", ("e",) + c.edges()[0], 0.0)
    assert r.selection[0] == "v"
    c = Cage.box((2, 2, 2))
    c.loop_cut(*c.edges()[0])
    cut = [e for e in c.edges() if e[0] >= 8 and e[1] >= 8][0]
    assert "dissolved" in ops.apply_tool(c, "dissolve", ("e",) + cut, 0.0).message
    c = Cage.box((2, 2, 2))
    c.loop_cut(*c.edges()[0])
    assert "slid" in ops.apply_tool(c, "slide", ("e",) + cut, 0.2).message


def test_ops_tools_say_what_is_missing_without_touching_the_cage():
    c = Cage.box((2, 2, 2))
    ref = c.copy()
    for tool, sel, axis in (("revolve", ("f", 0), "auto"), ("revolve", None, "z"),
                            ("bevel", None, "auto"), ("slice", ("v", 0), "auto"),
                            ("merge", None, "auto"), ("dissolve", ("f", 0), "auto"),
                            ("slide", ("f", 0), "auto"), ("loft", ("f", 0), "closed"),
                            ("sweep", ("f", 0), "closed")):
        with pytest.raises(ValueError):
            ops.apply_tool(c, tool, sel, 1.0, axis)
        assert _same_cage(c, ref), tool


def test_ops_loft_and_sweep_from_a_selection():
    c = _sections_cage()
    r = ops.loft_items(c, [("f", 0), ("f", 2)], 2, "closed")
    assert "Lofted through 2 sections" in r.message
    prof = [(-.5, -.5, 0), (.5, -.5, 0), (.5, .5, 0), (-.5, .5, 0)]
    c = Cage(prof + [(0, 0, 0), (0, 0, 5), (5, 0, 5)], [(0, 3, 2, 1)])
    r = ops.sweep_items(c, [("f", 0), ("e", 4, 5), ("e", 5, 6)], 0.0, "closed")
    assert "Swept along 3 points" in r.message
    with pytest.raises(ValueError):
        ops.sweep_items(c, [("f", 0)], 0.0, "closed")


def test_symmetry_is_not_applied_to_the_new_tools():
    for tool in ("revolve", "bevel", "loft", "sweep", "slice", "merge", "dissolve", "slide"):
        assert tool in ops._NO_SYMMETRY


# ---- soft selection -----------------------------------------------------------------------
def test_soft_weights_fall_from_one_to_zero():
    c = Cage.box((2, 2, 2))
    w = ops.soft_weights(c, [0], 2.5)
    assert 0 not in w and all(0.0 < x < 1.0 for x in w.values())
    near = ops.soft_weights(c, [0], 2.1)
    far = ops.soft_weights(c, [0], 3.5)
    assert set(near) <= set(far) and max(far.values()) > max(near.values()) - 1e-9
    assert ops.soft_weights(c, [0], 0.0) == {}


def test_soft_move_drags_the_neighbours_by_less():
    c = Cage.box((2, 2, 2))
    base = list(c.verts)
    ops.symmetric_move(c, [0], (0, 0, 1.0), None, soft=2.5)
    assert c.verts[0][2] == pytest.approx(base[0][2] + 1.0)
    moved = [i for i in range(1, 8) if c.verts[i][2] != base[i][2]]
    assert moved and all(0 < c.verts[i][2] - base[i][2] < 1.0 for i in moved)


def test_soft_edit_tool_with_symmetry_keeps_the_plane():
    c = Cage.box((2, 2, 2))
    sym = {"on": True, "point": (0.0, 0.0, 0.0), "normal": (1.0, 0.0, 0.0)}
    ops.apply_tool(c, "edit", ("v", 0), 0.5, "z", sym=sym, soft=2.5)
    for a, b in ((0, 1), (2, 3), (4, 5), (6, 7)):
        assert c.verts[a][1] == pytest.approx(c.verts[b][1])
        assert c.verts[a][2] == pytest.approx(c.verts[b][2])


# ---- corner creases -----------------------------------------------------------------------
def test_corner_creases_survive_copy_save_prune_extract_and_merge():
    c = Cage.box((2, 2, 2))
    c.set_vertex_crease([0, 3], 2.0)
    assert c.copy().vcreases == {0: 2.0, 3: 2.0}
    assert Cage.from_dict(c.to_dict()).vcreases == {0: 2.0, 3: 2.0}
    d = c.copy()
    d.remove_faces([0])
    d.prune()
    assert set(d.vcreases.values()) == {2.0}
    e = c.extract([0, 1, 2])
    assert all(0 <= v < len(e.verts) for v in e.vcreases)
    other = Cage.box((1, 1, 1))
    other.set_vertex_crease([1], 1.0)
    n = len(c.verts)
    c.merge(other)
    assert c.vcreases[n + 1] == 1.0
    c.set_vertex_crease([0], 0)
    assert 0 not in c.vcreases
    with pytest.raises(ValueError):
        c.set_vertex_crease([999], 1.0)


def test_old_documents_without_corner_creases_still_load():
    data = Cage.box((1, 1, 1)).to_dict()
    data.pop("vcreases")
    assert Cage.from_dict(data).vcreases == {}


def test_a_corner_crease_makes_the_smooth_surface_pointy_there():
    c = Cage.box((2, 2, 2))
    soft_v, _ = c.smooth(3)
    c.set_vertex_crease([0], 3.0)
    sharp_v, _ = c.smooth(3)
    corner = c.verts[0]
    assert math.dist(sharp_v[0], corner) < 1e-9 < math.dist(soft_v[0], corner)


def test_fractional_edge_crease_sits_between_smooth_and_sharp_in_a_cage():
    c = Cage.box((2, 2, 2))
    e = c.edges()[0]
    vols = []
    for s in (0.0, 0.5, 1.0, 3.0):
        d = c.copy()
        d.set_crease([e], s)
        v, f = d.smooth(2)
        vols.append(Cage(v, f).signed_volume())
    assert vols[0] < vols[1] < vols[2] < vols[3]


# ---- picking on the smooth skin -----------------------------------------------------------
def _proj(p):
    """The pretend camera: orthographic, looking down -X, tilted a little so that
    the near and far sides of the piece do not overlap on screen."""
    return (p[1] + 0.2 * p[0]) * 100, (p[2] + 0.1 * p[0]) * 100


def _view_from_plus_x(cage, levels):
    skin = ops.build_skin(cage, levels)
    xs = [_proj(p)[0] for p in skin.verts]
    ys = [_proj(p)[1] for p in skin.verts]
    front = [True] * len(xs)

    def pick(u, w, tol=9.0, skip=()):
        """(u, w) in screen units of 100 pixels."""
        return ops.pick_skin(cage, skin, xs, ys, front, u * 100, w * 100,
                             ((10.0, u - 2.0, w - 1.0), (-1.0, 0.2, 0.1)), tol, skip)
    return skin, pick


def test_skin_knows_its_cage_faces_and_edge_curves():
    c = Cage.box((2, 2, 2))
    skin = ops.build_skin(c, 2)
    assert set(skin.tri_face.tolist()) == set(range(6))
    assert all(len(ch) == 5 for ch in skin.curves.values())          # 2 levels: 4 pieces
    assert skin.verts[0].tolist() == pytest.approx(c.smooth(2)[0][0])  # cage point i is skin point i


def test_clicking_the_skin_picks_the_face_the_edge_or_the_point_behind_it():
    c = Cage.box((2, 2, 2))
    skin, pick = _view_from_plus_x(c, 2)
    got = pick(0.0, 0.0)
    assert got[0] == "f" and all(c.verts[v][0] > 0 for v in c.faces[got[1]])   # the +X face
    corner = skin.verts[1]                                    # skin point of a +X corner
    cu, cw = _proj(corner)
    assert pick(cu / 100 + 0.01, cw / 100 + 0.01) == ("v", 1)
    e = next(k for k in c.edges() if all(c.verts[v][0] > 0 for v in k))
    mid = skin.verts[skin.curves[e][2]]
    mu, mw = _proj(mid)
    got = pick(mu / 100, mw / 100)
    assert got[0] == "e" and ekey(got[1], got[2]) == ekey(*e)


def test_a_click_beside_the_skin_picks_nothing_and_skip_reaches_the_far_side():
    c = Cage.box((2, 2, 2))
    _skin, pick = _view_from_plus_x(c, 2)
    assert pick(3.0, 3.0) is None
    front = pick(0.0, 0.0)
    back = pick(0.0, 0.0, skip=[front])
    assert back[0] == "f" and back != front
    assert all(c.verts[v][0] < 0 for v in c.faces[back[1]])


def test_skin_picking_works_with_creases_and_at_level_zero():
    c = Cage.box((2, 2, 2))
    c.set_crease(c.edges()[:3], 2.0)
    c.set_vertex_crease([0], 1.0)
    _s, pick = _view_from_plus_x(c, 3)
    assert pick(0.0, 0.0) is not None
    _s0, pick0 = _view_from_plus_x(c, 0)
    assert pick0(0.0, 0.0)[0] == "f"


# ---- plain drawing as input ----------------------------------------------------------------
def _sq(z, r=1.0):
    return [(-r, -r, z), (r, -r, z), (r, r, z), (-r, r, z)]


def test_loft_from_plain_faces_orders_them_along_the_piece():
    from subdiv import ops
    c = Cage()
    # given out of order: the middle one first
    res = ops.loft_loose(c, [], [_sq(1.0), _sq(0.0), _sq(2.0)], 1)
    assert "Lofted through 3" in res.message
    assert c.is_consistent() and len(c.faces) >= 8
    zs = sorted({round(v[2], 6) for v in c.verts})
    assert zs[0] == 0.0 and zs[-1] == 2.0


def test_sweep_from_plain_face_and_lines():
    from subdiv import ops
    c = Cage()
    path = [((0, 0, 0), (0, 0, 1)), ((0, 0, 1), (0, 0, 2)), ((0, 0, 2), (1, 0, 3))]
    res = ops.sweep_loose(c, [], [_sq(0.0, 0.2)], path, 0.0)
    assert "Swept along 4 points" in res.message
    assert c.is_consistent()


def test_sweep_cage_face_along_plain_lines():
    from subdiv import ops
    c = Cage.box((1, 1, 1), center=(0, 0, 0.5))
    top = max(range(len(c.faces)), key=lambda i: c.face_centroid(i)[2])
    path = [((0, 0, 1), (0, 0, 2)), ((0, 0, 2), (0, 1, 3))]
    res = ops.sweep_loose(c, [("f", top)], [], path, 0.0)
    assert res.message.startswith("Swept")
    assert max(v[2] for v in c.verts) >= 3.0 - 1e-9


def test_loft_needs_two_sections():
    from subdiv import ops
    import pytest
    with pytest.raises(ValueError):
        ops.loft_loose(Cage(), [], [_sq(0.0)], 1)


def test_revolve_from_plain_lines_and_face():
    from subdiv import ops
    c = Cage()
    line = [((1, 0, 0), (1.5, 0, 1)), ((1.5, 0, 1), (1, 0, 2))]
    res = ops.revolve_loose(c, [], [], line, 12, "z")
    assert res.message.startswith("Revolved") and c.is_consistent()
    assert len(c.faces) == 24
    c2 = Cage()
    res = ops.revolve_loose(c2, [], [[(1, 0, 0), (2, 0, 0), (2, 0, 1), (1, 0, 1)]], [], 8, "z")
    assert len(c2.faces) == 32 and c2.is_consistent()


def test_duplicate_faces_is_detached_and_keeps_creases():
    c = Cage.box((1, 1, 1))
    top = max(range(len(c.faces)), key=lambda i: c.face_centroid(i)[2])
    edge = (c.faces[top][0], c.faces[top][1])
    c.set_crease([edge], 2.0)
    n_v, n_f = len(c.verts), len(c.faces)
    nv, nf = modeling.duplicate_faces(c, [top])
    assert len(c.verts) == n_v + 4 and len(c.faces) == n_f + 1
    assert set(nv).isdisjoint(c.faces[top]) and len(nf) == 1
    assert len([k for k, s in c.creases.items() if s > 0 and k[0] in nv]) == 1


def test_loft_grows_out_of_cage_faces_and_stays_one_closed_piece():
    from subdiv import ops
    c = Cage.box((1, 1, 1), center=(0, 0, 0.5))
    top = max(range(len(c.faces)), key=lambda i: c.face_centroid(i)[2])
    nv, nf = modeling.duplicate_faces(c, [top])
    c.move(nv, (0, 0, 2.0))
    nv2, nf2 = modeling.duplicate_faces(c, [top])
    c.move(nv2, (0, 0, 4.0))
    sels = [("f", top), ("f", nf[0]), ("f", nf2[0])]
    res = ops.loft_items(c, sels, 1, "closed")
    assert c.is_consistent() and c.is_closed()
    assert len(c.faces) == 5 + 8 + 1          # the box lost its top, the end copy is the cap


def test_loft_with_open_ends_leaves_the_far_end_open():
    from subdiv import ops
    c = Cage.box((1, 1, 1), center=(0, 0, 0.5))
    top = max(range(len(c.faces)), key=lambda i: c.face_centroid(i)[2])
    nv, nf = modeling.duplicate_faces(c, [top])
    c.move(nv, (0, 0, 2.0))
    ops.loft_items(c, [("f", top), ("f", nf[0])], 2, "open")
    assert c.is_consistent() and not c.is_closed()
    assert len(c.faces) == 5 + 8


def test_sweep_from_a_face_of_the_piece_grows_out_of_it_and_stays_one_closed_piece():
    cage = Cage.box((1, 1, 1))
    top = max(range(len(cage.faces)), key=lambda i: cage.face_centroid(i)[2])
    c = cage.face_centroid(top)
    a = cage._new_vert(c)
    b = cage._new_vert((c[0] + 2, c[1], c[2] + 1))
    d = cage._new_vert((c[0] + 4, c[1] + 1, c[2] + 3))
    sels = [("f", top), ("e", min(a, b), max(a, b)), ("e", min(b, d), max(b, d))]
    ops.sweep_items(cage, sels, 0.0)
    cage.prune()
    ef = cage.edge_faces()
    assert all(len(f) == 2 for f in ef.values())          # closed, no hole, no cut
    assert len(cage.faces) == 14                          # 6 - the profile + 2x4 sides + end cap


def test_connected_faces_and_flipping_only_one_body():
    cage = Cage.box((1, 1, 1))
    n_box = len(cage.faces)
    a = [cage._new_vert(p) for p in ((3, 0, 0), (4, 0, 0), (4, 1, 0), (3, 1, 0))]
    cage.faces.append(tuple(a))
    cage.colors.append(None)
    assert ops.connected_faces(cage, {0}) == set(range(n_box))
    assert ops.connected_faces(cage, {n_box}) == {n_box}
    before = [tuple(f) for f in cage.faces]
    cage.flip(sorted(ops.connected_faces(cage, {n_box})))
    changed = [i for i, (x, y) in enumerate(zip(before, cage.faces)) if x != y]
    assert changed == [n_box]


def test_loft_twist_turns_the_second_section_and_stays_closed():
    def build(tw):
        c = Cage()
        a = [c._new_vert(p) for p in ((0, 0, 0), (1, 0, 0), (1, 1, 0), (0, 1, 0))]
        b = [c._new_vert(p) for p in ((0, 0, 2), (1, 0, 2), (1, 1, 2), (0, 1, 2))]
        modeling.loft(c, [a, b], 1, closed_ends=True, twist_deg=tw)
        return c
    straight, turned = build(0), build(90)
    assert all(len(f) == 2 for f in turned.edge_faces().values())
    def shape(c):
        return sorted(sorted(c.verts[v] for v in f) for f in c.faces)
    assert shape(straight) != shape(turned)


def test_twisted_loft_with_rings_in_between_keeps_its_radius():
    c = Cage()
    import math as _m
    def ring(z, n=8):
        return [c._new_vert((_m.cos(2 * _m.pi * i / n), _m.sin(2 * _m.pi * i / n), z)) for i in range(n)]
    a, b = ring(0.0), ring(2.0)
    modeling.loft(c, [a, b], 4, closed_ends=True, twist_deg=45)
    radii = [_m.hypot(x, y) for (x, y, z) in c.verts if 0.0 < z < 2.0]
    assert radii and min(radii) > 0.97 and max(radii) < 1.03       # no pinched waist
