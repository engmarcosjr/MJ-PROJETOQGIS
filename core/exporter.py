# -*- coding: utf-8 -*-
"""Motor de exportação e recorte do QGIS para DXF/DWG."""

import os
import tempfile
from qgis.core import (
    QgsProject,
    QgsRectangle,
    QgsCoordinateReferenceSystem,
    QgsWkbTypes,
    QgsMapLayer,
    QgsProcessingFeatureSourceDefinition,
)
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
    2. Exportação para DXF via QGIS native:dxfexport
    3. Pós-processamento canônico com ezdxf (ByLayer, MTEXT com alturas proporcionais, hachuras)
    4. Conversão para DWG via ODA (opcional)
    """
    if not layers:
        raise ValueError("Nenhuma camada vetorial ativa selecionada para exportação.")

    if extent is None or extent.isEmpty():
        raise ValueError("A extensão de recorte (Bounding Box) é inválida ou está vazia.")

    extent_str = f"{extent.xMinimum()},{extent.xMaximum()},{extent.yMinimum()},{extent.yMaximum()} [{crs.authid()}]"

    with tempfile.TemporaryDirectory(prefix="qgis_dxf_pro_") as temp_dir:
        clipped_layers_config = []
        total_layers = len(layers)

        for idx, layer in enumerate(layers):
            if feedback and feedback.isCanceled():
                return False

            geom_type = layer.geometryType()
            # Nós e pontos não sofrem clip geométrico, apenas filtro por extensão
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
                res = processing.run("native:extractbyextent", params, feedback=feedback)
                temp_layer = res.get('OUTPUT')

                if temp_layer and temp_layer.featureCount() > 0:
                    # Checar se a camada tem campo de diâmetro (cat_dnom ou similar) para separação automática
                    split_field = None
                    for fname in ['cat_dnom', 'dnom', 'diametro', 'DN']:
                        if fname in [f.name() for f in temp_layer.fields()]:
                            split_field = fname
                            break

                    layer_spec = {
                        'layer': temp_layer,
                        'attributeFieldIndex': temp_layer.fields().indexFromName(split_field) if split_field else -1
                    }
                    clipped_layers_config.append(layer_spec)
                elif temp_layer:
                    # Se não tem feições no recorte, incluímos sem split se desejado ou ignoramos
                    pass
            except Exception as ex:
                if feedback:
                    feedback.reportError(f"Aviso ao recortar '{layer.name()}': {ex}")

        if not clipped_layers_config:
            raise RuntimeError("Nenhuma entidade geométrica foi encontrada dentro da área de recorte especificada.")

        if feedback and feedback.isCanceled():
            return False

        if feedback:
            feedback.setProgress(55)
            feedback.setProgressText("Exportando camadas recortadas via DXF QGIS...")

        raw_dxf = os.path.join(temp_dir, "raw_export.dxf")

        dxf_params = {
            'LAYERS': clipped_layers_config,
            'SYMBOLOGY_MODE': 2,  # Symbol Layer Symbology para preservar hachuras e estilos
            'SYMBOLOGY_SCALE': scale_denom,
            'ENCODING': 18,       # cp1252
            'CRS': crs,
            'USE_LAYER_TITLE': False,
            'FORCE_2D': False,
            'MTEXT': True,
            'OUTPUT': raw_dxf
        }

        processing.run("native:dxfexport", dxf_params, feedback=feedback)

        if not os.path.exists(raw_dxf):
            raise RuntimeError("Falha ao gerar o arquivo DXF intermediário do QGIS.")

        if feedback and feedback.isCanceled():
            return False

        if feedback:
            feedback.setProgress(70)
            feedback.setProgressText("Calculando proporções e aplicando pós-processamento CAD...")

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
