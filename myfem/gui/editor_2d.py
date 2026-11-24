# AI created the file
# Author: Copilot
# Copyright, License: GPLv3
# Created: 2026-11-23

# Last Changes:
# YYYY-MM-DD HH:mm CET: Author: Changes
# 2026-11-23 23:41 CET: Copilot: Separates support markers from node labels
# 2026-11-24 22:02 CET: Copilot: Renamed model geometry and tool mode to beams
# 2026-11-24 22:30 CET: Copilot: Emits node edit requests on double-click
# 2026-11-24 22:50 CET: Copilot: Adds beam and support selection and edit requests
# 2026-11-24 23:15 CET: Copilot: Emits node context-menu requests on right-click
# 2026-11-24 23:22 CET: Copilot: Allows node context menus in every tool mode
# 2026-11-24 23:24 CET: Copilot: Adds mouse-wheel zoom to the 2D canvas

"""Interactive 2D canvas for entering nodes and beams."""

import math
from typing import Literal

from PySide6.QtCore import QPoint, QPointF, QRectF, Qt, Signal
from PySide6.QtGui import (
    QBrush,
    QColor,
    QMouseEvent,
    QPainter,
    QPen,
    QPolygonF,
    QWheelEvent,
)
from PySide6.QtWidgets import QGraphicsScene, QGraphicsView

_PIXELS_PER_METER = 30.0
_GRID_STEP = 0.5
_GRID_PIXELS = _PIXELS_PER_METER * _GRID_STEP
_SCENE_RECT = QRectF(-900, -600, 1800, 1200)
_REFERENCE_FIBER_COLOR = "#747c85"
_REFERENCE_FIBER_OFFSET = 7.0
_ZOOM_FACTOR = 1.15
_MIN_ZOOM = 0.2
_MAX_ZOOM = 8.0


