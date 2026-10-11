# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 IngeTrazo contributors.
"""Keep a subdivision cage inside a group, and rebuild its surface from it.

A subdivision group is an ordinary IngeTrazo group whose mesh holds the
smoothed surface (triangles, so the viewport, picking and exports see plain
geometry) and whose ``ext["subdiv"]`` holds the control cage. Editing the cage
and calling :func:`build_group` again regenerates the surface; saving the
document saves both, with no change to the ``.igz`` format.

Nothing here imports Qt: the caller passes the ``Group``, ``Mesh`` and vector
classes in, so the logic is testable without a window.

Look of the surface (``lines``):
  "cage"  only the cage's own edges are drawn, as curved panel lines on the
          smooth skin (the default; reads like a hand-modelled SubD)
  "all"   every edge of the smoothed mesh (a wireframe of the result)
  "none"  no edge lines at all
Cage faces painted with :meth:`Cage.set_color` carry their colour onto the
surface.
"""
from __future__ import annotations

import math
from types import SimpleNamespace

from . import follow as subdiv_follow
from .edit import Cage, ekey

KEY = "subdiv"
LINES = ("cage", "all", "none")


def _flat_loop(det, quads, tol):
    """If the output quads of one cage face lie in a single plane and form one
    simple patch, the loop of vertex indices around it (wound like the quads);
    otherwise None."""
    verts = det.verts
    f0 = det.faces[quads[0]]
    n = _newell3([verts[i] for i in f0])
    ln = math.sqrt(n[0] * n[0] + n[1] * n[1] + n[2] * n[2])
    if ln < 1e-18:
        return None
    n = (n[0] / ln, n[1] / ln, n[2] / ln)
    p0 = verts[f0[0]]
    for q in quads:
        for i in det.faces[q]:
            v = verts[i]
            if abs((v[0] - p0[0]) * n[0] + (v[1] - p0[1]) * n[1] + (v[2] - p0[2]) * n[2]) > tol:
                return None
    directed = set()
    for q in quads:
        f = det.faces[q]
        for i, a in enumerate(f):
            directed.add((a, f[(i + 1) % len(f)]))
    nxt = {}
    for (a, b) in directed:
        if (b, a) not in directed:
            if a in nxt:
                return None                              # the border pinches
            nxt[a] = b
    if not nxt:
        return None
    start = next(iter(nxt))
    loop, cur = [start], nxt[start]
    while cur != start:
        loop.append(cur)
        cur = nxt.get(cur)
        if cur is None or len(loop) > len(nxt):
            return None
    return loop if len(loop) == len(nxt) else None       # more than one border: a hole


def _newell3(pts):
    x = y = z = 0.0
    for i, p in enumerate(pts):
        q = pts[(i + 1) % len(pts)]
        x += (p[1] - q[1]) * (p[2] + q[2])
        y += (p[2] - q[2]) * (p[0] + q[0])
        z += (p[0] - q[0]) * (p[1] + q[1])
    return (x, y, z)


def _straight(a, p, b) -> bool:
    """Is ``p`` on the straight run from ``a`` to ``b`` (and between them)?"""
    u = (p[0] - a[0], p[1] - a[1], p[2] - a[2])
    w = (b[0] - p[0], b[1] - p[1], b[2] - p[2])
    lu = math.sqrt(u[0] ** 2 + u[1] ** 2 + u[2] ** 2)
    lw = math.sqrt(w[0] ** 2 + w[1] ** 2 + w[2] ** 2)
    if lu < 1e-18 or lw < 1e-18:
        return False
    cr = (u[1] * w[2] - u[2] * w[1], u[2] * w[0] - u[0] * w[2], u[0] * w[1] - u[1] * w[0])
    sin = math.sqrt(cr[0] ** 2 + cr[1] ** 2 + cr[2] ** 2) / (lu * lw)
    return sin < 1e-7 and (u[0] * w[0] + u[1] * w[1] + u[2] * w[2]) > 0


def _plane_of(det, loop):
    pts = [det.verts[i] for i in loop]
    n = _newell3(pts)
    ln = math.sqrt(n[0] * n[0] + n[1] * n[1] + n[2] * n[2])
    if ln < 1e-18:
        return None
    n = (n[0] / ln, n[1] / ln, n[2] / ln)
    return n, n[0] * pts[0][0] + n[1] * pts[0][1] + n[2] * pts[0][2]


