# Changelog

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
