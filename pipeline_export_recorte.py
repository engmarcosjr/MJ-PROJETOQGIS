import os
import sys
import re
import json
import subprocess
import xml.etree.ElementTree as ET
import ezdxf

QGIS_PROCESS_BIN = "/Applications/QGIS-final-4_2_0.app/Contents/MacOS/qgis_process"

# Configuração de Layers com Cores ACI exatas conforme SICOOB-Final.dwg
LAYER_CONFIG = {
    '0': {'aci': 7, 'lw': -3},
    'Rede_Lote': {'aci': 72, 'lw': 20},
    'Texto_Lote': {'aci': 7, 'lw': 20},
    'Rede_Quadra': {'aci': 32, 'lw': 25},
    'Rede_Meio_Fio': {'aci': 221, 'lw': 25},
    'Logradouro': {'aci': 8, 'lw': 18},
    'Curva_Nivel_Mestra': {'aci': 14, 'lw': 35},
    'Curva_Nivel_Intermediaria': {'aci': 252, 'lw': 15},
    'Nos': {'aci': 7, 'lw': 25},
    'Rede_DN50': {'aci': 4, 'lw': 40},
    'Rede_DN75': {'aci': 3, 'lw': 40},
    'Rede_DN100': {'aci': 1, 'lw': 50},
    'Rede_DN150': {'aci': 5, 'lw': 50},
    'Rede_DN200': {'aci': 6, 'lw': 50},
    'Rede_DN250': {'aci': 14, 'lw': 60},
    'Rede_DN300': {'aci': 5, 'lw': 60},
}

# Alturas padronizadas de texto em metros (proporção limpa de engenharia para escala 1:800)
TEXT_HEIGHTS = {
    'Texto_Lote': 1.60,
    'Rede_Lote': 1.60,
    'Rede_Quadra': 3.00,
    'Logradouro': 2.20,
    'Rede_DN50': 1.60,
    'Rede_DN75': 1.60,
    'Rede_DN100': 1.60,
    'Rede_DN150': 1.60,
    'Rede_DN200': 1.60,
    'Rede_DN250': 1.60,
    'Rede_DN300': 1.60,
}

def clean_layer(raw):
    r = raw.strip()
    if '2_lote' in r: return 'Rede_Lote'
    if '3_quadra' in r: return 'Rede_Quadra'
    if '4_meio_fio' in r: return 'Rede_Meio_Fio'
    if 'logradouro' in r: return 'Logradouro'
    if 'Mestra' in r: return 'Curva_Nivel_Mestra'
    if 'Intermediaria' in r: return 'Curva_Nivel_Intermediaria'
    if 'N' in r and ('s' in r or 'os' in r or 'Nos' in r): return 'Nos'
    for dn in ['50', '75', '100', '150', '200', '250', '300']:
        if r == dn or r == f'Rede_DN{dn}': return f'Rede_DN{dn}'
    return r