def _flat_regions(det, colors=None) -> list:
    """``[(cage faces, loop)]`` for every flat patch of the smoothed surface.
    Neighbouring cage faces that lie in the same plane (a box face cut up with
    Divide, say) join into ONE patch, and the points that only sit on a
    straight run are left out (when no curved neighbour needs them), so a box
    face comes out as one clean polygon."""
    pts = det.verts
    if not pts:
        return []
    ext = max(max(p[k] for p in pts) - min(p[k] for p in pts) for k in range(3)) or 1.0
    tol = 1e-7 * ext
    by: dict = {}
    for qi, src in enumerate(det.source):
        by.setdefault(src, []).append(qi)
    loops, planes = {}, {}
    for src, qs in by.items():
        loop = _flat_loop(det, qs, tol)
        if loop:
            loops[src] = loop
            planes[src] = _plane_of(det, loop)
    # cage faces that touch along an edge of the output, in the same plane
    owner: dict = {}
    parent = {src: src for src in loops}

    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    for qi, f in enumerate(det.faces):
        src = det.source[qi]
        if src not in loops:
            continue
        for i, a in enumerate(f):
            key = (a, f[(i + 1) % len(f)]) if a < f[(i + 1) % len(f)] else (f[(i + 1) % len(f)], a)
            o = owner.setdefault(key, src)
            if o == src or planes[o] is None or planes[src] is None:
                continue
            (n1, d1), (n2, d2) = planes[o], planes[src]
            same = n1[0] * n2[0] + n1[1] * n2[1] + n1[2] * n2[2] > 1.0 - 1e-9
            if same and abs(d1 - d2) < tol * 10 and (colors is None or colors[o] == colors[src]):
                parent[find(o)] = find(src)
    groups: dict = {}
    for src in loops:
        groups.setdefault(find(src), []).append(src)
    regions = []
    for srcs in groups.values():
        if len(srcs) > 1:
            loop = _flat_loop(det, [q for s_ in srcs for q in by[s_]], tol)
            if loop:
                regions.append((srcs, loop))
                continue
        regions.extend(([s_], loops[s_]) for s_ in srcs)
    curved = {i for qi, f in enumerate(det.faces) if det.source[qi] not in loops for i in f}
    straight: dict = {}
    for _, loop in regions:
        m = len(loop)
        for i, v in enumerate(loop):
            ok = _straight(pts[loop[i - 1]], pts[v], pts[loop[(i + 1) % m]])
            straight[v] = straight.get(v, True) and ok
    drop = {v for v, ok in straight.items() if ok and v not in curved}
    out = []
    for srcs, loop in regions:
        kept = [v for v in loop if v not in drop]
        out.append((srcs, kept if len(kept) >= 3 else loop))
    return out


def fill_mesh(mesh, cage: Cage, levels: int, vec3, lines: str = "cage",
              merge_flat: bool = False) -> list:
    """Add the smoothed cage to ``mesh`` as triangles. Returns the faces added.
    With ``merge_flat`` every flat patch (a box face) becomes ONE polygon
    instead of hundreds of triangles: far lighter for the ordinary tools that
    take the group over once it is finished."""
    if lines not in LINES:
        raise ValueError(f"lines must be one of {LINES}")
    det = cage.smooth_detailed(levels, line_level=0)
    added, quad_of, tri_of, poly_of = [], {}, {}, {}
    regions = _flat_regions(det, cage.colors) if merge_flat else []
    flat = {src for srcs, _ in regions for src in srcs}
    for srcs, loop in regions:
        color = cage.colors[srcs[0]]
        face = mesh.add_face([vec3(*det.verts[k]) for k in loop])
        if color is not None:
            face.attrs["color"] = tuple(color)
        added.append(face)
        poly_of[face] = loop
    for qi, f in enumerate(det.faces):             # quads are not planar:
        if det.source[qi] in flat:
            continue
        color = cage.colors[det.source[qi]]
        for i in range(1, len(f) - 1):             # fan-triangulate each face
            tri = (f[0], f[i], f[i + 1])
            face = mesh.add_face([vec3(*det.verts[k]) for k in tri])
            if color is not None:
                face.attrs["color"] = tuple(color)
            added.append(face)
            quad_of[face], tri_of[face] = qi, tri

    vindex = {}                                     # mesh vertex -> output index
    for face, ids in list(tri_of.items()) + list(poly_of.items()):
        for vertex, k in zip(face.loop, ids):
            vindex[vertex] = k

    mine = set(added)
    for e in mesh.edges:
        fl = e.faces
        if not fl or any(face not in mine for face in fl):
            continue
        if any(face in poly_of for face in fl):     # the border of a flat patch is a real edge
            if lines == "none":
                e.soft = True
            continue
        if len(fl) == 2 and quad_of[fl[0]] == quad_of[fl[1]]:
            e.soft = True                           # a triangulation diagonal
        elif lines == "none":
            e.soft = True
        elif lines == "cage":
            a, b = vindex.get(e.v0), vindex.get(e.v1)
            if a is None or b is None or ekey(a, b) not in det.lines:
                e.soft = True
    return added


