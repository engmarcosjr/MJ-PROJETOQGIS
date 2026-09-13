# -*- coding: utf-8 -*-
"""Execução síncrona com processEvents para manter a interface responsiva e segura no PyQGIS."""

from qgis.PyQt.QtCore import QCoreApplication
from qgis.core import QgsMessageLog, Qgis
from .exporter import run_export_pipeline


class GuiFeedback:
    """Feedback com atualização visual direta da barra de progresso."""

    def __init__(self, progress_bar=None, status_label=None):
        self.progress_bar = progress_bar
        self.status_label = status_label
        self._canceled = False

    def setProgress(self, pct):
        if self.progress_bar:
            self.progress_bar.setValue(int(pct))
        QCoreApplication.processEvents()

    def setProgressText(self, text):
        if self.status_label:
            self.status_label.setText(text)
        QgsMessageLog.logMessage(text, "Exportador DXF Pro", Qgis.Info)
        QCoreApplication.processEvents()

    def isCanceled(self):
        return self._canceled

    def cancel(self):
        self._canceled = True

    def reportError(self, err):
        QgsMessageLog.logMessage(str(err), "Exportador DXF Pro", Qgis.Warning)
        QCoreApplication.processEvents()


def execute_export(
    layers: list,
    extent,
    crs,
    scale_denom: float,
    output_dxf_path: str,
    layer_config: dict,
    name_rules=None,
    clip_geometries: bool = True,
    generate_dwg: bool = False,
    oda_bin_path: str = None,
    feedback=None
):
    """Executa o pipeline chamando as rotinas com feedback contínuo."""
    return run_export_pipeline(
        layers=layers,
        extent=extent,
        crs=crs,
        scale_denom=scale_denom,
        output_dxf_path=output_dxf_path,
        layer_config=layer_config,
        name_rules=name_rules,
        clip_geometries=clip_geometries,
        generate_dwg=generate_dwg,
        oda_bin_path=oda_bin_path,
        feedback=feedback
    )
