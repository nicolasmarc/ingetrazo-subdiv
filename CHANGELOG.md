# Changelog

## 1.4 (trial)

- The symmetry plane is drawn whether the cage is shown or not.
- Hover detection: the last mouse move is always handled (a fast exit to empty space no longer leaves the highlight on the surface), and the point zone is back to a smaller size so it no longer reaches for far-away points.
- Slice shows its cutting plane as a see-through sheet (it follows the offset and the X/Y/Z choice, also while you adjust); the tool starts on Z.
- The move and rotate handles always show the three axes: the direction list (X/Y/Z) no longer reduces them to one ring and one arrow.
- Sweep from a face of the piece: the tube now grows out of that face and is welded to it (the face goes), so the piece is no longer cut in two.
- Faster: "Automatic" smoothing aims at 8 000 triangles (it was 25 000), the hover highlight no longer builds every skin point, and the pick works on the arrays directly.
- Points are easier to grab on the skin: bigger zone, and the points of the face or edge under the cursor are shown as small dots.
- The value box can be dragged by any of its text and is moved by the system (smoother).
- Delete (Supr) on a picked SubD face, edge or point removes just that part (one undo step); before, it could erase the whole piece. Loft / Sweep / Revolve show the plain drawing they will use ("Drawing: n face(s), n line(s)").
- Triple click on a SubD piece selects the whole piece (move it, Ctrl+drag to copy it, Delete to remove it). The second click of a double-click no longer enters the host's group editing, which hid the SubD handles.
- Compact panel: icon-only tool buttons (name and description shown above the value), "Join, split, convert" and "Smoothing, finish, handles" are collapsible and closed at first.
- "Pick on the skin" is now on by default and sits under the status line; with the cage shown, a cage point or edge you aim at still wins, otherwise the skin is picked. Edge picking on the skin also considers the neighbouring faces and is more tolerant.
- The SubD panel tab now has an icon.
- Right-click on a point, edge or face (on the cage or on the skin) opens a SubD menu with the tools that suit it, run with the panel's value.
- Revolve, Loft and Sweep accept plain faces and lines from the drawing (select them in the model, then Apply); no SubD group is needed first.
- Tools that take a value or a choice (Bevel, Offset, Shell side, Divide cut, Loft ends, direction…) ask for it in a small box at the cursor when run from the right-click menu; the last value typed per tool is remembered. Symmetry and Soft are toggles in that menu.
- Ctrl+C / Ctrl+V (and menu entries) copy selected SubD faces and paste them as a new SubD piece.
- Right-click on the SubD piece opens a menu of SubD tools only (switchable in "Smoothing, finish, handles"), with Smoothing 0 to 4 / Auto.
- Live adjustment: a tool chosen from the right-click menu (Edit cage, Crease, Grow, Stretch, Offset, Squeeze, Shell, Bevel, Slice, Slide, Merge) follows the mouse with a live wireframe preview and the value shown at the cursor; click applies, Enter types an exact value, Esc cancels, Shift = finer, Ctrl = snap, X/Y/Z set the direction.
- Ctrl + drag a move handle copies the selected faces (in place), or the whole piece as a new SubD group when every face is selected (right-click: Select all faces).
- The value box shows a live wireframe preview while you type, with an Apply button; the mouse-following mode is now optional and a right-click validates it.
- Picking on the skin is steadier: the item under the cursor lights up in blue before you click, and the point / edge / face zones scale with the size of the face on screen.
- Loft grows out of the cage faces: welded to their points, an attached face (or a middle one) is removed so the new surface joins the piece, a free face at an end stays as the cap (or goes with open ends).
- The value window can be dragged anywhere with the mouse, stays open while you turn the view, and reopens where you left it.
- Move / rotate handles are drawn (and usable) with the cage hidden.

- **Eight new tools**: Revolve, Bevel, Loft, Sweep, Slice, Merge, Dissolve and Slide
  (22 tools in all), each with its icon and English, French and Spanish texts.
  Lengths follow the document's unit.
- **Faster smoothing**: the Catmull-Clark step now runs on NumPy. Tests prove the
  result equal to the previous plain-Python version (kept as the reference) on boxes,
  open pieces, triangles, n-gons, non-manifold edges and random creases.
- **Soft selection**: tick *Soft* and set a radius; a drag or Edit cage also moves
  the points around, fading out smoothly. Works with symmetry.
- **Pick on the skin**: tick *Pick on the skin* and click the smooth surface itself;
  the cage point, edge or face behind the spot is selected (a point near a cage point,
  an edge near its curve on the skin, otherwise the face), even with the cage hidden,
  where the selection is drawn on the skin. Click again to reach the face behind.
- **Click again for the Ring** of an edge (after Edge and Loop).
- **Fractional creases** (1.5, 0.5...) and **corner creases** (Crease on a selected
  point), following DeRose, Kass and Truong (1998). Corner creases are saved with
  the cage; older documents load unchanged.

## 1.3

- **Spanish**: the panel now also speaks Spanish when IngeTrazo is in Spanish
  (`es`, `es-MX`...). English, French and Spanish are all covered; other languages
  stay in English (`SUBD_LANG=es|fr|en` forces one). A test checks that every text
  exists in French and Spanish with the same placeholders.
- The Bridge message now translates the words "face" / "opening".

## 1.2

- **The panel follows IngeTrazo's language**: French when IngeTrazo is in
  French, English otherwise (`SUBD_LANG=fr|en` forces one). Tools, help texts,
  messages and the checks before Finish.
- The volume after Finish is given in the document's unit (cubic metres in
  brackets).
- Tests for both.

## 1.1

- The help line and tooltips of the Create tool now follow the document's unit
  (mm, cm, m, in...) instead of always saying "metres", matching the value box.
  Reported on the IngeTrazo 0.5.8 unit settings.

## 1.0

First release as a standalone extension.

- Fourteen cage tools with their own icons: Create, Edit cage, Crease, Grow F,
  Grow E, Stretch, Offset F, Offset E, Squeeze, Divide, Delete F, Close,
  Bridge, Shell. Drag points, edges and faces with the mouse (axis constraint,
  Esc cancels).
- **Divide** is a loop cut (whole loop or only the chosen face); **Bridge** by
  two clicks; **Grow E** on a whole open contour (axis X/Y/Z or Auto);
  **Squeeze** and **Crease** on open edges and contours.
- Symmetry about a plane; Join two SubD pieces; conversion of ordinary groups
  with automatic creases above a chosen angle.
- **Finish**: one button. A closed, sound cage gives a Solid Group and its
  volume; an open one gives the plain surface and says why. Flat patches
  become single polygons; the default detail level keeps the result under
  about 6000 faces so the native tools stay fast.
- Fixed-size gizmos, compact panel, values in the document's unit.
- The cage follows the group when it is moved, rotated or scaled.