MAX_CAGE_FACES = 7000


def cage_from_mesh(mesh, max_faces: int = MAX_CAGE_FACES):
    """Read any IngeTrazo mesh (a group's, or one built by another tool) as a
    control cage: shared vertices stay shared, face colours come along, the
    winding is made consistent. Returns ``(cage, holes_ignored)`` — a face's
    inner holes cannot be part of a cage. Raises ValueError when the mesh is
    empty or too dense to be a sensible cage."""
    index: dict = {}
    verts: list = []
    faces: list = []
    colors: list = []
    holes = 0
    for face in mesh.faces:
        loop = face.loop
        if len(loop) < 3:
            continue
        ids = []
        for v in loop:
            k = index.get(v)
            if k is None:
                p = v.position
                k = index[v] = len(verts)
                verts.append((p.x(), p.y(), p.z()))
            ids.append(k)
        if len(set(ids)) < 3:
            continue
        faces.append(tuple(ids))
        col = face.attrs.get("color") if getattr(face, "attrs", None) else None
        colors.append(tuple(col[:3]) if col else None)
        if getattr(face, "hole_loops", None):
            holes += 1
    if not faces:
        raise ValueError("That group has no faces to convert")
    if len(faces) > max_faces:
        raise ValueError(f"That group has {len(faces)} faces: a cage should be coarse "
                         f"(under {max_faces}). Simplify it first.")
    cage = Cage(verts, faces, None, colors)
    cage.orient()
    return cage, holes


def triangle_count(cage: Cage, levels: int) -> int:
    """How many triangles the smoothed surface will have (without building it)."""
    if levels <= 0:
        return sum(max(len(f) - 2, 0) for f in cage.faces)
    quads = sum(len(f) for f in cage.faces) * 4 ** (levels - 1)
    return 2 * quads


def auto_levels(cage: Cage, budget: int = 25000, max_level: int = 4) -> int:
    """The smoothest level (0..max_level) whose surface stays within ``budget``
    triangles — dense where the cage is simple, lighter where it is big."""
    best = 0
    for lv in range(1, max_level + 1):
        if triangle_count(cage, lv) <= budget:
            best = lv
    return best


def build_group(cage: Cage, levels: int, Group, Mesh, vec3,
                name: str | None = None, lines: str = "cage", merge_flat: bool = False):
    """A new group holding the smoothed surface, with the cage in ``ext``."""
    group = Group(Mesh(), name=name) if name else Group(Mesh())
    fill_mesh(group.mesh, cage, levels, vec3, lines, merge_flat)
    group.ext = make_ext(cage, levels, lines, group.mesh)
    return group


def mesh_positions(mesh) -> list:
    """Vertex positions of a mesh, in the mesh's own order ([] if it has none)."""
    verts = getattr(mesh, "vertices", None)
    if verts is None:
        return []
    out = []
    for v in verts:
        p = v.position
        out.append((p.x(), p.y(), p.z()))
    return out


def make_ext(cage: Cage, levels: int, lines: str, mesh) -> dict:
    """The ``ext`` payload of a SubD group: the cage, its look, and what is
    needed to carry the cage along when the group is moved (see
    :mod:`subdiv.follow`)."""
    data = {"cage": cage.to_dict(), "levels": int(levels), "lines": lines}
    ref = subdiv_follow.make_ref(mesh_positions(mesh))
    if ref is not None:
        data["ref"] = ref
    return {KEY: data}


def read(group):
    """``(cage, levels, lines)`` stored in ``group``, or ``None`` if it has none."""
    data = (getattr(group, "ext", None) or {}).get(KEY)
    if not data:
        return None
    lines = data.get("lines") or ("cage" if data.get("soft", True) else "all")
    return Cage.from_dict(data["cage"]), int(data.get("levels", 2)), lines


