# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 IngeTrazo contributors.
import pytest

from subdiv.edit import Cage, ekey


def _closed_ok(c):
    assert c.is_closed() and c.is_consistent() and c.euler() == 2


def test_box_is_closed_and_outward():
    b = Cage.box((2, 2, 2))
    _closed_ok(b)
    for fi in range(len(b.faces)):
        n, c = b.face_normal(fi), b.face_centroid(fi)
        assert n[0] * c[0] + n[1] * c[1] + n[2] * c[2] > 0


def test_extrude_face_keeps_cage_closed():
    b = Cage.box((2, 2, 2))
    top = [i for i in range(6) if b.face_normal(i)[2] > 0.9][0]
    new = b.extrude_face(top, 1.0)
    assert len(b.verts) == 12 and len(b.faces) == 10
    assert all(abs(b.verts[v][2] - 2.0) < 1e-9 for v in new)
    _closed_ok(b)


def test_inset_face_shrinks_it():
    b = Cage.box((2, 2, 2))
    top = [i for i in range(6) if b.face_normal(i)[2] > 0.9][0]
    new = b.inset_face(top, 0.5)
    assert len(b.faces) == 10
    xs = [b.verts[v][0] for v in new]
    assert max(xs) - min(xs) == pytest.approx(1.0)
    _closed_ok(b)


def test_divide_face_stays_watertight():
    b = Cage.box((2, 2, 2))
    out = b.divide_face(0)
    assert len(out) == 4 and len(b.faces) == 16       # the cuts run round the box
    assert all(len(f) == 4 for f in b.faces)
    _closed_ok(b)


def test_divide_twice_on_neighbours():
    b = Cage.box()
    b.divide_face(0)
    b.divide_face(2)
    _closed_ok(b)


def test_close_hole_restores_closed_cage():
    b = Cage.box()
    b.remove_faces([1])
    loops = b.boundary_loops()
    assert len(loops) == 1 and len(loops[0]) == 4
    b.close_hole(loops[0])
    _closed_ok(b)


def test_extrude_open_edge():
    q = Cage([(0, 0, 0), (1, 0, 0), (1, 1, 0), (0, 1, 0)], [(0, 1, 2, 3)])
    new = q.extrude_edges([0, 1], (0, -1, 0))
    assert len(new) == 2 and len(q.faces) == 2
    assert q.is_consistent()
    loops = q.boundary_loops()
    assert len(loops) == 1 and len(loops[0]) == 6


def test_extrude_interior_edge_is_rejected():
    b = Cage.box()
    with pytest.raises(ValueError):
        b.extrude_edges([0, 1], (0, 0, 1))


def test_offset_edges_pulls_in():
    q = Cage([(0, 0, 0), (2, 0, 0), (2, 2, 0), (0, 2, 0)], [(0, 1, 2, 3)])
    new = q.offset_edges([0, 1, 2, 3, 0], 0.5)
    xs = [q.verts[v][0] for v in new]
    assert max(xs) - min(xs) == pytest.approx(1.0)
    assert q.is_consistent()


def test_bridge_two_squares_makes_a_cube():
    bottom = [(0, 1, 0), (1, 1, 0), (1, 0, 0), (0, 0, 0)]
    top = [(0, 0, 1), (1, 0, 1), (1, 1, 1), (0, 1, 1)]
    c = Cage(bottom + top, [(0, 1, 2, 3), (4, 5, 6, 7)])
    la, lb = c.boundary_loops()
    new = c.bridge(la, lb)
    assert len(new) == 4
    _closed_ok(c)


def test_stretch_and_squeeze():
    b = Cage.box((2, 2, 2))
    b.stretch(range(8), 2.0, (0, 0, 1))
    zs = [v[2] for v in b.verts]
    assert max(zs) - min(zs) == pytest.approx(4.0)
    top = [i for i, v in enumerate(b.verts) if v[2] > 0]
    b.squeeze(top, 0.5, (0, 0, 1))
    xs = [b.verts[i][0] for i in top]
    assert max(xs) - min(xs) == pytest.approx(1.0)


def _corner_reach(verts):
    return max(abs(p[0]) + abs(p[1]) + abs(p[2]) for p in verts)


def test_creases_keep_corners_sharp():
    smooth = Cage.box((2, 2, 2))
    sharp = Cage.box((2, 2, 2))
    sharp.set_crease(sharp.edges(), 1)
    vs, _ = smooth.smooth(1)
    vc, _ = sharp.smooth(1)
    assert _corner_reach(vs) < 3.0 - 1e-6
    assert (1.0, 1.0, 1.0) in [tuple(round(c, 9) for c in p) for p in vc]


def test_crease_relaxes_after_its_levels():
    sharp = Cage.box((2, 2, 2))
    sharp.set_crease(sharp.edges(), 1)
    v1, _ = sharp.smooth(1)
    v3, _ = sharp.smooth(3)
    # level 1 still reaches the cube corner (3.0); once the crease has
    # relaxed the corner is rounded off, but flat faces stay on their planes
    assert _corner_reach(v1) == pytest.approx(3.0)
    assert _corner_reach(v3) < 3.0 - 1e-6