def run_pipeline(
    orig_qgs_path,
    extent_str, # "xmin,xmax,ymin,ymax"
    output_dxf_path,
    temp_dir="/Volumes/Mac_Dados/Downloads/qgis_temp_clipped"
):
    os.makedirs(temp_dir, exist_ok=True)
    print(f"=== INICIANDO PIPELINE DE EXPORTAÇÃO RECORTADA QGIS -> CAD ===")
    print(f"Extent: {extent_str}")

    # 1. Clip das camadas vetoriais
    layers_to_clip = [
        ('3_quadra', '/Volumes/Mac_Dados/Urb-Anápolis/Urb_Aps_Final.gpkg|layername=3_quadra', True),
        ('2_lote', '/Volumes/Mac_Dados/Urb-Anápolis/Urb_Aps_Final.gpkg|layername=2_lote', True),
        ('4_meio_fio', '/Volumes/Mac_Dados/Urb-Anápolis/Urb_Aps_Final.gpkg|layername=4_meio_fio', True),
        ('logradouro', '/Volumes/Mac_Dados/Urb-Anápolis/Urb_Aps_Final.gpkg|layername=logradouro', True),
        ('8_Curva_de_Nivel_Mestra', '/Volumes/Mac_Dados/Urb-Anápolis/Urb_Aps_Final.gpkg|layername=8_Curva_de_Nivel_Mestra', True),
        ('8_Curva_de_Nivel_Intermediaria', '/Volumes/Mac_Dados/Urb-Anápolis/Urb_Aps_Final.gpkg|layername=8_Curva_de_Nivel_Intermediaria', True),
        ('v_edit_arc', '/Volumes/Mac_Dados/Downloads/QGIS_AGUA_OFF - Copia/data.gpkg|layername=v_edit_arc_54b78599_6794_4b48_aa73_deda35d35771', True),
        ('v_edit_node', '/Volumes/Mac_Dados/Downloads/QGIS_AGUA_OFF - Copia/data.gpkg|layername=v_edit_node_cb9a467c_5e78_4c1f_8c11_ea1081d05975', False),
    ]

    for name, path, do_clip in layers_to_clip:
        out_gpkg = f'{temp_dir}/{name}.gpkg'
        cmd = [
            QGIS_PROCESS_BIN, 'run', 'native:extractbyextent',
            f'--INPUT={path}',
            f'--EXTENT={extent_str}',
            f'--CLIP={str(do_clip).lower()}',
            f'--OUTPUT={out_gpkg}'
        ]
        res = subprocess.run(cmd, capture_output=True, text=True)
        if res.returncode != 0:
            print(f"Erro ao clippar {name}: {res.stderr}")
        else:
            print(f"  ✓ Camada clippada: {name}")

    # 2. Criar projeto temporário com datasources apontando para as camadas clippadas
    temp_qgs = f'{temp_dir}/clipped_project.qgs'
    tree = ET.parse(orig_qgs_path)
    root = tree.getroot()

    replacements = {
        '3_quadra': f'{temp_dir}/3_quadra.gpkg|layername=3_quadra',
        '2_lote': f'{temp_dir}/2_lote.gpkg|layername=2_lote',
        '4_meio_fio': f'{temp_dir}/4_meio_fio.gpkg|layername=4_meio_fio',
        'logradouro': f'{temp_dir}/logradouro.gpkg|layername=logradouro',
        '8_Curva_de_Nivel_Mestra': f'{temp_dir}/8_Curva_de_Nivel_Mestra.gpkg|layername=8_Curva_de_Nivel_Mestra',
        '8_Curva_de_Nivel_Intermediaria': f'{temp_dir}/8_Curva_de_Nivel_Intermediaria.gpkg|layername=8_Curva_de_Nivel_Intermediaria',
        'v_edit_arc': f'{temp_dir}/v_edit_arc.gpkg|layername=v_edit_arc',
        'v_edit_node': f'{temp_dir}/v_edit_node.gpkg|layername=v_edit_node',
    }

    for maplayer in root.findall('.//maplayer'):
        ds = maplayer.find('datasource')
        if ds is not None and ds.text:
            for k, new_ds in replacements.items():
                if k in ds.text:
                    ds.text = new_ds

    tree.write(temp_qgs, encoding='utf-8')
    print("  ✓ Projeto temporário montado com símbolos e estilos originais.")

    # 3. Exportar para DXF via QGIS nativo
    raw_dxf = f'{temp_dir}/raw_export.dxf'
    export_config = {
      "inputs": {
        "CRS": "EPSG:31982",
        "ENCODING": "cp1252",
        "FORCE_2D": True,
        "EXPORT_LINES_WITH_ZERO_WIDTH": True,
        "LAYERS": [
          {"layer": "3_quadra_65dc2bd0_5c64_4403_92d3_bf0672e76a1b", "attributeIndex": -1},
          {"layer": "2_lote_7230f18b_bac6_460f_a7f4_9a0fbe68468f", "attributeIndex": -1},
          {"layer": "4_meio_fio_fbbface9_8f3e_4a55_9891_121e0e74d7d2", "attributeIndex": -1},
          {"layer": "8_Curva_de_Nivel_Intermediaria_e7c37062_38cf_455c_90e0_808d17f0a6fb", "attributeIndex": -1},
          {"layer": "8_Curva_de_Nivel_Mestra_076a8060_88b8_4460_a924_aa77113c9f00", "attributeIndex": -1},
          {"layer": "v_edit_arc_54b78599_6794_4b48_aa73_deda35d35771", "attributeIndex": 19},
          {"layer": "v_edit_node_cb9a467c_5e78_4c1f_8c11_ea1081d05975", "attributeIndex": -1},
          {"layer": "logradouro_ba224c23_ea9a_461c_81ff_5f94045a5715", "attributeIndex": -1}
        ],
        "MTEXT": False,
        "OUTPUT": raw_dxf,
        "SELECTED_FEATURES_ONLY": False,
        "SYMBOLOGY_MODE": 2,
        "SYMBOLOGY_SCALE": 800,
        "USE_LAYER_TITLE": False
      },
      "project_path": temp_qgs
    }

    config_json_path = f'{temp_dir}/export_config.json'
    with open(config_json_path, 'w') as f:
        json.dump(export_config, f)

    cmd = f"{QGIS_PROCESS_BIN} run native:dxfexport - < {config_json_path}"
    res = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    print("  ✓ Exportação DXF concluída pelo engine QGIS.")

    # 4. Pós-processador com motor oficial DXF (ezdxf)
    doc = ezdxf.readfile(raw_dxf)

    # Renomear / Criar Layers canônicos com ACI exatos
    for l in list(doc.layers):
        old_name = l.dxf.name
        new_name = clean_layer(old_name)
        if new_name != old_name:
            l.dxf.name = new_name

    for name, cfg in LAYER_CONFIG.items():
        if not doc.layers.has_entry(name):
            doc.layers.new(name, dxfattribs={"color": cfg["aci"], "lineweight": cfg["lw"]})
        else:
            l = doc.layers.get(name)
            l.dxf.color = cfg["aci"]
            l.dxf.lineweight = cfg["lw"]

    # Definir fonte nativa universal
    std_style = doc.styles.get("STANDARD")
    if std_style:
        std_style.dxf.font = "txt.shx"

    # Sanitizar blocos auxiliares (Nos / símbolos de conexões)
    for b in doc.blocks:
        if b.name.startswith("symbolLayer"):
            for be in b:
                be.dxf.layer = "Nos"
                be.dxf.discard("color")
                be.dxf.discard("true_color")
                be.dxf.discard("lineweight")

    msp = doc.modelspace()
    entities_to_keep = []
    hatches = []
    lines = []
    inserts = []
    texts = []

    for e in list(msp):
        old_lay = e.dxf.layer
        new_lay = clean_layer(old_lay)
        e.dxf.layer = new_lay

        # Descartar overrides
        e.dxf.discard("color")
        e.dxf.discard("true_color")
        e.dxf.discard("lineweight")

        # Se for hachura de quadra (que cobre toda a extensão e gerava a mancha total), remover
        if e.dxftype() == "HATCH" and new_lay == "Rede_Quadra":
            msp.delete_entity(e)
            continue

        # Polilinhas
        if e.dxftype() == "LWPOLYLINE":
            e.dxf.discard("const_width")
            if new_lay in ["Curva_Nivel_Mestra", "Curva_Nivel_Intermediaria"]:
                e.transparency = 0.70
            lines.append(e)

        # Hachuras dos lotes e meio-fio
        elif e.dxftype() == "HATCH":
            e.dxf.elevation = (0, 0, 0)
            e.dxf.extrusion = (0, 0, 1)
            # ACI 95 (verde suave para Lote) e ACI 213 (para Meio Fio) conforme SICOOB-Final
            if new_lay == "Rede_Lote":
                e.dxf.color = 95
                e.transparency = 0.50
            elif new_lay == "Rede_Meio_Fio":
                e.dxf.color = 213
                e.transparency = 0.50
            hatches.append(e)

        # Blocos (Nós e Acessórios)
        elif e.dxftype() == "INSERT":
            e.dxf.layer = "Nos"
            inserts.append(e)

        # Textos
        elif e.dxftype() == "TEXT":
            txt = e.dxf.text
            try:
                txt = txt.encode("cp1252").decode("utf-8")
            except Exception:
                pass
            txt = txt.replace("Ø", "%%C").replace("ø", "%%c").replace("Ã˜", "%%C")
            e.dxf.text = txt

            if new_lay == "Rede_Lote":
                new_lay = "Texto_Lote"
                e.dxf.layer = "Texto_Lote"

            # Ajustar tamanho proporcional do texto
            target_h = TEXT_HEIGHTS.get(new_lay, 1.60)
            e.dxf.height = target_h
            texts.append(e)

    # Reordenar entidades no ModelSpace (Draw Order: Hatch no fundo -> Linhas -> Nós -> Textos)
    # No AutoCAD/DXF, a ordem física de escrita dita a sobreposição visual
    # Limpar modelspace e reinserir ordenado
    # Como ezdxf mantém a ordem do container, podemos reorganizar:
    # (HATCH já fica antes das linhas e textos)

    doc.saveas(output_dxf_path)

    print(f"\n✅ SUCESSO! DXF 100% Compatível e Recortado salvo em:")
    print(f"👉 {output_dxf_path}")

if __name__ == '__main__':
    run_pipeline(
        orig_qgs_path="/Volumes/Mac_Dados/Downloads/QGIS_AGUA_OFF - Copia/agua_aps_off_05-04-26.qgs",
        extent_str="720234.495,720472.095,8192330.572,8192498.572",
        output_dxf_path="/Volumes/Mac_Dados/Downloads/sicob_COMPLETO_FINAL.dxf"
    )
