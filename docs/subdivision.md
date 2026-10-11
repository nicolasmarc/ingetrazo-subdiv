# Subdivision modelling (SubD)

Model a smooth surface from a coarse control **cage**: push, pinch, crease
and divide a few faces, and the Catmull-Clark skin follows. The SubD side
panel is an extension (the `subdiv/` package); the geometry and the tool logic
live in pure-Python modules that are tested without a window.

## Using it

1. Open the **SubD** tab and press **Apply** on *Create*: a box cage appears
   with its smooth surface. Tick **Create with sharp edges** first to get a
   crisp, rectilinear box instead of a rounded block (the edges stay sharp
   when the *Crease edges over* angle, 30 by default, is below 90).
2. With the **Select** tool, click a point, an edge or a face of the cage.
3. **Drag** it to move it freely (the axis box next to the value constrains
   the drag; `Esc` cancels), or pick one of the fourteen tools, set its value
   and press **Apply**.

Every step is one undo step; undo puts the previous surface back.

| Tool | Needs | What it does |
|------|-------|--------------|
| Create | – | New box cage (size in metres), with its lower corner on the origin |
| Edit cage | point, edge or face | Move it along an axis |
| Crease | edge or face | Keep edges sharp for N subdivision levels (0 clears) |
| Grow F | face | Push the face out along its normal |
| Grow E | open edge | Extend an open edge into a new strip; with the whole contour selected (click an edge again) it goes outwards; with X, Y or Z chosen, the whole open contour is extruded along that axis |
| Stretch | point, edge or face | Scale the selection along an axis. A face stretched along its own normal (Auto) stretches the whole piece that way, the far side staying put |
| Offset F | face | Add a smaller copy of the face inside it |
| Offset E | open edge | Run a new loop inside the open border |
| Squeeze | face, open edge, or a contour | Pinch the face's ring towards its axis. On an open edge it pinches the whole open contour; with a contour selected (click an edge again) or several items, all their points together |
| Divide | face or edge | The menu next to it picks the reach: *Whole loop* or *Only this face*. Face: cut a quad in four; as a loop the cuts run on round the piece (a box face divided cuts the whole box), *Only this face* leaves the neighbours with an extra point. Edge: cut across that edge, as the whole loop through it or only in the faces touching it. Faces that are not quads are cut into one quad per corner |
| Delete F | face | Remove the face, leaving an opening |
| Close | open edge | Fill the open border with a face |
| Shell | none (whole piece) + Inside / Outside / Centred | Give the piece a wall of the chosen thickness: an open piece becomes a thick sheet, a closed one a hollow body. The lip stays crisp. |
| Bridge (Twist) | a face (or an open edge), then another: click one, then click the other: the bridge is made at the second click (Shift+click then Apply, or Apply after each, also work) | Remove the two faces and join their openings with a ring of quads (both need the same number of sides) |

Lengths (Create, Edit cage, Grow F, Grow E) are typed and shown in the
document's unit (mm, cm, m, in, ft); the model itself is metres.

**Smoothing** sets the number of Catmull-Clark steps (0 is the cage itself;
4 is the smoothest). With **Auto** on, the plugin picks the smoothest level
that keeps the surface under about 25 000 triangles. **Cage lines** draws the
cage's own edges as panel lines on the smooth skin; *All edges* draws every
edge of the result; *No lines* hides them.

## Symmetry

Tick **Symmetry** and set the plane: **Centre** puts it through the middle of
the piece perpendicular to the chosen axis (X, Y or Z), **From face** uses
the plane of the selected face. Every edit, drag and tool is then repeated on
the other side: moving a point moves its mirror image, dividing or growing a
face does the same to its twin, creases are copied. Points on the plane stay
on it. The plane is stored with the cage and follows the group when it is
moved. Bridge and Delete F are not mirrored.

## Joining pieces and bridging them

Several SubD groups can be merged into one: choose the other piece under
**Join with** and press **Join**. Then **Delete F** a face on each piece and
**Bridge** the two openings; the result is a single smooth surface. Ctrl+Z
separates the pieces again.

## Moving, rotating and scaling a SubD group

The cage follows the group. When a group is built, four well-spread surface
vertices and the surface centroid are remembered; after the group has been
moved, rotated, scaled uniformly or mirrored, the same vertices tell the plugin
where the surface went and the cage (and the symmetry plane) is carried along.
If the mesh was reloaded in another vertex order the plugin falls back to
following translations only.

## Converting existing geometry

Pick a group made with any other tool under **Convert group**, set the
crease angle, and press **Convert to SubD**. Its faces become the control
cage (keep it coarse: under 7000 faces; a few hundred edit best), its winding is made consistent, its
face colours are kept, and edges that meet at more than the chosen angle are
creased so a box stays boxy. Ctrl+Z brings the original group back. Faces
with holes lose their holes, because a cage cannot have them.

## How it is stored

A SubD group is an ordinary group: its mesh holds the smoothed surface as
triangles (so rendering, picking and export need nothing special) and
`group.ext["subdiv"]` holds the cage, the smoothing level and the line mode.
It is saved in the `.igz` with no format change. Rebuilding replaces the
group in `scene.groups` through an undoable command that keeps its name,
layer, BIM tag, visibility and paint.

