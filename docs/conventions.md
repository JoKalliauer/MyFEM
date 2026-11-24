<!-- AI created the file -->
<!-- Author: Copilot -->
<!-- Created: 2026-11-23 -->
<!--
Last Changes:
YYYY-MM-DD HH:mm CET: Author: Changes
2026-11-23 23:35 CET: Copilot: Documented 2D support symbols and reference-fiber markers
2026-11-24 22:02 CET: Copilot: Renamed model orientation terminology to beams
-->

# 2D coordinate and beam-orientation convention

## Global axes

The 2D model lies in the global x-z plane with `y = 0`. Positive x points right
and positive z points down. The canvas uses the same directions.

## Beam reference fiber

The beam's ordered start and end nodes define its direction. In the x-z plane,
the positive reference-fiber direction is the normalized vector
`(-delta_z, delta_x)`, where `delta_x` and `delta_z` are the end coordinates
minus the start coordinates. The canvas indicates this reference fiber with
three short, thin gray dashes parallel to and offset from the beam centerline.

Therefore, a beam directed left-to-right has its reference fiber below it
(positive z). A beam directed bottom-to-top has its reference fiber to the
right (positive x). Reversing the beam's start and end nodes reverses the
reference-fiber direction.

This direction agrees with the solver's default local z-axis in the x-z plane
when the beam rotation is zero.

## 2D supports

The canvas displays the in-plane restraint degrees of freedom: `DX`, `DZ`, and
`RY`. It uses a triangle for a pin (`DX` and `DZ` restrained, `RY` free), a
hatched block for a fixed support, and roller symbols for a single restrained
translation. Other in-plane combinations are marked directly at the node.
Out-of-plane restraints (`DY`, `RX`, and `RZ`) are not shown in the 2D view.
