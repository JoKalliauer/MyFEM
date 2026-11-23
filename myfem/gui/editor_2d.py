# AI created the file
# Author: Copilot
# Copyright, License: GPLv3
# Created: 2026-11-23

# Last Changes:
# YYYY-MM-DD HH:mm CET: Author: Changes
# 2026-11-23 23:41 CET: Copilot: Separates support markers from node labels

"""Interactive 2D canvas for entering nodes and members."""

import math
from typing import Literal

from PySide6.QtCore import QPointF, QRectF, Qt, Signal
from PySide6.QtGui import QBrush, QColor, QMouseEvent, QPainter, QPen, QPolygonF
from PySide6.QtWidgets import QGraphicsScene, QGraphicsView

_PIXELS_PER_METER = 30.0
_GRID_STEP = 0.5
_GRID_PIXELS = _PIXELS_PER_METER * _GRID_STEP
_SCENE_RECT = QRectF(-900, -600, 1800, 1200)
_REFERENCE_FIBER_COLOR = "#747c85"
_REFERENCE_FIBER_OFFSET = 7.0


class ModelCanvas2D(QGraphicsView):
    """Display a model in the x-z plane and emit requests for graphical input."""

    node_position_clicked = Signal(float, float)
    node_selected = Signal(str)
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
        self._mode: Literal["select", "node", "member"] = "select"
        self._node_positions: dict[str, QPointF] = {}
        self._member_endpoints: list[tuple[str, str]] = []
        self._supports: list[tuple[str, bool, bool, bool]] = []
        self._pending_node_id: str | None = None
        self.setMinimumSize(360, 300)
        self.set_model(None)
        self.centerOn(0, 0)

    def set_mode(self, mode: Literal["select", "node", "member"]) -> None:
        """Set the active canvas input tool."""
        self._mode = mode
        cursor = (
            Qt.CursorShape.CrossCursor
            if mode in ("node", "member")
            else Qt.CursorShape.ArrowCursor
        )
        self.setCursor(cursor)

    @property
    def mode(self) -> Literal["select", "node", "member"]:
        """Return the active input tool."""
        return self._mode

    def set_pending_node(self, node_id: str | None) -> None:
        """Highlight the first endpoint while a member is being entered."""
        self._pending_node_id = node_id
        self._redraw_model()

    def set_model(self, model: dict[str, object] | None) -> None:
        """Replace the displayed geometry with a compiled model."""
        self._node_positions = {}
        self._member_endpoints = []
        self._supports = []
        self._scene.clear()
        if model is None:
            self._draw_grid()
            return

        node_records = model.get("nodes")
        member_records = model.get("members")
        if not isinstance(node_records, list) or not isinstance(member_records, list):
            raise TypeError("Model nodes and members must be lists")

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

        for record in member_records:
            if not isinstance(record, dict):
                raise TypeError("Each model member must be an object")
            start_id = record.get("node_start")
            end_id = record.get("node_end")
            if (
                not isinstance(start_id, str)
                or not isinstance(end_id, str)
                or start_id not in self._node_positions
                or end_id not in self._node_positions
            ):
                raise TypeError("Each model member must reference existing nodes")
            self._member_endpoints.append((start_id, end_id))

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
        member_pen = QPen(QColor("#26384d"), 3)
        fiber_pen = QPen(QColor(_REFERENCE_FIBER_COLOR), 1)
        support_pen = QPen(QColor("#46525e"), 1.5)
        for start_id, end_id in self._member_endpoints:
            start = self._node_positions[start_id]
            end = self._node_positions[end_id]
            self._scene.addLine(start.x(), start.y(), end.x(), end.y(), member_pen)
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
            self._draw_support(self._node_positions[node_id], dx, dz, ry, support_pen)

        support_states = {
            node_id: (dx, dz, ry) for node_id, dx, dz, ry in self._supports
        }
        node_pen = QPen(QColor("#153f73"), 1.5)
        for identifier, position in self._node_positions.items():
            is_pending = identifier == self._pending_node_id
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

    def mousePressEvent(self, event: QMouseEvent) -> None:
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
        elif self._mode == "member":
            node_id = self._nearest_node(position)
            if node_id is None:
                self.message_requested.emit("Click an existing node to enter a member.")
            else:
                self.node_selected.emit(node_id)
        elif self._mode == "select":
            node_id = self._nearest_node(position)
            if node_id is not None:
                self.node_selected.emit(node_id)
        event.accept()
