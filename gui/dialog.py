# -*- coding: utf-8 -*-
"""Interface Gráfica (Dialog) do Exportador DXF/CAD Pro."""

import os
from qgis.PyQt.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QTabWidget, QWidget, QLabel,
    QLineEdit, QPushButton, QComboBox, QCheckBox, QTableWidget,
    QTableWidgetItem, QHeaderView, QFileDialog, QMessageBox, QGroupBox,
    QFormLayout, QSpinBox, QDoubleSpinBox, QProgressBar
)
from qgis.PyQt.QtCore import Qt, pyqtSignal
from qgis.PyQt.QtGui import QColor
from qgis.core import (
    QgsProject, QgsRectangle, QgsApplication, QgsSettings
)

from ..config.settings import (
    load_layer_config, save_layer_config, reset_layer_config,
    get_oda_path, set_oda_path
)
from ..core.exporter import get_active_visible_vector_layers
from ..core.export_task import DxfExportTask
from ..core.scale_calc import paper_mm_to_model_m
from ..core.dxf_processor import is_ezdxf_available
from .extent_tool import MapToolDrawExtent


class DxfExportDialog(QDialog):
    """Janela principal do Exportador DXF/CAD Pro."""

    def __init__(self, iface, parent=None):
        super().__init__(parent or iface.mainWindow())
        self.iface = iface
        self.canvas = iface.mapCanvas()
        self.draw_tool = MapToolDrawExtent(self.canvas)
        self.draw_tool.extentDrawn.connect(self._on_extent_drawn)

        self.custom_extent = None
        self.layer_config = load_layer_config()

        self.setWindowTitle("Exportador DXF / CAD Pro — Saneamento & Urbano")
        self.resize(750, 580)

        self._setup_ui()
        self._load_current_status()

    def _setup_ui(self):
        main_layout = QVBoxLayout(self)

        self.tabs = QTabWidget()
        main_layout.addWidget(self.tabs)

        # Tab 1: Exportação Principal
        tab_main = QWidget()
        self._setup_main_tab(tab_main)
        self.tabs.addTab(tab_main, "📐 Exportação e Recorte")

        # Tab 2: Configuração de Camadas e Penas
        tab_layers = QWidget()
        self._setup_layers_tab(tab_layers)
        self.tabs.addTab(tab_layers, "🎨 Camadas, Cores (ACI) e Textos")

        # Barra de Progresso e Botões
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        main_layout.addWidget(self.progress_bar)

        btn_layout = QHBoxLayout()
        self.lbl_status = QLabel("")
        btn_layout.addWidget(self.lbl_status)
        btn_layout.addStretch()

        self.btn_cancel = QPushButton("Fechar")
        self.btn_cancel.clicked.connect(self.reject)
        btn_layout.addWidget(self.btn_cancel)

        self.btn_export = QPushButton("🚀 Exportar para DXF/DWG")
        self.btn_export.setStyleSheet("font-weight: bold; padding: 6px 16px; background-color: #0078d7; color: white;")
        self.btn_export.clicked.connect(self._start_export)
        btn_layout.addWidget(self.btn_export)

        main_layout.addLayout(btn_layout)

    def _setup_main_tab(self, parent):
        layout = QVBoxLayout(parent)

        # Grupo: Área de Recorte
        gb_area = QGroupBox("1. Área de Recorte Espacial")
        area_layout = QVBoxLayout(gb_area)

        h_area_btns = QHBoxLayout()
        self.btn_extent_canvas = QPushButton("🖥️ Capturar Extensão da Tela Visível")
        self.btn_extent_canvas.clicked.connect(self._set_canvas_extent)
        h_area_btns.addWidget(self.btn_extent_canvas)

        self.btn_extent_draw = QPushButton("✏️ Desenhar Retângulo no Mapa")
        self.btn_extent_draw.clicked.connect(self._start_draw_extent)
        h_area_btns.addWidget(self.btn_extent_draw)

        area_layout.addLayout(h_area_btns)

        self.lbl_extent_info = QLabel("Extensão selecionada: Nenhuma (clique em um botão acima)")
        self.lbl_extent_info.setStyleSheet("color: #555; font-style: italic;")
        area_layout.addWidget(self.lbl_extent_info)

        self.chk_clip_geoms = QCheckBox("Recortar geometrias rigorosamente na borda da BBox (linhas e polígonos)")
        self.chk_clip_geoms.setChecked(True)
        area_layout.addWidget(self.chk_clip_geoms)

        layout.addWidget(gb_area)

        # Grupo: Escala e Proporções
        gb_scale = QGroupBox("2. Escala Alvo da Prancha (Ajusta Alturas de Texto)")
        scale_layout = QHBoxLayout(gb_scale)

        scale_layout.addWidget(QLabel("Escala 1 :"))
        self.combo_scale = QComboBox()
        self.combo_scale.setEditable(True)
        self.combo_scale.addItems(["250", "500", "750", "800", "1000", "1250", "1500", "2000", "2500", "5000"])
        self.combo_scale.setCurrentText("800")
        self.combo_scale.currentTextChanged.connect(self._on_scale_changed)
        scale_layout.addWidget(self.combo_scale)

        self.lbl_scale_calc = QLabel("(Na escala 1:800 -> Texto de lote = 1.60m | Rua = 2.40m | Quadra = 3.00m)")
        self.lbl_scale_calc.setStyleSheet("color: #0066cc;")
        scale_layout.addWidget(self.lbl_scale_calc)
        scale_layout.addStretch()

        layout.addWidget(gb_scale)

        # Grupo: Camadas Ativas Detectadas
        gb_layers = QGroupBox("3. Camadas Vetoriais Ativas")
        layers_vbox = QVBoxLayout(gb_layers)
        self.lbl_layers_count = QLabel("Detectando camadas visíveis no QGIS...")
        layers_vbox.addWidget(self.lbl_layers_count)
        layout.addWidget(gb_layers)

        # Grupo: Destino dos Arquivos
        gb_dest = QGroupBox("4. Destino e Conversão")
        dest_form = QFormLayout(gb_dest)

        h_dest = QHBoxLayout()
        self.txt_out_path = QLineEdit()
        default_dir = os.path.expanduser("~/Downloads")
        self.txt_out_path.setText(os.path.join(default_dir, "projeto_exportado.dxf"))
        h_dest.addWidget(self.txt_out_path)

        self.btn_browse = QPushButton("Procurar...")
        self.btn_browse.clicked.connect(self._browse_output)
        h_dest.addWidget(self.btn_browse)
        dest_form.addRow("Arquivo DXF:", h_dest)

        self.chk_generate_dwg = QCheckBox("Gerar também arquivo DWG nativo (AutoCAD 2018 via ODA Converter)")
        self.chk_generate_dwg.setChecked(os.path.exists(get_oda_path()))
        dest_form.addRow("", self.chk_generate_dwg)

        layout.addWidget(gb_dest)
        layout.addStretch()

    def _setup_layers_tab(self, parent):
        layout = QVBoxLayout(parent)

        lbl_desc = QLabel(
            "Configure as cores (ACI do AutoCAD), espessuras de pena e alturas de texto no papel (em mm).\n"
            "O plugin calcula automaticamente as alturas no Model do CAD de acordo com a escala escolhida."
        )
        lbl_desc.setWordWrap(True)
        layout.addWidget(lbl_desc)

        self.tbl_layers = QTableWidget()
        self.tbl_layers.setColumnCount(5)
        self.tbl_layers.setHorizontalHeaderLabels([
            "Camada CAD", "Cor ACI", "Pena (0.01 mm)", "Texto Papel (mm)", "Descrição"
        ])
        self.tbl_layers.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.tbl_layers.horizontalHeader().setSectionResizeMode(4, QHeaderView.Stretch)
        layout.addWidget(self.tbl_layers)

        self._populate_layers_table()

        btn_bar = QHBoxLayout()
        self.btn_reset_cfg = QPushButton("Restaurar Padrões")
        self.btn_reset_cfg.clicked.connect(self._reset_to_defaults)
        btn_bar.addWidget(self.btn_reset_cfg)

        btn_bar.addStretch()
        self.btn_save_cfg = QPushButton("Salvar Configurações")
        self.btn_save_cfg.clicked.connect(self._save_table_config)
        btn_bar.addWidget(self.btn_save_cfg)

        layout.addLayout(btn_bar)

    def _populate_layers_table(self):
        self.tbl_layers.setRowCount(0)
        for row, (name, cfg) in enumerate(self.layer_config.items()):
            self.tbl_layers.insertRow(row)

            item_name = QTableWidgetItem(name)
            item_is_editable = getattr(getattr(Qt, 'ItemFlag', None), 'ItemIsEditable', getattr(Qt, 'ItemIsEditable', 0))
            item_name.setFlags(item_name.flags() & ~item_is_editable)
            self.tbl_layers.setItem(row, 0, item_name)

            item_aci = QTableWidgetItem(str(cfg.get('aci', 7)))
            self.tbl_layers.setItem(row, 1, item_aci)

            item_lw = QTableWidgetItem(str(cfg.get('lw', 20)))
            self.tbl_layers.setItem(row, 2, item_lw)

            txt_mm = cfg.get('text_height_mm')
            item_txt = QTableWidgetItem(f"{txt_mm:.2f}" if txt_mm else "-")
            self.tbl_layers.setItem(row, 3, item_txt)

            item_desc = QTableWidgetItem(cfg.get('desc', ''))
            self.tbl_layers.setItem(row, 4, item_desc)

    def _save_table_config(self):
        new_config = {}
        for row in range(self.tbl_layers.rowCount()):
            name = self.tbl_layers.item(row, 0).text()
            try:
                aci = int(self.tbl_layers.item(row, 1).text())
                lw = int(self.tbl_layers.item(row, 2).text())
            except ValueError:
                QMessageBox.warning(self, "Aviso", f"Valores de ACI ou Pena inválidos na linha {row+1}.")
                return

            txt_str = self.tbl_layers.item(row, 3).text().strip()
            txt_mm = None
            if txt_str and txt_str != "-":
                try:
                    txt_mm = float(txt_str)
                except ValueError:
                    pass

            desc = self.tbl_layers.item(row, 4).text()

            new_config[name] = {
                'aci': aci,
                'lw': lw,
                'text_height_mm': txt_mm,
                'desc': desc
            }

        self.layer_config = new_config
        save_layer_config(new_config)
        self._on_scale_changed(self.combo_scale.currentText())
        QMessageBox.information(self, "Sucesso", "Configurações de camadas salvas com sucesso!")

    def _reset_to_defaults(self):
        reply = QMessageBox.question(
            self, "Confirmar", "Deseja restaurar as configurações de camadas para o padrão original?",
            QMessageBox.Yes | QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            self.layer_config = reset_layer_config()
            self._populate_layers_table()
            self._on_scale_changed(self.combo_scale.currentText())

    def _load_current_status(self):
        # Detectar camadas ativas
        active_layers = get_active_visible_vector_layers()
        names = [l.name() for l in active_layers]
        self.lbl_layers_count.setText(
            f"✅ <b>{len(active_layers)} camadas vetoriais visíveis detectadas:</b> "
            f"<span style='color: #444;'>{', '.join(names[:5])}{'...' if len(names) > 5 else ''}</span>"
        )
        self._set_canvas_extent()

    def _set_canvas_extent(self):
        extent = self.canvas.extent()
        self.custom_extent = extent
        crs = self.canvas.mapSettings().destinationCrs().authid()
        self.lbl_extent_info.setText(
            f"🖥️ Extensão da tela visível [{crs}]:\n"
            f"X: {extent.xMinimum():.2f} a {extent.xMaximum():.2f} | "
            f"Y: {extent.yMinimum():.2f} a {extent.yMaximum():.2f} "
            f"({extent.width():.1f}m x {extent.height():.1f}m)"
        )

    def _start_draw_extent(self):
        self.hide()
        self.canvas.setMapTool(self.draw_tool)

    def _on_extent_drawn(self, rect):
        self.canvas.unsetMapTool(self.draw_tool)
        self.custom_extent = rect
        crs = self.canvas.mapSettings().destinationCrs().authid()
        self.lbl_extent_info.setText(
            f"✏️ Retângulo desenhado no mapa [{crs}]:\n"
            f"X: {rect.xMinimum():.2f} a {rect.xMaximum():.2f} | "
            f"Y: {rect.yMinimum():.2f} a {rect.yMaximum():.2f} "
            f"({rect.width():.1f}m x {rect.height():.1f}m)"
        )
        self.show()
        self.raise_()
        self.activateWindow()

    def _on_scale_changed(self, text):
        try:
            denom = float(text)
            h_lote = paper_mm_to_model_m(2.0, denom)
            h_rua = paper_mm_to_model_m(3.0, denom)
            h_quadra = paper_mm_to_model_m(3.75, denom)
            self.lbl_scale_calc.setText(
                f"(Na escala 1:{int(denom)} -> Lote = {h_lote:.2f}m | Rua = {h_rua:.2f}m | Quadra = {h_quadra:.2f}m)"
            )
        except ValueError:
            pass

    def _browse_output(self):
        path, _ = QFileDialog.getSaveFileName(
            self, "Salvar DXF de Saída", self.txt_out_path.text(), "Arquivo AutoCAD DXF (*.dxf)"
        )
        if path:
            if not path.lower().endswith(".dxf"):
                path += ".dxf"
            self.txt_out_path.setText(path)

    def _start_export(self):
        if not is_ezdxf_available():
            QMessageBox.critical(
                self, "Dependência Ausente",
                "A biblioteca Python 'ezdxf' não está instalada no ambiente do QGIS.\n\n"
                "Para instalá-la no Mac, abra o Terminal e execute:\n"
                "pip install ezdxf"
            )
            return

        active_layers = get_active_visible_vector_layers()
        if not active_layers:
            QMessageBox.warning(self, "Aviso", "Nenhuma camada vetorial visível encontrada no projeto.")
            return

        if not self.custom_extent or self.custom_extent.isEmpty():
            QMessageBox.warning(self, "Aviso", "Defina uma área de recorte válida antes de exportar.")
            return

        try:
            scale_denom = float(self.combo_scale.currentText())
        except ValueError:
            QMessageBox.warning(self, "Aviso", "A escala digitada é inválida.")
            return

        output_dxf = self.txt_out_path.text().strip()
        if not output_dxf:
            QMessageBox.warning(self, "Aviso", "Selecione o caminho do arquivo DXF de saída.")
            return

        crs = self.canvas.mapSettings().destinationCrs()
        generate_dwg = self.chk_generate_dwg.isChecked()
        oda_path = get_oda_path()

        # Iniciar QgsTask em segundo plano
        self.btn_export.setEnabled(False)
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)
        self.lbl_status.setText("Exportando em segundo plano...")

        task = DxfExportTask(
            description="Exportação DXF/CAD Pro",
            layers=active_layers,
            extent=self.custom_extent,
            crs=crs,
            scale_denom=scale_denom,
            output_dxf_path=output_dxf,
            layer_config=self.layer_config,
            clip_geometries=self.chk_clip_geoms.isChecked(),
            generate_dwg=generate_dwg,
            oda_bin_path=oda_path,
            on_success=self._on_export_success,
            on_error=self._on_export_error
        )

        task.progressChanged.connect(self.progress_bar.setValue)
        QgsApplication.taskManager().addTask(task)

    def _on_export_success(self, out_path):
        self.btn_export.setEnabled(True)
        self.progress_bar.setVisible(False)
        self.lbl_status.setText("✅ Exportado com sucesso!")

        dwg_msg = ""
        dwg_path = os.path.splitext(out_path)[0] + ".dwg"
        if self.chk_generate_dwg.isChecked() and os.path.exists(dwg_path):
            dwg_msg = f"\n\nArquivo DWG nativo gerado:\n👉 {dwg_path}"

        QMessageBox.information(
            self, "Sucesso",
            f"Projeto recortado e exportado com sucesso!\n\n"
            f"Arquivo DXF gerado:\n👉 {out_path}{dwg_msg}"
        )

    def _on_export_error(self, ex):
        self.btn_export.setEnabled(True)
        self.progress_bar.setVisible(False)
        self.lbl_status.setText("❌ Erro na exportação.")
        QMessageBox.critical(self, "Erro na Exportação", f"Ocorreu um erro durante a exportação:\n\n{str(ex)}")
