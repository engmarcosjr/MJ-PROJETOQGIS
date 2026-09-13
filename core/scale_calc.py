# -*- coding: utf-8 -*-
"""Cálculos de proporções, escalas e conversões milímetros-papel para metros-desenho."""


def paper_mm_to_model_m(height_mm: float, scale_denom: float) -> float:
    """Converte a altura do texto no papel (em mm) para altura no Model do AutoCAD (em metros).

    Fórmula ABNT / CAD:
    altura_metros = altura_papel_mm * (denominador_escala / 1000.0)

    Exemplo:
      height_mm = 2.0, scale_denom = 800  -> 2.0 * 0.8  = 1.60 m
      height_mm = 2.0, scale_denom = 1000 -> 2.0 * 1.0  = 2.00 m
      height_mm = 3.75, scale_denom = 800 -> 3.75 * 0.8 = 3.00 m
    """
    if height_mm is None or height_mm <= 0:
        return 1.60  # fallback seguro
    return round((height_mm * (scale_denom / 1000.0)), 3)


def get_text_heights_for_scale(layer_config: dict, scale_denom: float) -> dict:
    """Gera o dicionário de alturas de texto em metros para cada camada na escala informada.

    Retorna:
      dict: { 'Nome_Camada': altura_em_metros, ... }
    """
    heights_in_meters = {}
    for layer_name, cfg in layer_config.items():
        mm = cfg.get('text_height_mm')
        if mm is not None and mm > 0:
            heights_in_meters[layer_name] = paper_mm_to_model_m(mm, scale_denom)
        else:
            # Fallback padrão de 2.0 mm se não houver definição explícita
            heights_in_meters[layer_name] = paper_mm_to_model_m(2.0, scale_denom)

    return heights_in_meters