def test_longer_crease_stays_sharp_longer():
    a = Cage.box((2, 2, 2))
    b = Cage.box((2, 2, 2))
    a.set_crease(a.edges(), 1)
    b.set_crease(b.edges(), 3)
    va, _ = a.smooth(3)
    vb, _ = b.smooth(3)
    assert _corner_reach(vb) > _corner_reach(va)


def test_split_edge_keeps_crease_on_both_halves():
    b = Cage.box()
    e = b.edges()[0]
    b.set_crease([e], 2)
    m = b.split_edge(*e)
    assert b.creases[ekey(e[0], m)] == 2 and b.creases[ekey(m, e[1])] == 2
    assert ekey(*e) not in b.creases
    assert b.is_closed()


def test_set_crease_rejects_non_edge():
    b = Cage.box()
    with pytest.raises(ValueError):
        b.set_crease([(0, 7)], 1)


def test_prune_renumbers():
    b = Cage.box()
    b.remove_faces([0])
    b.prune()
    assert all(v < len(b.verts) for f in b.faces for v in f)


def test_orient_fixes_mixed_winding_and_points_outward():
    c = Cage.box((2, 2, 2))
    c.faces[0] = tuple(reversed(c.faces[0]))
    c.faces[3] = tuple(reversed(c.faces[3]))
    assert not c.is_consistent()
    assert c.orient() > 0
    _closed_ok(c)
    for fi in range(len(c.faces)):
        n, p = c.face_normal(fi), c.face_centroid(fi)
        assert n[0] * p[0] + n[1] * p[1] + n[2] * p[2] > 0     # ...and outward
    # all flipped inside-out: the whole piece is turned back outward
    inside_out = Cage([v for v in c.verts], [tuple(reversed(f)) for f in c.faces])
    inside_out.orient()
    for fi in range(len(inside_out.faces)):
        n, p = inside_out.face_normal(fi), inside_out.face_centroid(fi)
        assert n[0] * p[0] + n[1] * p[1] + n[2] * p[2] > 0


def test_crease_by_angle_keeps_a_box_boxy_and_a_curve_round():
    box = Cage.box((2, 2, 2))
    assert box.crease_by_angle(30, 4) == 12
    assert all(s == 4 for s in box.creases.values())
    import math
    n = 16                                    # a 16-sided prism: sides meet at 22.5 degrees
    ring = [(math.cos(2 * math.pi * i / n), math.sin(2 * math.pi * i / n)) for i in range(n)]
    verts = [(x, y, z) for z in (0.0, 1.0) for x, y in ring]
    faces = [(i, (i + 1) % n, n + (i + 1) % n, n + i) for i in range(n)]
    prism = Cage(verts, faces)
    prism.orient()
    assert prism.crease_by_angle(30, 4) == 0  # the open rims are boundaries, not creases
    assert prism.crease_by_angle(10, 4) == n  # a tighter threshold catches the side edges


def test_solid_report_accepts_a_closed_box_and_gives_its_volume():
    ok, problems, vol = Cage.box((2, 2, 2)).solid_report()
    assert ok and problems == [] and abs(vol - 8.0) < 1e-9


def test_solid_report_names_openings_and_keeps_volume_out():
    c = Cage.box((2, 2, 2))
    c.remove_faces([0])
    ok, problems, vol = c.solid_report()
    assert not ok and any("opening" in p for p in problems) and vol == 0.0


def test_solid_report_inside_out_still_gives_positive_volume():
    c = Cage.box((2, 2, 2))
    c.faces = [tuple(reversed(f)) for f in c.faces]
    ok, problems, vol = c.solid_report()
    assert ok and abs(vol - 8.0) < 1e-9 and c.signed_volume() < 0
    c.orient()
    assert c.signed_volume() > 0


def test_solid_report_flags_overlapping_points():
    c = Cage.box((2, 2, 2))
    c.verts.append(c.verts[0])
    c.faces[0] = tuple(len(c.verts) - 1 if v == 0 else v for v in c.faces[0])
    ok, problems, _v = c.solid_report()
    assert not ok


def test_components_and_extract_split_a_joined_cage():
    from subdiv.group import join_cages
    a = Cage.box((2, 2, 2), center=(0, 0, 1))
    b = Cage.box((1, 1, 1), center=(5, 0, 0))
    j = join_cages(a, b)
    parts = j.components()
    assert len(parts) == 2 and sorted(map(len, parts)) == [6, 6]
    pa, pb = (j.extract(f) for f in parts)
    assert pa.is_closed() and pb.is_closed() and len(pa.verts) == 8
    assert abs(pa.signed_volume() - 8.0) < 1e-9 and abs(pb.signed_volume() - 1.0) < 1e-9


def test_two_boxes_joined_are_two_components():
    from subdiv.group import join_cages
    j = join_cages(Cage.box((2, 2, 2), center=(0, 0, 1)), Cage.box((2, 2, 2), center=(0, 0, 4)))
    assert len(j.components()) == 2