class ModelCanvas2D(QGraphicsView):
    """Display a model in the x-z plane and emit requests for graphical input."""

    node_position_clicked = Signal(float, float)
    node_selected = Signal(str)
    object_selected = Signal(str, str)
    object_double_clicked = Signal(str, str)
    node_context_requested = Signal(str, QPoint)
    message_requested = Signal(str)

    def __init__(self) -> None:
        super().__init__()
        self.setObjectName("model_canvas_2d")
        self._scene = QGraphicsScene(self)
        self.setScene(self._scene)
        self.setSceneRect(_SCENE_RECT)
        self.setRenderHint(QPainter.RenderHint.Antialiasing)
        self.setBackgroundBrush(QColor("#fbfcfe"))
        self.setDragMode(QGraphicsView.DragMode.NoDrag)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.setTransformationAnchor(QGraphicsView.ViewportAnchor.AnchorUnderMouse)
        self._mode: Literal["select", "node", "beam"] = "select"
        self._node_positions: dict[str, QPointF] = {}
        self._beam_endpoints: list[tuple[str, str, str]] = []
        self._supports: list[tuple[str, bool, bool, bool]] = []
        self._selected_object: tuple[str, str] | None = None
        self._pending_node_id: str | None = None
        self.setMinimumSize(360, 300)
        self.set_model(None)
        self.centerOn(0, 0)

    def wheelEvent(self, event: QWheelEvent) -> None:
        delta = event.angleDelta().y() or event.pixelDelta().y()
        if delta == 0:
            super().wheelEvent(event)
            return

        steps = max(-20.0, min(20.0, delta / 120.0))
        current_scale = self.transform().m11()
        target_scale = min(
            _MAX_ZOOM,
            max(_MIN_ZOOM, current_scale * (_ZOOM_FACTOR**steps)),
        )
        scale_factor = target_scale / current_scale
        if scale_factor != 1.0:
            self.scale(scale_factor, scale_factor)
        event.accept()

    def set_mode(self, mode: Literal["select", "node", "beam"]) -> None:
        """Set the active canvas input tool."""
        self._mode = mode
        cursor = (
            Qt.CursorShape.CrossCursor
            if mode in ("node", "beam")
            else Qt.CursorShape.ArrowCursor
        )
        self.setCursor(cursor)

    @property
    def mode(self) -> Literal["select", "node", "beam"]:
        """Return the active input tool."""
        return self._mode

    def set_pending_node(self, node_id: str | None) -> None:
        """Highlight the first endpoint while a beam is being entered."""
        self._pending_node_id = node_id
        self._redraw_model()

    def set_model(self, model: dict[str, object] | None) -> None:
        """Replace the displayed geometry with a compiled model."""
        self._node_positions = {}
        self._beam_endpoints = []
        self._supports = []
        self._scene.clear()
        if model is None:
            self._selected_object = None
            self._draw_grid()
            return

        node_records = model.get("nodes")
        beam_records = model.get("beams")
        if not isinstance(node_records, list) or not isinstance(beam_records, list):
            raise TypeError("Model nodes and beams must be lists")

        for record in node_records:
            if not isinstance(record, dict):
                raise TypeError("Each model node must be an object")
            identifier = record.get("id")
            x = record.get("x")
            z = record.get("z")
            if (
                not isinstance(identifier, str)
                or isinstance(x, bool)
                or not isinstance(x, (int, float))
                or isinstance(z, bool)
                or not isinstance(z, (int, float))
            ):
                raise TypeError("Each model node must have an id, x, and z")
            self._node_positions[identifier] = QPointF(
                float(x) * _PIXELS_PER_METER,
                float(z) * _PIXELS_PER_METER,
            )

        for record in beam_records:
            if not isinstance(record, dict):
                raise TypeError("Each model beam must be an object")
            identifier = record.get("id")
            start_id = record.get("node_start")
            end_id = record.get("node_end")
            if (
                not isinstance(identifier, str)
                or not isinstance(start_id, str)
                or not isinstance(end_id, str)
                or start_id not in self._node_positions
                or end_id not in self._node_positions
            ):
                raise TypeError(
                    "Each model beam must have an id and reference existing nodes"
                )
            self._beam_endpoints.append((identifier, start_id, end_id))

        support_records = model.get("supports")
        if not isinstance(support_records, list):
            raise TypeError("Model supports must be a list")
        for record in support_records:
            if not isinstance(record, dict):
                raise TypeError("Each model support must be an object")
            node_id = record.get("node")
            dx = record.get("DX")
            dz = record.get("DZ")
            ry = record.get("RY")
            if (
                not isinstance(node_id, str)
                or node_id not in self._node_positions
                or not isinstance(dx, bool)
                or not isinstance(dz, bool)
                or not isinstance(ry, bool)
            ):
                raise TypeError("Each 2D support must define node, DX, DZ, and RY")
            self._supports.append((node_id, dx, dz, ry))
        if self._selected_object is not None:
            kind, identifier = self._selected_object
            available_ids = {
                "node": set(self._node_positions),
                "beam": {beam_id for beam_id, _, _ in self._beam_endpoints},
                "support": {node_id for node_id, _, _, _ in self._supports},
            }
            if identifier not in available_ids.get(kind, set()):
                self._selected_object = None
        self._redraw_model()

    def _draw_grid(self) -> None:
        minor_pen = QPen(QColor("#e5eaf0"), 0.8)
        major_pen = QPen(QColor("#d0d9e3"), 1)
        for x in range(-900, 901, round(_GRID_PIXELS)):
            pen = major_pen if x % round(_PIXELS_PER_METER) == 0 else minor_pen
            self._scene.addLine(x, -600, x, 600, pen)
        for z in range(-600, 601, round(_GRID_PIXELS)):
            pen = major_pen if z % round(_PIXELS_PER_METER) == 0 else minor_pen
            self._scene.addLine(-900, z, 900, z, pen)

        axis_pen = QPen(QColor("#b4c0cc"), 1)
        self._scene.addLine(-900, 0, 900, 0, axis_pen)
        self._scene.addLine(0, -600, 0, 600, axis_pen)
        x_label = self._scene.addSimpleText("x (m) →")
        x_label.setPos(820, 8)
        z_label = self._scene.addSimpleText("z (m) ↓")
        z_label.setPos(8, 550)

    def _redraw_model(self) -> None:
        self._scene.clear()
        self._draw_grid()
        beam_pen = QPen(QColor("#26384d"), 3)
        fiber_pen = QPen(QColor(_REFERENCE_FIBER_COLOR), 1)
        support_pen = QPen(QColor("#46525e"), 1.5)
        selected_pen = QPen(QColor("#e67700"), 4)
        for beam_id, start_id, end_id in self._beam_endpoints:
            start = self._node_positions[start_id]
            end = self._node_positions[end_id]
            pen = (
                selected_pen if self._selected_object == ("beam", beam_id) else beam_pen
            )
            self._scene.addLine(start.x(), start.y(), end.x(), end.y(), pen)
            dx = end.x() - start.x()
            dz = end.y() - start.y()
            length = math.hypot(dx, dz)
            offset_x = -dz / length * _REFERENCE_FIBER_OFFSET
            offset_z = dx / length * _REFERENCE_FIBER_OFFSET
            unit_x = dx / length
            unit_z = dz / length
            dash_length = min(12.0, length * 0.1)
            dash_gap = dash_length * 0.4
            dash_spacing = dash_length + dash_gap
            for dash_index in (-1, 0, 1):
                dash_center = length / 2 + dash_index * dash_spacing
                dash_start = dash_center - dash_length / 2
                dash_end = dash_center + dash_length / 2
                self._scene.addLine(
                    start.x() + unit_x * dash_start + offset_x,
                    start.y() + unit_z * dash_start + offset_z,
                    start.x() + unit_x * dash_end + offset_x,
                    start.y() + unit_z * dash_end + offset_z,
                    fiber_pen,
                )

        for node_id, dx, dz, ry in self._supports:
            pen = (
                QPen(QColor("#e67700"), 2.5)
                if self._selected_object == ("support", node_id)
                else support_pen
            )
            self._draw_support(self._node_positions[node_id], dx, dz, ry, pen)

        support_states = {
            node_id: (dx, dz, ry) for node_id, dx, dz, ry in self._supports
        }
        node_pen = QPen(QColor("#153f73"), 1.5)
        for identifier, position in self._node_positions.items():
            is_pending = identifier == self._pending_node_id or (
                self._selected_object == ("node", identifier)
            )
            self._scene.addEllipse(
                QRectF(position.x() - 5, position.y() - 5, 10, 10),
                node_pen,
                QColor("#f2a541" if is_pending else "#1976d2"),
            )
            label = self._scene.addSimpleText(identifier)
            label.setBrush(QColor("#24364b"))
            support = support_states.get(identifier)
            if support is None:
                label.setPos(position.x() + 8, position.y() - 18)
            else:
                dx, dz, ry = support
                if (dx and not dz) or (ry and not (dx and dz)):
                    label.setPos(
                        position.x() - 8 - label.boundingRect().width(),
                        position.y() - 22,
                    )
                else:
                    label.setPos(position.x() + 8, position.y() - 22)

    def _draw_support(
        self, position: QPointF, dx: bool, dz: bool, ry: bool, pen: QPen
    ) -> None:
        x = position.x()
        z = position.y()
        brush = QBrush(QColor("#fbfcfe"))
        if dx and dz and ry:
            top = z + 5
            base = z + 13
            self._scene.addRect(
                QRectF(x - 9, top, 18, base - top), pen, QBrush(QColor("#dce2e8"))
            )
            self._scene.addLine(x - 10, base, x + 10, base, pen)
            for offset in (-8, -2, 4):
                self._scene.addLine(x + offset, base, x + offset - 4, base + 5, pen)
        elif dx and dz:
            self._scene.addPolygon(
                QPolygonF(
                    (
                        QPointF(x, z + 5),
                        QPointF(x - 10, z + 19),
                        QPointF(x + 10, z + 19),
                    )
                ),
                pen,
                brush,
            )
            self._scene.addLine(x - 11, z + 20, x + 11, z + 20, pen)
            for offset in (-8, -2, 4):
                self._scene.addLine(x + offset, z + 20, x + offset - 4, z + 25, pen)
        elif dz:
            self._scene.addLine(x, z + 5, x, z + 8, pen)
            self._scene.addEllipse(QRectF(x - 6, z + 8, 4, 4), pen, brush)
            self._scene.addEllipse(QRectF(x + 2, z + 8, 4, 4), pen, brush)
            self._scene.addLine(x - 10, z + 14, x + 10, z + 14, pen)
            for offset in (-8, -2, 4):
                self._scene.addLine(x + offset, z + 14, x + offset - 4, z + 19, pen)
        elif dx:
            self._scene.addLine(x + 5, z, x + 8, z, pen)
            self._scene.addEllipse(QRectF(x + 8, z - 5, 4, 4), pen, brush)
            self._scene.addEllipse(QRectF(x + 8, z + 1, 4, 4), pen, brush)
            self._scene.addLine(x + 14, z - 10, x + 14, z + 10, pen)
            for offset in (-7, -1, 5):
                self._scene.addLine(x + 14, z + offset, x + 19, z + offset - 4, pen)
        elif ry:
            self._scene.addEllipse(QRectF(x - 8, z - 8, 16, 16), pen)
        else:
            self._scene.addPolygon(
                QPolygonF(
                    (
                        QPointF(x, z - 6),
                        QPointF(x + 6, z),
                        QPointF(x, z + 6),
                        QPointF(x - 6, z),
                    )
                ),
                pen,
                brush,
            )

        if ry and (dx != dz):
            label = self._scene.addSimpleText("RY")
            label.setBrush(pen.color())
            label.setPos(x + 22, z - 18)

    def _nearest_node(self, position: QPointF) -> str | None:
        nearest_id: str | None = None
        nearest_distance = 15.0
        for identifier, node_position in self._node_positions.items():
            distance = (position - node_position).manhattanLength()
            if distance < nearest_distance:
                nearest_id = identifier
                nearest_distance = distance
        return nearest_id

    def _nearest_support(self, position: QPointF) -> str | None:
        for node_id, dx, dz, ry in self._supports:
            node_position = self._node_positions[node_id]
            offset_x = position.x() - node_position.x()
            offset_z = position.y() - node_position.y()
            if dx and dz:
                hit = abs(offset_x) <= 15 and 3 <= offset_z <= 27
            elif dz:
                hit = abs(offset_x) <= 15 and 4 <= offset_z <= 21
            elif dx:
                hit = 4 <= offset_x <= 21 and abs(offset_z) <= 15
            elif ry:
                radius = math.hypot(offset_x, offset_z)
                hit = 8 <= radius <= 12
            else:
                hit = abs(offset_x) + abs(offset_z) <= 8
            if hit:
                return node_id
        return None

    def _nearest_beam(self, position: QPointF) -> str | None:
        nearest_id: str | None = None
        nearest_distance = 8.0
        for beam_id, start_id, end_id in self._beam_endpoints:
            start = self._node_positions[start_id]
            end = self._node_positions[end_id]
            direction = end - start
            length_squared = direction.x() ** 2 + direction.y() ** 2
            projection = (
                (position - start).x() * direction.x()
                + (position - start).y() * direction.y()
            ) / length_squared
            projection = min(1.0, max(0.0, projection))
            closest = start + direction * projection
            distance = math.hypot(
                position.x() - closest.x(), position.y() - closest.y()
            )
            if distance < nearest_distance:
                nearest_id = beam_id
                nearest_distance = distance
        return nearest_id

    def _object_at(self, position: QPointF) -> tuple[str, str] | None:
        support_id = self._nearest_support(position)
        if support_id is not None:
            return "support", support_id
        node_id = self._nearest_node(position)
        if node_id is not None:
            return "node", node_id
        beam_id = self._nearest_beam(position)
        if beam_id is not None:
            return "beam", beam_id
        return None

    def _select_object(self, selected: tuple[str, str] | None) -> None:
        self._selected_object = selected
        self._redraw_model()
        self.object_selected.emit(*(selected or ("", "")))

    def mousePressEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.MouseButton.RightButton:
            position = self.mapToScene(event.position().toPoint())
            node_id = self._nearest_node(position)
            if node_id is not None:
                self._select_object(("node", node_id))
                global_position = self.viewport().mapToGlobal(
                    event.position().toPoint()
                )
                self.node_context_requested.emit(node_id, global_position)
                event.accept()
                return
        if event.button() != Qt.MouseButton.LeftButton:
            super().mousePressEvent(event)
            return

        position = self.mapToScene(event.position().toPoint())
        if self._mode == "node":
            x = round(position.x() / _GRID_PIXELS) * _GRID_STEP
            z = round(position.y() / _GRID_PIXELS) * _GRID_STEP
            snapped_position = QPointF(x * _PIXELS_PER_METER, z * _PIXELS_PER_METER)
            if self._nearest_node(snapped_position) is not None:
                self.message_requested.emit("A node already exists at this position.")
            else:
                self.node_position_clicked.emit(x, z)
        elif self._mode == "beam":
            node_id = self._nearest_node(position)
            if node_id is None:
                self.message_requested.emit("Click an existing node to enter a beam.")
            else:
                self.node_selected.emit(node_id)
        elif self._mode == "select":
            self._select_object(self._object_at(position))
        event.accept()

    def mouseDoubleClickEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.MouseButton.LeftButton and self._mode == "select":
            selected = self._object_at(self.mapToScene(event.position().toPoint()))
            if selected is not None:
                self._select_object(selected)
                self.object_double_clicked.emit(*selected)
                event.accept()
                return
        super().mouseDoubleClickEvent(event)
