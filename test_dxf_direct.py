import sys
import os
from qgis.core import (
    QgsApplication, QgsVectorLayer, QgsRectangle, QgsCoordinateReferenceSystem,
    QgsFeature, QgsGeometry, QgsPointXY, QgsDxfExport, QgsProject
)
from qgis.PyQt.QtCore import QTimer, QFile

def test():
    with open("/Volumes/Mac_Dados/Repos/MJ-PROJETOQGIS/test_dxf.log", "w") as log:
        try:
            log.write("1. Criando camada de teste...\n")
            vl = QgsVectorLayer("LineString?crs=epsg:31982", "Rede_Teste", "memory")
            pr = vl.dataProvider()
            f = QgsFeature()
            f.setGeometry(QgsGeometry.fromPolylineXY([QgsPointXY(10, 10), QgsPointXY(100, 100)]))
            pr.addFeatures([f])
            vl.updateExtents()

            log.write("2. Testando QgsDxfExport direto da API C++...\n")
            dxf = QgsDxfExport()
            dxf.setExtent(QgsRectangle(0, 0, 200, 200))
            dxf.setSymbologyScale(800)
            dxf.setSymbologyMode(QgsDxfExport.SymbologyMode.SymbolLayerSymbology if hasattr(QgsDxfExport, 'SymbologyMode') else 2)
            dxf.setCrs(QgsCoordinateReferenceSystem("EPSG:31982"))

            dlayer = QgsDxfExport.DxfLayer(vl, -1)
            dxf.addLayers([dlayer])

            out_file = "/tmp/qgs_direct.dxf"
            qf = QFile(out_file)
            if qf.open(QFile.OpenModeFlag.WriteOnly if hasattr(QFile, 'OpenModeFlag') else QFile.WriteOnly):
                res = dxf.writeToFile(qf, "cp1252")
                qf.close()
                log.write(f"3. QgsDxfExport.writeToFile resultado: {res} (0 é sucesso QgsDxfExport.ExportResult.Success)\n")
                log.write(f"4. Arquivo gerado tamanho: {os.path.getsize(out_file)} bytes\n")
            else:
                log.write("Falha ao abrir arquivo para escrita.\n")
        except Exception as e:
            import traceback
            log.write(f"ERRO: {traceback.format_exc()}\n")

    QgsApplication.instance().quit()

QTimer.singleShot(500, test)
