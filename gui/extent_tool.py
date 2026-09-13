# -*- coding: utf-8 -*-
"""Ferramenta interativa de mapa para desenhar retângulo de recorte no canvas do QGIS."""

from qgis.PyQt.QtCore import pyqtSignal, Qt
from qgis.PyQt.QtGui import QColor, QCursor
from qgis.core import QgsRectangle, QgsPointXY, QgsWkbTypes
from qgis.gui import QgsMapTool, QgsRubberBand


# Obter identificadores de botão e tecla compatíveis com Qt5 e Qt6
LEFT_BUTTON = getattr(getattr(Qt, 'MouseButton', None), 'LeftButton', getattr(Qt, 'LeftButton', None))
KEY_ESCAPE = getattr(getattr(Qt, 'Key', None), 'Key_Escape', getattr(Qt, 'Key_Escape', None))


class MapToolDrawExtent(QgsMapTool):
    """Permite ao usuário clicar e arrastar no mapa para definir a Bounding Box de recorte."""

    extentDrawn = pyqtSignal(QgsRectangle)

    def __init__(self, canvas):
        super().__init__(canvas)
        self.canvas = canvas
        self.rubber_band = None
        self.start_point = None
        self.end_point = None
        self.is_drawing = False
        try:
            # Compatibilidade Qt5 / Qt6
            cursor_shape = getattr(getattr(Qt, 'CursorShape', None), 'CrossCursor', getattr(Qt, 'CrossCursor', None))
            if cursor_shape is not None:
                self.setCursor(QCursor(cursor_shape))
        except Exception:
            pass

    def canvasPressEvent(self, event):
        if event.button() == LEFT_BUTTON:
            self.start_point = self.toMapCoordinates(event.pos())
            self.end_point = self.start_point
            self.is_drawing = True

            if not self.rubber_band:
                self.rubber_band = QgsRubberBand(self.canvas, QgsWkbTypes.PolygonGeometry)
                self.rubber_band.setColor(QColor(0, 120, 215, 60))
                self.rubber_band.setStrokeColor(QColor(0, 120, 215, 220))
                self.rubber_band.setWidth(2)

            self.rubber_band.reset(QgsWkbTypes.PolygonGeometry)
            self._update_rubber_band()

    def canvasMoveEvent(self, event):
        if self.is_drawing and self.start_point:
            self.end_point = self.toMapCoordinates(event.pos())
            self._update_rubber_band()

    def canvasReleaseEvent(self, event):
        if event.button() == LEFT_BUTTON and self.is_drawing:
            self.end_point = self.toMapCoordinates(event.pos())
            self.is_drawing = False

            rect = QgsRectangle(
                min(self.start_point.x(), self.end_point.x()),
                min(self.start_point.y(), self.end_point.y()),
                max(self.start_point.x(), self.end_point.x()),
                max(self.start_point.y(), self.end_point.y())
            )

            if rect.width() > 0 and rect.height() > 0:
                self.extentDrawn.emit(rect)

            self.reset()

    def keyPressEvent(self, event):
        if event.key() == KEY_ESCAPE:
            self.reset()

    def _update_rubber_band(self):
        if not self.rubber_band or not self.start_point or not self.end_point:
            return

        p1 = self.start_point
        p2 = self.end_point

        rect_geom = [
            QgsPointXY(p1.x(), p1.y()),
            QgsPointXY(p2.x(), p1.y()),
            QgsPointXY(p2.x(), p2.y()),
            QgsPointXY(p1.x(), p2.y()),
            QgsPointXY(p1.x(), p1.y()),
        ]

        self.rubber_band.reset(QgsWkbTypes.PolygonGeometry)
        for pt in rect_geom:
            self.rubber_band.addPoint(pt, False)
        self.rubber_band.show()

    def reset(self):
        self.is_drawing = False
        self.start_point = None
        self.end_point = None
        if self.rubber_band:
            self.rubber_band.reset(QgsWkbTypes.PolygonGeometry)
            self.rubber_band.hide()

    def deactivate(self):
        self.reset()
        super().deactivate()
