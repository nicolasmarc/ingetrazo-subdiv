# Changelog

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
