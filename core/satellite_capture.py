# -*- coding: utf-8 -*-
"""Captura e georreferenciamento de imagem ortorretificada (Google Satellite / Ortofoto) no QGIS."""

import os
from qgis.core import (
    QgsProject,
    QgsRectangle,
    QgsCoordinateReferenceSystem,
    QgsRasterLayer,
    QgsMapLayer,
    QgsMapSettings,
    QgsMapRendererSequentialJob,
)
from qgis.PyQt.QtCore import QSize
from qgis.PyQt.QtGui import QColor


GOOGLE_SATELLITE_URL = "type=xyz&url=https://mt1.google.com/vt/lyrs=s&x={x}&y={y}&z={z}"
GOOGLE_HYBRID_URL = "type=xyz&url=https://mt1.google.com/vt/lyrs=y&x={x}&y={y}&z={z}"


def get_active_visible_raster_layers():
    """Retorna as camadas raster atualmente visíveis no projeto QGIS (ortofotos, satélite)."""
    project = QgsProject.instance()
    root = project.layerTreeRoot()
    raster_layers = []

    for tree_layer in root.findLayers():
        if tree_layer.isVisible():
            layer = tree_layer.layer()
            if layer and layer.isValid() and layer.type() == QgsMapLayer.RasterLayer:
                raster_layers.append(layer)

    return raster_layers


def capture_satellite_image(
    extent: QgsRectangle,
    crs: QgsCoordinateReferenceSystem,
    output_image_path: str,
    target_width_px: int = 2560,
    use_project_raster: bool = True
) -> dict:
    """Renderiza ortofoto ou satélite Google Maps perfeitamente recortada para a extensão BBox.

    Gera:
      1. Arquivo de imagem (.jpg)
      2. World File georreferenciado (.jgw)

    Retorna dicionário com metadados para inserção no DXF:
      {
        'image_path': str,
        'image_name': str,
        'size_in_pixel': (w_px, h_px),
        'size_in_units': (w_m, h_m),
        'insert_point': (xmin, ymin, 0.0)
      }
    """
    if extent is None or extent.isEmpty():
        raise ValueError("A extensão para captura de imagem de satélite está vazia.")

    # Calcular proporção de pixels mantendo o aspect ratio do terreno
    w_m = extent.width()
    h_m = extent.height()
    aspect_ratio = h_m / w_m
    width_px = int(target_width_px)
    height_px = max(100, int(width_px * aspect_ratio))

    # Selecionar camadas para renderizar: se tiver raster visível no projeto, usa; senão usa Google Satellite
    active_rasters = get_active_visible_raster_layers() if use_project_raster else []
    temp_google_layer = None

    if not active_rasters:
        temp_google_layer = QgsRasterLayer(GOOGLE_SATELLITE_URL, "Google_Satellite_Temp", "wms")
        if not temp_google_layer.isValid():
            raise RuntimeError("Não foi possível conectar ao serviço de imagens do Google Satélite.")
        render_layers = [temp_google_layer]
    else:
        render_layers = active_rasters

    # Configurar parâmetros de renderização
    map_settings = QgsMapSettings()
    map_settings.setExtent(extent)
    map_settings.setDestinationCrs(crs)
    map_settings.setOutputSize(QSize(width_px, height_px))
    map_settings.setLayers(render_layers)
    map_settings.setBackgroundColor(QColor(255, 255, 255))

    from qgis.PyQt.QtCore import QCoreApplication, QTime
    job = QgsMapRendererSequentialJob(map_settings)
    job.start()

    # Processar eventos enquanto o download dos tiles do Google ocorre
    t_start = QTime.currentTime()
    while job.isActive():
        QCoreApplication.processEvents()
        if t_start.msecsTo(QTime.currentTime()) > 25000:  # 25s timeout
            job.cancel()
            break

    rendered_img = job.renderedImage()
    if rendered_img.isNull():
        raise RuntimeError("Falha na renderização da imagem de satélite.")

    # Salvar arquivo JPG
    os.makedirs(os.path.dirname(os.path.abspath(output_image_path)), exist_ok=True)
    if not output_image_path.lower().endswith(('.jpg', '.jpeg')):
        output_image_path += ".jpg"

    saved = rendered_img.save(output_image_path, "JPG", 92)
    if not saved or not os.path.exists(output_image_path):
        raise RuntimeError(f"Falha ao gravar arquivo de imagem: {output_image_path}")

    # Gerar World File (.jgw) para georreferenciamento cartográfico universal
    # Formato World File:
    # Linha 1: Tamanho do pixel em X (metros/pixel)
    # Linha 2: Rotação em Y (0.0)
    # Linha 3: Rotação em X (0.0)
    # Linha 4: Tamanho do pixel em Y negativo (-metros/pixel)
    # Linha 5: Coordenada X do centro do pixel superior esquerdo
    # Linha 6: Coordenada Y do centro do pixel superior esquerdo
    px_size_x = w_m / float(width_px)
    px_size_y = h_m / float(height_px)
    center_x = extent.xMinimum() + (px_size_x / 2.0)
    center_y = extent.yMaximum() - (px_size_y / 2.0)

    stem, _ = os.path.splitext(output_image_path)
    jgw_path = stem + ".jgw"
    with open(jgw_path, "w", encoding="utf-8") as f:
        f.write(f"{px_size_x:.8f}\n")
        f.write("0.00000000\n")
        f.write("0.00000000\n")
        f.write(f"{-px_size_y:.8f}\n")
        f.write(f"{center_x:.8f}\n")
        f.write(f"{center_y:.8f}\n")

    return {
        'image_path': output_image_path,
        'image_name': os.path.basename(output_image_path),
        'jgw_path': jgw_path,
        'size_in_pixel': (width_px, height_px),
        'size_in_units': (w_m, h_m),
        'insert_point': (extent.xMinimum(), extent.yMinimum(), 0.0),
        'crs_authid': crs.authid()
    }
