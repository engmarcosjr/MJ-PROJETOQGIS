import sys
import os
import tempfile
from qgis.core import (
    QgsApplication, QgsVectorLayer, QgsRectangle, QgsCoordinateReferenceSystem,
    QgsFeature, QgsGeometry, QgsPointXY, QgsField
)
from qgis.PyQt.QtCore import QVariant, QTimer
import processing

def test():
    print("Iniciando teste native:dxfexport...")
    vl = QgsVectorLayer("LineString?crs=epsg:31982", "Rede_DN100", "memory")
    pr = vl.dataProvider()
    pr.addAttributes([QgsField("cat_dnom", QVariant.String)])
    vl.updateFields()

    f = QgsFeature()
    f.setGeometry(QgsGeometry.fromPolylineXY([QgsPointXY(10, 10), QgsPointXY(100, 100)]))
    f.setAttributes(["100"])
    pr.addFeatures([f])
    vl.updateExtents()

    out_dxf = "/tmp/test_out.dxf"
    if os.path.exists(out_dxf):
        os.remove(out_dxf)

    params = {
        'LAYERS': [vl],
        'SYMBOLOGY_MODE': 0,
        'SYMBOLOGY_SCALE': 800,
        'ENCODING': 'cp1252',
        'CRS': QgsCoordinateReferenceSystem("EPSG:31982"),
        'OUTPUT': out_dxf
    }
    res = processing.run("native:dxfexport", params)
    print("Resultado dxfexport:", res)
    print("Arquivo gerado existe?", os.path.exists(out_dxf), "Tamanho:", os.path.getsize(out_dxf) if os.path.exists(out_dxf) else 0)
    QgsApplication.instance().quit()

QTimer.singleShot(500, test)
