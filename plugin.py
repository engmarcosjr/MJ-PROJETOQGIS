# -*- coding: utf-8 -*-
"""Classe principal do plugin QGIS Exportador DXF/CAD Pro."""

import os
from qgis.PyQt.QtWidgets import QAction
from qgis.PyQt.QtGui import QIcon
from qgis.PyQt.QtCore import QCoreApplication

from .gui.dialog import DxfExportDialog


class DxfExportPlugin:
    """Plugin QGIS para exportação e recorte inteligente para DXF/DWG."""

    def __init__(self, iface):
        self.iface = iface
        self.plugin_dir = os.path.dirname(__file__)
        self.action = None
        self.menu = "Exportador CAD"
        self.dialog = None

    def tr(self, message):
        return QCoreApplication.translate('DxfExportPlugin', message)

    def initGui(self):
        icon_path = os.path.join(self.plugin_dir, 'resources', 'icon.svg')
        icon = QIcon(icon_path)

        self.action = QAction(icon, self.tr("Exportar Recorte para DXF / CAD Pro"), self.iface.mainWindow())
        self.action.setStatusTip(self.tr("Recorta e exporta camadas ativas para DXF/DWG compatível com AutoCAD"))
        self.action.triggered.connect(self.run)

        # Adicionar à barra de ferramentas e ao menu
        self.iface.addToolBarIcon(self.action)
        self.iface.addPluginToMenu(self.menu, self.action)

    def unload(self):
        if self.action:
            self.iface.removePluginMenu(self.menu, self.action)
            self.iface.removeToolBarIcon(self.action)
            del self.action

    def run(self):
        """Abre a janela de diálogo do exportador."""
        self.dialog = DxfExportDialog(self.iface)
        self.dialog.show()
        self.dialog.raise_()
        self.dialog.activateWindow()