def is_subdiv(group) -> bool:
    return read(group) is not None


class SwapGroup:
    """Undoable replacement of one group by another in ``scene.groups`` (or an
    addition when ``old`` is None). It deliberately does not inherit from the
    app's ``Command``: it only needs ``do`` and ``undo``, which keeps it
    testable without Qt — the plugin mixes it with ``Command``.

    Unlike a console script, undo puts the OLD group back."""

    def __init__(self, old, new) -> None:
        self.old, self.new = old, new

    def do(self, scene) -> None:
        if self.old is None:
            scene.groups.append(self.new)
        else:
            scene.groups[scene.groups.index(self.old)] = self.new
        scene.version += 1

    def undo(self, scene) -> None:
        if self.old is None:
            scene.groups.remove(self.new)
        else:
            scene.groups[scene.groups.index(self.new)] = self.old
        scene.version += 1


def carry_over(old, new) -> None:
    """Give ``new`` the identity and attributes ``old`` had as a container
    (name, layer, BIM tag, visibility, paint, uid), so a rebuild keeps them."""
    new.name, new.layer, new.ifc = old.name, old.layer, old.ifc
    new.hidden, new.material, new.uid = old.hidden, old.material, old.uid


class StateCache:
    """Reads SubD groups' cages, carried along with the groups.

    ``get(group, stamp)`` returns ``(cage, levels, lines)`` or None. The cage
    is the stored one moved/rotated/scaled the way the group's surface has
    been since it was built. The work is redone only when ``stamp`` (the
    scene's version) or the group's mesh/ext object changes."""

    def __init__(self) -> None:
        self._entries: dict = {}

    def get(self, group, stamp=None):
        ext = getattr(group, "ext", None)
        data = ext.get(KEY) if ext else None
        if not data:
            return None
        e = self._entries.get(group.uid)
        if e is None or e.ext is not ext:
            cage, levels, lines = read(group)
            e = SimpleNamespace(ext=ext, base=cage, levels=levels, lines=lines,
                                ref=data.get("ref"), key=None, cur=cage)
            self._entries[group.uid] = e
        if e.ref:
            key = (id(group.mesh), stamp)
            if stamp is None or key != e.key:
                e.key = key
                aff = subdiv_follow.fit(e.ref, mesh_positions(group.mesh))
                if aff is None:
                    e.cur = e.base
                else:
                    e.cur = e.base.copy()
                    e.cur.transform(aff)
        return e.cur, e.levels, e.lines


class SetExt:
    """Undoable replacement of a group's ``ext`` (no mesh rebuild): used for
    settings such as the symmetry plane. Same do/undo shape as SwapGroup."""

    def __init__(self, group, new_ext) -> None:
        self.group, self.new, self.old = group, new_ext, None

    def do(self, scene) -> None:
        if self.old is None:
            self.old = self.group.ext
        self.group.ext = self.new
        scene.version += 1

    def undo(self, scene) -> None:
        self.group.ext = self.old
        scene.version += 1


class JoinGroups:
    """Undoable merge of two groups into ``new``: ``keep`` is replaced by it
    and ``gone`` is removed; undo puts both back where they were."""

    def __init__(self, keep, gone, new) -> None:
        self.keep, self.gone, self.new = keep, gone, new
        self._at = None

    def do(self, scene) -> None:
        i, j = scene.groups.index(self.keep), scene.groups.index(self.gone)
        self._at = (i, j)
        scene.groups[i] = self.new
        del scene.groups[j]
        scene.version += 1

    def undo(self, scene) -> None:
        i, j = self._at
        scene.groups[scene.groups.index(self.new)] = self.keep
        scene.groups.insert(j, self.gone)
        scene.version += 1


class SplitGroup:
    """Undoable split of one group into several (``news``, in order, taking
    ``old``'s place); undo puts ``old`` back."""

    def __init__(self, old, news) -> None:
        self.old, self.news = old, list(news)
        self._at = None

    def do(self, scene) -> None:
        i = scene.groups.index(self.old)
        self._at = i
        scene.groups[i:i + 1] = self.news
        scene.version += 1

    def undo(self, scene) -> None:
        i = scene.groups.index(self.news[0])
        scene.groups[i:i + len(self.news)] = [self.old]
        scene.version += 1


def join_cages(a: Cage, b: Cage) -> Cage:
    """Two cages as one (kept apart until a Bridge joins them)."""
    out = a.copy()
    out.merge(b)
    return out
