# -*- coding: utf-8 -*-
"""Execução em segundo plano via QgsTask para não congelar o QGIS."""

from qgis.core import QgsTask, QgsMessageLog, Qgis
from .exporter import run_export_pipeline


class DxfExportTask(QgsTask):
    """QgsTask para recorte e exportação DXF/DWG em segundo plano."""

    def __init__(
        self,
        description: str,
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
        on_success=None,
        on_error=None
    ):
        super().__init__(description, QgsTask.CanCancel)
        self.layers = layers
        self.extent = extent
        self.crs = crs
        self.scale_denom = scale_denom
        self.output_dxf_path = output_dxf_path
        self.layer_config = layer_config
        self.name_rules = name_rules
        self.clip_geometries = clip_geometries
        self.generate_dwg = generate_dwg
        self.oda_bin_path = oda_bin_path
        self.on_success = on_success
        self.on_error = on_error
        self.exception = None

    def run(self):
        try:
            # Feedback adapter
            class TaskFeedback:
                def __init__(self, task):
                    self.task = task

                def setProgress(self, pct):
                    self.task.setProgress(pct)

                def setProgressText(self, text):
                    QgsMessageLog.logMessage(text, "Exportador DXF Pro", Qgis.Info)

                def isCanceled(self):
                    return self.task.isCanceled()

                def reportError(self, err):
                    QgsMessageLog.logMessage(err, "Exportador DXF Pro", Qgis.Warning)

            feedback = TaskFeedback(self)

            return run_export_pipeline(
                layers=self.layers,
                extent=self.extent,
                crs=self.crs,
                scale_denom=self.scale_denom,
                output_dxf_path=self.output_dxf_path,
                layer_config=self.layer_config,
                name_rules=self.name_rules,
                clip_geometries=self.clip_geometries,
                generate_dwg=self.generate_dwg,
                oda_bin_path=self.oda_bin_path,
                feedback=feedback
            )
        except Exception as ex:
            self.exception = ex
            return False

    def finished(self, result):
        if result:
            if self.on_success:
                self.on_success(self.output_dxf_path)
        else:
            if not self.isCanceled() and self.on_error:
                self.on_error(self.exception or Exception("Processo abortado."))
