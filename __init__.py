# -*- coding: utf-8 -*-
"""Ponto de entrada do plugin Exportador DXF/CAD Pro para o QGIS."""


def classFactory(iface):
    """Instancia a classe principal do plugin quando carregado pelo QGIS."""
    from .plugin import DxfExportPlugin
    return DxfExportPlugin(iface)
