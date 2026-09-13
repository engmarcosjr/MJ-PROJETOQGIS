#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Modelos e definições paramétricas de Pranchas, Margens e Carimbos conforme normas ABNT.
NBR 16752 (Dimensões de Folhas e Margens) e NBR 16861 (Carimbo/Identificação).
"""

from typing import Dict, List, Tuple

# Dimensões nominais em milímetros (Largura x Altura) em orientação Paisagem (Landscape)
SHEET_SIZES = {
    "A0": {"width": 1189.0, "height": 841.0, "left_margin": 25.0, "other_margin": 10.0},
    "A1": {"width": 841.0,  "height": 594.0, "left_margin": 25.0, "other_margin": 10.0},
    "A2": {"width": 594.0,  "height": 420.0, "left_margin": 25.0, "other_margin": 7.0},
    "A3": {"width": 420.0,  "height": 297.0, "left_margin": 25.0, "other_margin": 7.0},
    "A4": {"width": 297.0,  "height": 210.0, "left_margin": 25.0, "other_margin": 7.0},
}

# Largura e Altura padrão do carimbo ABNT (milímetros)
TITLE_BLOCK_WIDTH = 178.0
TITLE_BLOCK_HEIGHT = 60.0

def get_sheet_geometry(sheet_name: str, orientation: str = "landscape") -> Dict:
    """
    Retorna as coordenadas da folha, margens e área útil para desenho.
    A origem (0, 0) é o canto inferior esquerdo da folha de corte.
    """
    sheet_name = sheet_name.upper()
    if sheet_name not in SHEET_SIZES:
        raise ValueError(f"Formato de folha desconhecido: {sheet_name}. Disponíveis: {list(SHEET_SIZES.keys())}")

    base = SHEET_SIZES[sheet_name]
    w = base["width"]
    h = base["height"]

    if orientation == "portrait":
        w, h = h, w

    lm = base["left_margin"]
    om = base["other_margin"]

    # Moldura interna de margem
    margin_min_x = lm
    margin_min_y = om
    margin_max_x = w - om
    margin_max_y = h - om

    inner_w = margin_max_x - margin_min_x
    inner_h = margin_max_y - margin_min_y

    # Área reservada para o carimbo (canto inferior direito da margem)
    tb_w = TITLE_BLOCK_WIDTH
    tb_h = TITLE_BLOCK_HEIGHT

    # Se a folha for A4 ou A3 muito apertada, o carimbo ocupa a base
    tb_x0 = margin_max_x - tb_w
    tb_y0 = margin_min_y
    tb_x1 = margin_max_x
    tb_y1 = margin_min_y + tb_h

    # Área útil primária disponível para o Viewport principal:
    # A área útil inteira desconta o carimbo.
    # No caso padrão, deixamos uma margem de folga entre a viewport e a margem/carimbo.
    viewport_padding = 5.0

    return {
        "sheet_name": sheet_name,
        "orientation": orientation,
        "sheet_width": w,
        "sheet_height": h,
        # Bounding box da folha física (0, 0 até W, H)
        "sheet_box": (0.0, 0.0, w, h),
        # Bounding box da margem interna
        "margin_box": (margin_min_x, margin_min_y, margin_max_x, margin_max_y),
        "margin_width": inner_w,
        "margin_height": inner_h,
        # Carimbo
        "title_block_box": (tb_x0, tb_y0, tb_x1, tb_y1),
        "title_block_width": tb_w,
        "title_block_height": tb_h,
        # Área útil máxima de desenho considerando o carimbo no canto
        # Para um viewport retangular simples ocupando o espaço acima ou ao lado
        "drawing_area_width": inner_w - (viewport_padding * 2),
        "drawing_area_height": inner_h - tb_h - (viewport_padding * 2),
    }

def draw_sheet_border(layout, geom: Dict, doc) -> None:
    """
    Desenha no PaperSpace (Layout) a folha de corte, a margem ABNT e o carimbo.
    Garante camadas canônicas e estilo limpo ByLayer.
    """
    # 1. Garantir camadas canônicas de prancha
    layers_to_create = {
        "_PRANCHA_FOLHA":   {"color": 7, "lineweight": 15},   # Linha fina de corte
        "_PRANCHA_MARGEM":  {"color": 7, "lineweight": 50},   # Borda grossa da margem
        "_PRANCHA_CARIMBO": {"color": 7, "lineweight": 25},   # Linhas internas do selo
        "_PRANCHA_TEXTO":   {"color": 7, "lineweight": 20},   # Textos do carimbo
        "Defpoints":        {"color": 7, "lineweight": -3},   # Viewport (não plota)
    }

    for lay_name, props in layers_to_create.items():
        if not doc.layers.has_entry(lay_name):
            doc.layers.new(lay_name, dxfattribs={"color": props["color"], "lineweight": props["lineweight"]})

    w = geom["sheet_width"]
    h = geom["sheet_height"]
    mx0, my0, mx1, my1 = geom["margin_box"]

    # Folha de corte externa
    layout.add_lwpolyline(
        [(0.0, 0.0), (w, 0.0), (w, h), (0.0, h)],
        close=True,
        dxfattribs={"layer": "_PRANCHA_FOLHA"}
    )

    # Margem ABNT interna
    layout.add_lwpolyline(
        [(mx0, my0), (mx1, my0), (mx1, my1), (mx0, my1)],
        close=True,
        dxfattribs={"layer": "_PRANCHA_MARGEM"}
    )

def draw_title_block(layout, geom: Dict, info: Dict) -> None:
    """
    Desenha o carimbo / selo técnico com subdivisões e textos formatados em MTEXT.
    info contém: title, client, discipline, scale_str, date, sheet_num, engineer.
    """
    tx0, ty0, tx1, ty1 = geom["title_block_box"]
    w = geom["title_block_width"]
    h = geom["title_block_height"]

    # Contorno externo do carimbo
    layout.add_lwpolyline(
        [(tx0, ty0), (tx1, ty0), (tx1, ty1), (tx0, ty1)],
        close=True,
        dxfattribs={"layer": "_PRANCHA_CARIMBO"}
    )

    # Linhas divisórias horizontais
    y_div1 = ty0 + 35.0
    y_div2 = ty0 + 18.0
    layout.add_line((tx0, y_div1), (tx1, y_div1), dxfattribs={"layer": "_PRANCHA_CARIMBO"})
    layout.add_line((tx0, y_div2), (tx1, y_div2), dxfattribs={"layer": "_PRANCHA_CARIMBO"})

    # Linhas verticais da base (Escala, Data, Prancha)
    x_div1 = tx0 + 60.0
    x_div2 = tx0 + 120.0
    layout.add_line((x_div1, ty0), (x_div1, y_div2), dxfattribs={"layer": "_PRANCHA_CARIMBO"})
    layout.add_line((x_div2, ty0), (x_div2, y_div2), dxfattribs={"layer": "_PRANCHA_CARIMBO"})

    # Helper para adicionar MTEXT padrão sem estilos quebrados do Mac
    def add_label(text: str, pos: Tuple[float, float], height: float = 2.2, bold: bool = False):
        b_code = "b1" if bold else "b0"
        mtext_content = f"\\fArial|i0|{b_code};" + text.replace(" ", "\\~")
        layout.add_mtext(
            mtext_content,
            dxfattribs={
                "layer": "_PRANCHA_TEXTO",
                "char_height": height,
                "insert": pos,
                "attachment_point": 1, # Top Left
                "width": 0.0,
                "flow_direction": 5,
                "line_spacing_style": 1
            }
        )

    # Preenchimento dos campos do Carimbo
    client = info.get("client", "CLIENTE / MUNICÍPIO")
    title = info.get("title", "PROJETO EXECUTIVO")
    content = info.get("content", "PLANTA BAIXA / REDE")
    engineer = info.get("engineer", "MARCOS JR - ENG. CIVIL")
    crea = info.get("crea", "CREA/CAU: REGISTRO")
    scale_str = info.get("scale", "1:1000")
    date_str = info.get("date", "SET/2026")
    prancha_str = info.get("sheet_num", "01/01")

    # Bloco Superior: Cliente e Projeto
    add_label("PROPRIETÁRIO / CLIENTE:", (tx0 + 3.0, ty1 - 2.0), height=1.6)
    add_label(client, (tx0 + 3.0, ty1 - 5.0), height=2.4, bold=True)

    add_label("TÍTULO DO PROJETO:", (tx0 + 3.0, ty1 - 12.0), height=1.6)
    add_label(title, (tx0 + 3.0, ty1 - 15.0), height=2.8, bold=True)

    add_label("CONTEÚDO DA PRANCHA:", (tx0 + 3.0, ty1 - 22.0), height=1.6)
    add_label(content, (tx0 + 3.0, ty1 - 25.0), height=2.6, bold=True)

    # Bloco Intermediário: Responsável Técnico
    add_label("RESPONSÁVEL TÉCNICO:", (tx0 + 3.0, y_div1 - 2.0), height=1.6)
    add_label(engineer, (tx0 + 3.0, y_div1 - 5.5), height=2.4, bold=True)
    add_label(crea, (tx0 + 3.0, y_div1 - 10.0), height=1.8)

    # Bloco Inferior: Escala, Data, Prancha
    add_label("ESCALA:", (tx0 + 3.0, y_div2 - 2.0), height=1.6)
    add_label(scale_str, (tx0 + 3.0, y_div2 - 6.0), height=3.0, bold=True)

    add_label("DATA:", (x_div1 + 3.0, y_div2 - 2.0), height=1.6)
    add_label(date_str, (x_div1 + 3.0, y_div2 - 6.0), height=2.4, bold=True)

    add_label("PRANCHA:", (x_div2 + 3.0, y_div2 - 2.0), height=1.6)
    add_label(prancha_str, (x_div2 + 3.0, y_div2 - 6.0), height=3.2, bold=True)
