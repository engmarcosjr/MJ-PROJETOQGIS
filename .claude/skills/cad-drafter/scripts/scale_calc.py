#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Motor de cálculo de escalas para projetos de engenharia e CAD conforme ABNT NBR 16861.
Suporta conversão entre unidades de ModelSpace (Metros/mm) e PaperSpace (Milímetros).
"""

from typing import Dict, List, Tuple, Optional
import math

# Escalas normalizadas recomendadas pela NBR 16861
STANDARD_SCALES = [
    # Detalhes e ampliações
    1, 2, 5, 10, 20, 25, 50, 75,
    # Plantas de edificações, projetos hidráulicos e saneamento
    100, 125, 200, 250, 500, 750, 800, 1000,
    # Projetos urbanos, loteamentos e cartografia cadastral
    1250, 1500, 2000, 2500, 5000, 10000
]

def calculate_drawing_size_on_sheet(
    dx_meters: float,
    dy_meters: float,
    scale_denominator: float
) -> Tuple[float, float]:
    """
    Calcula o tamanho que um desenho no ModelSpace (em metros) ocupará na folha (em milímetros).

    1 metro = 1000 milímetros.
    Tamanho na folha (mm) = (Tamanho no Model em metros * 1000) / Denominador da Escala
    """
    width_mm = (dx_meters * 1000.0) / scale_denominator
    height_mm = (dy_meters * 1000.0) / scale_denominator
    return width_mm, height_mm

def get_viewport_custom_scale(scale_denominator: float, model_unit_in_mm: float = 1000.0) -> float:
    """
    Retorna o valor de 'custom_scale' da Viewport do AutoCAD.
    No AutoCAD, quando o ModelSpace está em metros (1m = 1000mm) e o PaperSpace em mm:
    CustomScale = 1000.0 / Escala.
    No Zoom XP: (1000/Escala)xp
    """
    return model_unit_in_mm / scale_denominator

def estimate_scale_from_viewport(custom_scale: float, model_unit_in_mm: float = 1000.0) -> float:
    """
    A partir do custom_scale de uma Viewport, deduz o denominador da escala.
    """
    if custom_scale <= 0:
        return 0.0
    return model_unit_in_mm / custom_scale

def find_best_standard_scale(
    dx_meters: float,
    dy_meters: float,
    available_width_mm: float,
    available_height_mm: float,
    safety_margin: float = 0.10,
    allow_rotation: bool = True
) -> Dict:
    """
    Calcula a menor escala padronizada (maior nível de detalhe) que enquadra o desenho
    dentro da área útil da folha, respeitando uma margem de respiro de segurança.

    safety_margin: 0.10 significa que 10% do espaço é deixado livre para respiro/cotas/textos.
    """
    eff_w = available_width_mm * (1.0 - safety_margin)
    eff_h = available_height_mm * (1.0 - safety_margin)

    best_scale = None
    rotated = False

    # Testa orientação normal e rotacionada 90 graus
    for scale in STANDARD_SCALES:
        w_mm, h_mm = calculate_drawing_size_on_sheet(dx_meters, dy_meters, scale)

        # Teste normal
        if w_mm <= eff_w and h_mm <= eff_h:
            best_scale = scale
            rotated = False
            break

        # Teste rotacionado (se permitido)
        if allow_rotation and (h_mm <= eff_w and w_mm <= eff_h):
            best_scale = scale
            rotated = True
            break

    if best_scale is None:
        # Se ultrapassar até 1:10000, calcula o valor exato analítico
        scale_x = (dx_meters * 1000.0) / eff_w
        scale_y = (dy_meters * 1000.0) / eff_h
        exact_scale = max(scale_x, scale_y)
        # Arredonda para a próxima centena ou milhar
        best_scale = int(math.ceil(exact_scale / 500.0) * 500)

    w_final, h_final = calculate_drawing_size_on_sheet(dx_meters, dy_meters, best_scale)
    if rotated:
        w_final, h_final = h_final, w_final

    occupancy_x = (w_final / available_width_mm) * 100.0
    occupancy_y = (h_final / available_height_mm) * 100.0

    return {
        "scale_denominator": best_scale,
        "scale_str": f"1:{best_scale}",
        "custom_scale": get_viewport_custom_scale(best_scale),
        "zoom_xp_str": f"{get_viewport_custom_scale(best_scale):.4f}xp",
        "drawing_width_mm": round(w_final, 1),
        "drawing_height_mm": round(h_final, 1),
        "available_width_mm": round(available_width_mm, 1),
        "available_height_mm": round(available_height_mm, 1),
        "occupancy_x_percent": round(occupancy_x, 1),
        "occupancy_y_percent": round(occupancy_y, 1),
        "rotated_90deg": rotated
    }

def format_scale_table(evaluations: List[Dict]) -> str:
    """
    Formata tabela Markdown com opções de escalas testadas.
    """
    lines = [
        "| Formato | Escala Indicada | Tamanho no Papel (mm) | Área Útil (mm) | Ocupação | Rotacionar? |",
        "|---|---|---|---|---|---|"
    ]
    for ev in evaluations:
        lines.append(
            f"| **{ev['sheet_name']}** | {ev['scale_str']} | "
            f"{ev['drawing_width_mm']} x {ev['drawing_height_mm']} mm | "
            f"{ev['available_width_mm']} x {ev['available_height_mm']} mm | "
            f"{max(ev['occupancy_x_percent'], ev['occupancy_y_percent']):.1f}% | "
            f"{'Sim (90°)' if ev['rotated_90deg'] else 'Não'} |"
        )
    return "\n".join(lines)
