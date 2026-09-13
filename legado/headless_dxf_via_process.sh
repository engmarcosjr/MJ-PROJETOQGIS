#!/bin/bash
PROJECT="/Volumes/Mac_Dados/Downloads/QGIS_AGUA_OFF - Copia/agua_aps_off_05-04-26.qgs"
QGIS_CMD="/Applications/QGIS-final-4_2_0.app/Contents/MacOS/qgis_process"

# Layers string definition (dxf export needs an arcane string for dxflayers)
# Format is layeredName|layerSplitField|layerId... 
# Actually qgis_process using native dxf doesnt have deep parameter manipulation unless we pass json.
