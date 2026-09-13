# -*- coding: utf-8 -*-
"""Configurações padrões e persistência de preferências do Exportador DXF/CAD Pro."""

import json
try:
    from qgis.core import QgsSettings
except ImportError:
    QgsSettings = None

SETTINGS_KEY = "ExportadorDXFPro"

# Configuração padrão de Camadas e Penas (ACI e Lineweight em centésimos de mm)
# text_height_mm: Altura do texto impresso na folha/papel (em milímetros)
DEFAULT_LAYER_CONFIG = {
    '0': {'aci': 7, 'lw': -3, 'text_height_mm': None, 'desc': 'Layer padrão 0'},
    'Rede_Lote': {'aci': 72, 'lw': 20, 'text_height_mm': 2.00, 'desc': 'Lotes cadastrais e hachuras'},
    'Texto_Lote': {'aci': 7, 'lw': 20, 'text_height_mm': 2.00, 'desc': 'Textos e numeração de lote'},
    'Rede_Quadra': {'aci': 32, 'lw': 25, 'text_height_mm': 3.75, 'desc': 'Perímetros e identificação de quadra'},
    'Rede_Meio_Fio': {'aci': 221, 'lw': 25, 'text_height_mm': None, 'desc': 'Meio-fio e calçadas'},
    'Logradouro': {'aci': 8, 'lw': 18, 'text_height_mm': 3.00, 'desc': 'Nomes de ruas, avenidas e vias'},
    'Curva_Nivel_Mestra': {'aci': 14, 'lw': 35, 'text_height_mm': 1.80, 'desc': 'Curvas de nível mestras'},
    'Curva_Nivel_Intermediaria': {'aci': 252, 'lw': 15, 'text_height_mm': None, 'desc': 'Curvas de nível intermediárias'},
    'Nos': {'aci': 7, 'lw': 25, 'text_height_mm': 1.80, 'desc': 'Nós e acessórios da rede'},
    'Rede_DN50': {'aci': 4, 'lw': 40, 'text_height_mm': 2.00, 'desc': 'Rede de água DN 50'},
    'Rede_DN75': {'aci': 3, 'lw': 40, 'text_height_mm': 2.00, 'desc': 'Rede de água DN 75'},
    'Rede_DN100': {'aci': 1, 'lw': 50, 'text_height_mm': 2.00, 'desc': 'Rede de água DN 100'},
    'Rede_DN150': {'aci': 5, 'lw': 50, 'text_height_mm': 2.00, 'desc': 'Rede de água DN 150'},
    'Rede_DN200': {'aci': 6, 'lw': 50, 'text_height_mm': 2.00, 'desc': 'Rede de água DN 200'},
    'Rede_DN250': {'aci': 14, 'lw': 60, 'text_height_mm': 2.00, 'desc': 'Rede de água DN 250'},
    'Rede_DN300': {'aci': 5, 'lw': 60, 'text_height_mm': 2.00, 'desc': 'Rede de água DN 300'},
}

# Regras de correspondência de nomes das camadas do QGIS para o DXF
DEFAULT_NAME_RULES = [
    {'pattern': '2_lote', 'target': 'Rede_Lote'},
    {'pattern': '3_quadra', 'target': 'Rede_Quadra'},
    {'pattern': 'meio_fio', 'target': 'Rede_Meio_Fio'},
    {'pattern': 'logradouro', 'target': 'Logradouro'},
    {'pattern': 'Mestra', 'target': 'Curva_Nivel_Mestra'},
    {'pattern': 'Intermediaria', 'target': 'Curva_Nivel_Intermediaria'},
    {'pattern': 'v_edit_node', 'target': 'Nos'},
    {'pattern': r'^N.{0,3}s$', 'target': 'Nos', 'regex': True},
]

ODA_DEFAULT_PATH = "/Applications/ODAFileConverter.app/Contents/MacOS/ODAFileConverter"


def load_layer_config():
    """Carrega as configurações de camadas do QgsSettings ou retorna padrão."""
    s = QgsSettings()
    val = s.value(f"{SETTINGS_KEY}/layer_config", "")
    if val:
        try:
            cfg = json.loads(val)
            if isinstance(cfg, dict):
                return cfg
        except Exception:
            pass
    return dict(DEFAULT_LAYER_CONFIG)


def save_layer_config(config_dict):
    """Salva as configurações de camadas no QgsSettings."""
    s = QgsSettings()
    s.setValue(f"{SETTINGS_KEY}/layer_config", json.dumps(config_dict, indent=2))


def reset_layer_config():
    """Restaura as configurações de camadas para o padrão de fábrica."""
    save_layer_config(DEFAULT_LAYER_CONFIG)
    return dict(DEFAULT_LAYER_CONFIG)


def get_oda_path():
    """Retorna o caminho do ODA File Converter configurado."""
    s = QgsSettings()
    return s.value(f"{SETTINGS_KEY}/oda_path", ODA_DEFAULT_PATH)


def set_oda_path(path):
    """Salva o caminho do ODA File Converter."""
    s = QgsSettings()
    s.setValue(f"{SETTINGS_KEY}/oda_path", path)
