# -*- coding: utf-8 -*-
"""Motor de exportação e recorte do QGIS para DXF/DWG usando a API nativa QgsDxfExport."""

import os
import tempfile
from qgis.core import (
    QgsProject,
    QgsRectangle,
    QgsCoordinateReferenceSystem,
    QgsWkbTypes,
    QgsMapLayer,
    QgsDxfExport,
)
from qgis.PyQt.QtCore import QFile
import processing

from .scale_calc import get_text_heights_for_scale
from .dxf_processor import post_process_dxf, convert_to_dwg_with_oda


def get_active_visible_vector_layers():
    """Retorna a lista de camadas vetoriais atualmente visíveis no projeto QGIS."""
    project = QgsProject.instance()
    root = project.layerTreeRoot()
    visible_layers = []

    for tree_layer in root.findLayers():
        if tree_layer.isVisible():
            layer = tree_layer.layer()
            if layer and layer.isValid() and layer.type() == QgsMapLayer.VectorLayer:
                visible_layers.append(layer)

    return visible_layers


def run_export_pipeline(
    layers: list,
    extent: QgsRectangle,
    crs: QgsCoordinateReferenceSystem,
    scale_denom: float,
    output_dxf_path: str,
    layer_config: dict,
    name_rules=None,
    clip_geometries: bool = True,
    generate_dwg: bool = False,
    oda_bin_path: str = None,
    feedback=None
):
    """Executa o pipeline completo:

    1. Recorte espacial das camadas ativas (geométrico para linhas/polígonos, seleção para pontos)
    2. Exportação para DXF via motor nativo C++ QgsDxfExport
    3. Pós-processamento canônico com ezdxf (ByLayer, MTEXT com alturas proporcionais, hachuras)
    4. Conversão para DWG via ODA (opcional)
    """
    if not layers:
        raise ValueError("Nenhuma camada vetorial ativa selecionada para exportação.")

    if extent is None or extent.isEmpty():
        raise ValueError("A extensão de recorte (Bounding Box) é inválida ou está vazia.")

    with tempfile.TemporaryDirectory(prefix="qgis_dxf_pro_") as temp_dir:
        dxf_layers_to_export = []
        total_layers = len(layers)

        for idx, layer in enumerate(layers):
            if feedback and feedback.isCanceled():
                return False

            geom_type = layer.geometryType()
            # Pontos não sofrem clip geométrico, apenas recorte por extensão
            do_clip = clip_geometries and (geom_type != QgsWkbTypes.PointGeometry)

            pct = int(10 + (idx / total_layers) * 40)
            if feedback:
                feedback.setProgress(pct)
                feedback.setProgressText(f"Recortando camada ({idx+1}/{total_layers}): {layer.name()}")

            # Executar extractbyextent com ou sem clip
            try:
                params = {
                    'INPUT': layer,
                    'EXTENT': extent,
                    'CLIP': do_clip,
                    'OUTPUT': 'TEMPORARY_OUTPUT'
                }
                res = processing.run("native:extractbyextent", params)
                temp_layer = res.get('OUTPUT')

                if temp_layer and temp_layer.featureCount() > 0:
                    # Manter o nome original da camada para o mapeador de layers reconhecer
                    temp_layer.setName(layer.name())

                    # Checar se a camada tem campo de diâmetro para separação automática em camadas
                    split_idx = -1
                    for fname in ['cat_dnom', 'dnom', 'diametro', 'DN']:
                        idx_found = temp_layer.fields().indexFromName(fname)
                        if idx_found != -1:
                            split_idx = idx_found
                            break

                    dxf_layer = QgsDxfExport.DxfLayer(temp_layer, split_idx)
                    dxf_layers_to_export.append(dxf_layer)
            except Exception as ex:
                if feedback:
                    feedback.reportError(f"Aviso ao recortar '{layer.name()}': {ex}")

        if not dxf_layers_to_export:
            raise RuntimeError("Nenhuma entidade geométrica foi encontrada dentro da área de recorte especificada.")

        if feedback and feedback.isCanceled():
            return False

        if feedback:
            feedback.setProgress(55)
            feedback.setProgressText("Exportando camadas recortadas via QgsDxfExport...")

        raw_dxf = os.path.join(temp_dir, "raw_export.dxf")

        # Configurar o exportador oficial C++ do QGIS
        dxf_exporter = QgsDxfExport()
        dxf_exporter.setExtent(extent)
        dxf_exporter.setDestinationCrs(crs)
        dxf_exporter.setSymbologyScale(scale_denom)

        symb_mode = getattr(getattr(QgsDxfExport, 'SymbologyExport', None), 'SymbolLayerSymbology', 2)
        dxf_exporter.setSymbologyExport(symb_mode)
        dxf_exporter.addLayers(dxf_layers_to_export)

        qfile = QFile(raw_dxf)
        open_flags = getattr(getattr(QFile, 'OpenModeFlag', None), 'WriteOnly', getattr(QFile, 'WriteOnly', 2))
        if not qfile.open(open_flags):
            raise RuntimeError(f"Não foi possível abrir o arquivo intermediário: {raw_dxf}")

        export_res = dxf_exporter.writeToFile(qfile, "cp1252")
        qfile.close()

        if not os.path.exists(raw_dxf) or os.path.getsize(raw_dxf) == 0:
            raise RuntimeError(f"Falha na geração do DXF intermediário (código QGIS: {export_res}).")

        if feedback and feedback.isCanceled():
            return False

        if feedback:
            feedback.setProgress(70)
            feedback.setProgressText("Formatando e aplicando pós-processamento CAD...")

        # 3. Calcular alturas de texto para a escala escolhida
        text_heights_in_m = get_text_heights_for_scale(layer_config, scale_denom)

        # 4. Pós-processador ezdxf (ByLayer, MTEXT nativo, ACI, transparências)
        def dxf_progress(pct, msg):
            if feedback:
                feedback.setProgress(70 + int(pct * 0.20))
                feedback.setProgressText(msg)

        post_process_dxf(
            dxf_path=raw_dxf,
            output_dxf_path=output_dxf_path,
            layer_config=layer_config,
            text_heights_in_m=text_heights_in_m,
            name_rules=name_rules,
            progress_callback=dxf_progress
        )

        if feedback and feedback.isCanceled():
            return False

        # 5. Conversão para DWG (se requisitado)
        if generate_dwg and oda_bin_path and os.path.exists(oda_bin_path):
            if feedback:
                feedback.setProgress(92)
                feedback.setProgressText("Convertendo para DWG nativo via ODA File Converter...")
            convert_to_dwg_with_oda(output_dxf_path, oda_bin_path)

        if feedback:
            feedback.setProgress(100)
            feedback.setProgressText("Concluído com sucesso!")

    return True