## Modules

| File | Role |
|------|------|
| `subdiv/subdivide.py` | Catmull-Clark step, semi-sharp creases, edge/face lineage |
| `subdiv/edit.py` | `Cage`: the editing operations, orientation, serialisation |
| `subdiv/ops.py` | The tools as functions, selection rules, picking, drag maths |
| `subdiv/group.py` | Cage in a group, mesh to cage, undoable swap/join/settings, follow cache |
| `subdiv/follow.py` | Carrying the cage along when the group is moved or transformed |
| `subdiv/icons.py` | The toolbar icons, drawn with QPainter (no image files) |
| `subdiv/panel.py` | The side panel, the cage overlay, the mouse drag |
| `subdiv/__init__.py` | `setup(app)`: loads the panel when IngeTrazo starts |

## Known limits

- The viewport shades each face from its own normal, so a smooth surface
  still shows faint facets; a higher smoothing level reduces them. Smooth
  shading across soft edges belongs in the IngeTrazo core (viewport), not in
  this extension.
- One element is selected at a time.
- Non-uniform scaling of a SubD group is not followed by its cage (edit the cage or rebuild).
- Only top-level groups are converted or listed.

## Finishing a piece

* **Finish** (no longer SubD) keeps the smooth surface as an ordinary group and drops the cage. It first checks the cage: if it is closed and sound (no opening left, no edge shared by three faces, no overlapping points, no empty face), the faces are re-oriented outwards, the result is a group IngeTrazo recognises as a solid (usable with Solid Tools) and the volume is reported. If the cage is still open, you get the plain surface and the status bar says why it is not a solid (Close or Bridge it, then Finish again). One undo step brings the cage back.
* **Finish detail** (above the button) sets how finely curved parts are cut when finishing: *Automatic (light)* (the default: the smoothest level that keeps the result under about 6 000 faces, so ordinary tools such as Push/Pull stay fast), *Same as the view*, Light (1), Medium (2) or Fine (3). Each step multiplies the triangles by four. Flat faces are always single polygons whatever you choose, and neighbouring flat faces in the same plane and the same colour (a box face cut up with Divide, or a Grow F wall flush with the old one) join into one, and the status bar tells you how many faces the result has. A big curved piece finished at the view's full smoothing can run to tens of thousands of faces, which makes the ordinary tools slow.
* Every **flat patch** of a finished piece (the face of a sharp box) becomes one polygon, not hundreds of triangles, so Push/Pull and the other ordinary tools stay fast on it. Curved areas stay triangles.

The move arrows and rotation rings keep a **fixed size on screen** (they do not grow with the piece or the zoom).

**Twist** (Bridge's value box) turns the ring of the bridge by that many points, either way, when the tube comes out crossed. Undo and Apply again with another value.

**Split** undoes a Join: each separate piece of the group becomes its own SubD group again (Ctrl+Z joins them back). A bridged pair is one piece: delete the bridge's faces first (Delete F), then Split.

## Moving several items together

**Shift+click** adds a point, edge or face to the selection (or takes it out again). When a face is already selected and another lies behind it, Shift+click on the same spot reaches the one behind.

**Repeated click.** Click the same spot again (without dragging) to go on to the next thing there. On a face, each click selects the next face behind it, and starts over after the last. On an edge, the next clicks step through its contours: the edge loop (a border edge gives the entire border loop, an inner edge the loop that runs straight through every four-way point; skipped when it is just the edge), then the outline of each of the two faces the edge touches, then back to the edge alone. The status bar says which one is selected. Drag any selected item, or a coloured axis handle, and they all move together; with symmetry on, the mirrored partners follow. **Edit cage** with X, Y or Z moves them all by the value. The other tools work on a single item, so click one item before using them.

**Handles** (list near the bottom of the panel) chooses what the selection shows: *Move + Rotate* (the default) shows both at once: the three coloured tips to slide along an axis and, closer in, three coloured rings (a protractor) to turn around an axis; *Move only* and *Rotate only* keep one of them. Drag a ring to turn the selection around that axis through its centre; a protractor with a tick every 15° and the angle appears while you drag, and **Ctrl** snaps to 15°. With symmetry on, the mirrored points follow. Picking X, Y or Z in the direction list keeps only that axis.

The panel scrolls when it is taller than the window.

**Sharp stays sharp.** *Grow F* and *Offset F* on a face whose edges are sharp give sharp new edges too, so a crisp box pushed out stays rectilinear; on a soft cage nothing is creased and the result stays organic.

**Rounding a sharp piece.** Sharp edges are creases: the *Crease* tool sets how sharp (0 = fully rounded, 1 to 2 = a small radius, 4 or more = crisp). With nothing selected it applies to every edge, so *Crease* at 0 turns a sharp box into a soft block. To round only some edges, select them (Shift+click, or click an edge again to step to its loop or face outline) and Apply: the value goes to all of them. The cage only has the faces you gave it, so for a tighter radius on a bigger piece, *Divide* a face first.
