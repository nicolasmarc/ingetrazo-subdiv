# Changelog

## 1.4 (trial)

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
