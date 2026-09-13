#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
CLI e Utilitário Automatizado de Projetista CAD (cad-drafter).
Inspeciona DXF, calcula escalas padronizadas ABNT, gera pranchas completas com carimbo e viewports.
"""

import os
import sys
import argparse
import math
from typing import Tuple, Dict, List, Optional

# Garantir import dos módulos locais mesmo se executado fora da pasta scripts
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
if SCRIPT_DIR not in sys.path:
    sys.path.insert(0, SCRIPT_DIR)

import ezdxf
from ezdxf import bbox

# Import local modules
import scale_calc
import sheet_templates

def get_modelspace_bounding_box(doc) -> Tuple[float, float, float, float, float, float]:
    """
    Calcula a extensão precisa de todas as entidades do ModelSpace de forma tolerante a falhas.
    Retorna: (min_x, min_y, max_x, max_y, delta_x, delta_y)
    """
    msp = doc.modelspace()
    min_x, min_y = float("inf"), float("inf")
    max_x, max_y = float("-inf"), float("-inf")
    has_points = False

    for e in msp:
        # Tenta extrair bbox via ezdxf bbox
        box_done = False
        try:
            b = bbox.extents([e])
            if b.has_data:
                ex_min, ex_max = b.extmin, b.extmax
                min_x = min(min_x, ex_min[0])
                min_y = min(min_y, ex_min[1])
                max_x = max(max_x, ex_max[0])
                max_y = max(max_y, ex_max[1])
                has_points = True
                box_done = True
        except Exception:
            pass

        if not box_done:
            # Fallback seguro para entidades que falham no cálculo analítico (ex: blocos malformados)
            if hasattr(e.dxf, "insert"):
                pt = e.dxf.insert
                min_x = min(min_x, pt[0])
                min_y = min(min_y, pt[1])
                max_x = max(max_x, pt[0])
                max_y = max(max_y, pt[1])
                has_points = True
            elif hasattr(e.dxf, "start") and hasattr(e.dxf, "end"):
                s, end_p = e.dxf.start, e.dxf.end
                min_x = min(min_x, s[0], end_p[0])
                min_y = min(min_y, s[1], end_p[1])
                max_x = max(max_x, s[0], end_p[0])
                max_y = max(max_y, s[1], end_p[1])
                has_points = True

    if not has_points:
        raise ValueError("ModelSpace vazio ou sem entidades mensuráveis.")

    delta_x = max_x - min_x
    delta_y = max_y - min_y

    return min_x, min_y, max_x, max_y, delta_x, delta_y

def inspect_dxf(dxf_path: str) -> None:
    """
    Audita o arquivo DXF: versão, unidades, bounding box, camadas, layouts existentes e viewports.
    """
    if not os.path.exists(dxf_path):
        print(f"Erro: Arquivo não encontrado: {dxf_path}")
        sys.exit(1)

    doc = ezdxf.readfile(dxf_path)
    print(f"=== AUDITORIA DE PROJETO CAD: {os.path.basename(dxf_path)} ===")
    print(f"Versão DXF: {doc.dxfversion} ({doc.acad_release})")

    # ModelSpace Bounding Box
    try:
        min_x, min_y, max_x, max_y, dx, dy = get_modelspace_bounding_box(doc)
        print(f"\n📐 EXTENSÃO DO MODELSPACE (Metros):")
        print(f"  X: {min_x:.3f} até {max_x:.3f} (ΔX = {dx:.3f} m)")
        print(f"  Y: {min_y:.3f} até {max_y:.3f} (ΔY = {dy:.3f} m)")
        print(f"  Centro: X = {((min_x + max_x)/2):.3f}, Y = {((min_y + max_y)/2):.3f}")
    except Exception as e:
        print(f"\n⚠️ Não foi possível calcular Bounding Box: {e}")
        dx, dy = 0.0, 0.0

    # Camadas
    print(f"\n📁 CAMADAS ({len(doc.layers)} no total):")
    for l in sorted(doc.layers, key=lambda x: x.dxf.name):
        color = l.dxf.color
        lw = l.dxf.lineweight
        print(f"  - {l.dxf.name: <25} Cor ACI: {color: <4} Lineweight: {lw} (1/100 mm)")

    # Layouts (PaperSpace)
    print(f"\n📋 LAYOUTS / PRANCHAS:")
    for layout in doc.layouts:
        if layout.name.lower() == "model":
            continue
        vps = layout.viewports()
        # vps[0] costuma ser a viewport do próprio layout (geral)
        real_vps = [v for v in vps if v.dxf.id > 1]
        print(f"  • Layout: '{layout.name}' ({len(real_vps)} viewport(s) de desenho)")
        for idx, vp in enumerate(real_vps, start=1):
            view_h = getattr(vp.dxf, 'view_height', 0.0)
            center_x, center_y, _ = getattr(vp.dxf, 'center', (0,0,0))
            w = getattr(vp.dxf, 'width', 0.0)
            h = getattr(vp.dxf, 'height', 0.0)
            # Deduz a escala a partir da relação altura do papel (mm) e altura do model (m)
            # scale = (view_h * 1000) / h
            scale_est = (view_h * 1000.0) / h if h > 0 and view_h > 0 else 0.0
            scale_str = f"1:{int(round(scale_est))}" if scale_est > 0 else "Indefinida"
            custom_scale = (h / (view_h * 1000.0)) * 1000.0 if view_h > 0 else 0.0
            print(f"    - Viewport #{idx}: Centro=({center_x:.1f}, {center_y:.1f}) mm | Tamanho=({w:.1f} x {h:.1f}) mm | Escala={scale_str} (CustomScale={custom_scale:.5f})")

def suggest_scales(dxf_path: str, sheet_filter: Optional[str] = None) -> None:
    """
    Calcula as melhores escalas para enquadrar o desenho em todas as folhas ABNT.
    """
    doc = ezdxf.readfile(dxf_path)
    min_x, min_y, max_x, max_y, dx, dy = get_modelspace_bounding_box(doc)

    print(f"=== ANÁLISE DE ENQUADRAMENTO E ESCALAS (ABNT NBR 16861) ===")
    print(f"Dimensões do desenho no Model: ΔX = {dx:.2f} m, ΔY = {dy:.2f} m\n")

    sheets = [sheet_filter.upper()] if sheet_filter else ["A0", "A1", "A2", "A3", "A4"]
    evaluations = []

    for s_name in sheets:
        if s_name not in sheet_templates.SHEET_SIZES:
            continue
        geom = sheet_templates.get_sheet_geometry(s_name)
        eval_res = scale_calc.find_best_standard_scale(
            dx_meters=dx,
            dy_meters=dy,
            available_width_mm=geom["drawing_area_width"],
            available_height_mm=geom["drawing_area_height"],
            safety_margin=0.08
        )
        eval_res["sheet_name"] = s_name
        evaluations.append(eval_res)

    print(scale_calc.format_scale_table(evaluations))
    print("\n💡 Dica: O cálculo já desconta a margem ABNT de encadernação (25mm) e a reserva para o carimbo.")

def create_sheet(
    dxf_path: str,
    output_path: str,
    sheet_name: str,
    scale_val: Optional[int] = None,
    layout_name: Optional[str] = None,
    title: str = "PROJETO EXECUTIVO",
    client: str = "CLIENTE",
    engineer: str = "MARCOS JR - ENG. CIVIL",
    crea: str = "CREA/CAU: REGISTRO",
    sheet_num: str = "01/01",
    date_str: str = "SET/2026"
) -> None:
    """
    Cria uma nova prancha ABNT no arquivo DXF com margens, carimbo e viewport configurada.
    """
    doc = ezdxf.readfile(dxf_path)
    min_x, min_y, max_x, max_y, dx, dy = get_modelspace_bounding_box(doc)
    center_model_x = (min_x + max_x) / 2.0
    center_model_y = (min_y + max_y) / 2.0

    geom = sheet_templates.get_sheet_geometry(sheet_name)

    # Determinar escala se não informada
    if scale_val is None:
        best = scale_calc.find_best_standard_scale(
            dx_meters=dx,
            dy_meters=dy,
            available_width_mm=geom["drawing_area_width"],
            available_height_mm=geom["drawing_area_height"]
        )
        scale_val = best["scale_denominator"]

    scale_str = f"1:{scale_val}"
    custom_scale = scale_calc.get_viewport_custom_scale(scale_val)

    if not layout_name:
        layout_name = f"PRANCHA_{sheet_name}_{scale_str.replace(':', '_')}"

    # Criar ou substituir Layout
    if layout_name in doc.layouts:
        doc.layouts.delete(layout_name)
    layout = doc.layouts.new(layout_name)

    # Desenhar Folha, Margens e Carimbo
    sheet_templates.draw_sheet_border(layout, geom, doc)
    sheet_templates.draw_title_block(
        layout,
        geom,
        {
            "title": title,
            "client": client,
            "engineer": engineer,
            "crea": crea,
            "scale": scale_str,
            "sheet_num": sheet_num,
            "date": date_str
        }
    )

    # Configuração da Viewport principal
    # A área útil para a viewport:
    # No eixo X: vai de margin_min_x até margin_max_x (ou ajustada ao carimbo)
    # No eixo Y: fica acima do carimbo ou dividida
    mx0, my0, mx1, my1 = geom["margin_box"]
    tb_x0, tb_y0, tb_x1, tb_y1 = geom["title_block_box"]

    # Largura e altura da Viewport
    vp_margin = 8.0 # mm de folga das bordas da margem
    vp_w = (mx1 - mx0) - (2 * vp_margin)
    vp_h = (my1 - my0) - (2 * vp_margin)

    # Se a viewport colidir com o carimbo no canto inferior direito, deixamos a área livre:
    # Para pranchas A1 a A0, uma viewport centralizada com respiro comporta bem.
    vp_center_x = (mx0 + mx1) / 2.0
    vp_center_y = (my0 + my1 + (tb_y1 - my0) * 0.3) / 2.0
    # Reduzimos um pouco a altura para não sobrepor o selo
    vp_h = (my1 - tb_y1) - (2 * vp_margin)
    vp_center_y = tb_y1 + (vp_h / 2.0) + vp_margin

    # Em ezdxf / DXF nativo:
    # A escala da viewport é definida pela proporção entre a altura física na folha (height, em mm)
    # e a altura visível do modelo (view_height, em unidades de model = metros).
    # Como 1m = 1000mm, na escala 1:E:
    # view_height = (vp_h * scale_val) / 1000.0
    view_h_model = (vp_h * scale_val) / 1000.0

    # Adicionar Viewport no PaperSpace
    vp = layout.add_viewport(
        center=(vp_center_x, vp_center_y),
        size=(vp_w, vp_h),
        view_center_point=(center_model_x, center_model_y),
        view_height=view_h_model,
        dxfattribs={
            "layer": "Defpoints",
            "status": 1
        }
    )

    # Salvar
    doc.saveas(output_path)
    print(f"✅ Prancha '{layout_name}' criada com sucesso!")
    print(f"  Formato: {sheet_name} ({geom['sheet_width']} x {geom['sheet_height']} mm)")
    print(f"  Escala configurada: {scale_str} (CustomScale = {custom_scale:.5f})")
    print(f"  Viewport centralizada em Model: ({center_model_x:.2f}, {center_model_y:.2f})")
    print(f"  Arquivo gerado: {output_path}")

def add_detail_viewport(
    dxf_path: str,
    output_path: str,
    layout_name: str,
    center_model_x: float,
    center_model_y: float,
    scale_val: int,
    vp_center_sheet_x: float,
    vp_center_sheet_y: float,
    vp_width_mm: float,
    vp_height_mm: float,
    detail_title: str = "DETALHE"
) -> None:
    """
    Adiciona uma viewport secundária de detalhe em uma prancha existente.
    """
    doc = ezdxf.readfile(dxf_path)
    if layout_name not in doc.layouts:
        raise ValueError(f"Layout '{layout_name}' não encontrado no DXF.")

    layout = doc.layouts.get(layout_name)

    view_h_model = (vp_height_mm * scale_val) / 1000.0

    vp = layout.add_viewport(
        center=(vp_center_sheet_x, vp_center_sheet_y),
        size=(vp_width_mm, vp_height_mm),
        view_center_point=(center_model_x, center_model_y),
        view_height=view_h_model,
        dxfattribs={
            "layer": "Defpoints",
            "status": 1
        }
    )

    # Adicionar título e indicação de escala abaixo da viewport de detalhe
    title_pos = (vp_center_sheet_x - (vp_width_mm / 2.0), vp_center_sheet_y - (vp_height_mm / 2.0) - 3.0)
    title_content = f"\\fArial|i0|b1;{detail_title}\\~-\\~ESC.\\~1:{scale_val}"
    layout.add_mtext(
        title_content,
        dxfattribs={
            "layer": "_PRANCHA_TEXTO",
            "char_height": 2.5,
            "insert": title_pos,
            "attachment_point": 1,
            "width": 0.0,
            "flow_direction": 5,
            "line_spacing_style": 1
        }
    )

    doc.saveas(output_path)
    print(f"✅ Detalhe '{detail_title}' adicionado ao layout '{layout_name}'!")
    print(f"  Escala: 1:{scale_val} | Foco Model: ({center_model_x:.2f}, {center_model_y:.2f})")
    print(f"  Arquivo salvo em: {output_path}")

def main():
    parser = argparse.ArgumentParser(description="CAD Drafter - Projetista de CAD Automatizado")
    subparsers = parser.add_subparsers(dest="command", required=True)

    # Subcomando: inspect
    p_inspect = subparsers.add_parser("inspect", help="Audita o arquivo DXF, camadas, extensões e viewports")
    p_inspect.add_argument("dxf", help="Caminho do arquivo DXF")

    # Subcomando: suggest-scale
    p_scale = subparsers.add_parser("suggest-scale", help="Sugere escalas normatizadas ABNT para cada formato de folha")
    p_scale.add_argument("dxf", help="Caminho do arquivo DXF")
    p_scale.add_argument("--sheet", choices=["A0", "A1", "A2", "A3", "A4"], help="Filtrar por formato específico")

    # Subcomando: make-sheet
    p_sheet = subparsers.add_parser("make-sheet", help="Cria uma prancha completa com margem, carimbo e viewport")
    p_sheet.add_argument("dxf", help="Caminho do arquivo DXF de entrada")
    p_sheet.add_argument("--output", "-o", required=True, help="Caminho do arquivo DXF de saída")
    p_sheet.add_argument("--sheet", choices=["A0", "A1", "A2", "A3", "A4"], default="A1", help="Formato da folha ABNT")
    p_sheet.add_argument("--scale", type=int, help="Denominador da escala (ex: 500 para 1:500, 1000 para 1:1000)")
    p_sheet.add_argument("--layout", help="Nome do layout a ser criado")
    p_sheet.add_argument("--title", default="PROJETO EXECUTIVO", help="Título do projeto")
    p_sheet.add_argument("--client", default="CLIENTE", help="Nome do cliente ou proprietário")
    p_sheet.add_argument("--engineer", default="MARCOS JR - ENG. CIVIL", help="Nome do Responsável Técnico")
    p_sheet.add_argument("--crea", default="CREA/CAU: REGISTRO", help="Registro profissional")
    p_sheet.add_argument("--sheet-num", default="01/01", help="Número da prancha (ex: 01/03)")
    p_sheet.add_argument("--date", default="SET/2026", help="Data da prancha")

    # Subcomando: add-detail
    p_detail = subparsers.add_parser("add-detail", help="Adiciona uma viewport secundária com detalhe ampliado")
    p_detail.add_argument("dxf", help="Caminho do arquivo DXF de entrada")
    p_detail.add_argument("--output", "-o", required=True, help="Caminho do arquivo DXF de saída")
    p_detail.add_argument("--layout", required=True, help="Nome do layout existente")
    p_detail.add_argument("--model-center", required=True, help="Coordenadas do centro no ModelSpace (ex: 100.5,75.2)")
    p_detail.add_argument("--scale", type=int, required=True, help="Denominador da escala do detalhe (ex: 20 para 1:20, 50 para 1:50)")
    p_detail.add_argument("--sheet-center", required=True, help="Coordenadas do centro da viewport na folha em mm (ex: 200,150)")
    p_detail.add_argument("--size", required=True, help="Tamanho da viewport na folha em mm: LARGURA,ALTURA (ex: 120,80)")
    p_detail.add_argument("--title", default="DETALHE", help="Título do detalhe")

    args = parser.parse_args()

    if args.command == "inspect":
        inspect_dxf(args.dxf)
    elif args.command == "suggest-scale":
        suggest_scales(args.dxf, args.sheet)
    elif args.command == "make-sheet":
        create_sheet(
            dxf_path=args.dxf,
            output_path=args.output,
            sheet_name=args.sheet,
            scale_val=args.scale,
            layout_name=args.layout,
            title=args.title,
            client=args.client,
            engineer=args.engineer,
            crea=args.crea,
            sheet_num=args.sheet_num,
            date_str=args.date
        )
    elif args.command == "add-detail":
        mc_x, mc_y = [float(v.strip()) for v in args.model_center.split(",")]
        sc_x, sc_y = [float(v.strip()) for v in args.sheet_center.split(",")]
        w_mm, h_mm = [float(v.strip()) for v in args.size.split(",")]
        add_detail_viewport(
            dxf_path=args.dxf,
            output_path=args.output,
            layout_name=args.layout,
            center_model_x=mc_x,
            center_model_y=mc_y,
            scale_val=args.scale,
            vp_center_sheet_x=sc_x,
            vp_center_sheet_y=sc_y,
            vp_width_mm=w_mm,
            vp_height_mm=h_mm,
            detail_title=args.title
        )

if __name__ == "__main__":
    main()
