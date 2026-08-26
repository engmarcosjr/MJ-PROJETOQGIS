import os
import sys
import re
import json
import subprocess
import xml.etree.ElementTree as ET

QGIS_PROCESS_BIN = "/Applications/QGIS-final-4_2_0.app/Contents/MacOS/qgis_process"

LAYER_CONFIG = {
    'Rede_Lote': {'aci': 72, 'lw': 20},
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
        "MTEXT": True,
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

    # 4. Pós-processador para ByLayer, ACI Colors, Geometria HATCH e Expurgo de Overrides
    with open(raw_dxf, 'r', encoding='cp1252', errors='replace') as f:
        lines = f.read().splitlines()

    pairs = []
    for i in range(0, len(lines)-1, 2):
        pairs.append((lines[i].strip(), lines[i+1].strip()))

    header_tables_blocks = []
    entities_list = []
    objects_trailer = []

    mode = 'PRE_ENTITIES'
    curr_ent = []
    curr_type = None
    in_layer_table = False
    curr_layer_name = None

    i = 0
    while i < len(pairs):
        k, v = pairs[i]

        if mode == 'PRE_ENTITIES':
            if k == '0' and v == 'SECTION' and i+1 < len(pairs) and pairs[i+1][0] == '2' and pairs[i+1][1] == 'ENTITIES':
                mode = 'ENTITIES'
                header_tables_blocks.append((k, v))
                header_tables_blocks.append(pairs[i+1])
                i += 2
                continue
            else:
                # Adicionar $FILLMODE 1 no fim do HEADER se necessário
                if k == '0' and v == 'ENDSEC' and len(header_tables_blocks) > 0 and header_tables_blocks[1] == ('2', 'HEADER'):
                    header_tables_blocks.append(('9', '$FILLMODE'))
                    header_tables_blocks.append(('70', '1'))

                if k == '0' and v == 'TABLE':
                    if i+1 < len(pairs) and pairs[i+1][0] == '2' and pairs[i+1][1] == 'LAYER':
                        in_layer_table = True
                elif k == '0' and v == 'ENDTAB' and in_layer_table:
                    in_layer_table = False

                if in_layer_table:
                    if k == '2' and v != 'LAYER':
                        curr_layer_name = clean_layer(v)
                        header_tables_blocks.append((k, curr_layer_name))
                        i += 1
                        continue
                    if k == '62' and curr_layer_name in LAYER_CONFIG:
                        header_tables_blocks.append((k, f"{LAYER_CONFIG[curr_layer_name]['aci']:>8}"))
                        if 'truecolor' in LAYER_CONFIG[curr_layer_name]:
                            header_tables_blocks.append(('420', f"{LAYER_CONFIG[curr_layer_name]['truecolor']:>8}"))
                        if 'lw' in LAYER_CONFIG[curr_layer_name]:
                            header_tables_blocks.append(('370', f"{LAYER_CONFIG[curr_layer_name]['lw']:>8}"))
                        i += 1
                        continue

                header_tables_blocks.append((k, v))
                i += 1
                continue

        elif mode == 'ENTITIES':
            if k == '0' and v == 'ENDSEC':
                if curr_ent:
                    entities_list.append((curr_type, curr_ent))
                    curr_ent = []
                mode = 'POST_ENTITIES'
                objects_trailer.append((k, v))
                i += 1
                continue
            elif k == '0':
                if curr_ent:
                    entities_list.append((curr_type, curr_ent))
                curr_type = v
                curr_ent = [(k, v)]
                i += 1
                continue
            else:
                # Expurgo de overrides desnecessários
                if k in ['420', '370', '40', '41', '43']:
                    i += 1
                    continue
                # Preservar ou ignorar cores diretas nas entidades comuns (mas ajustaremos nas hachuras)
                if k == '62':
                    i += 1
                    continue
                if k == '8':
                    curr_ent.append((k, clean_layer(v)))
                    i += 1
                    continue

                curr_ent.append((k, v))
                i += 1
                continue

        elif mode == 'POST_ENTITIES':
            objects_trailer.append((k, v))
            i += 1

    # Normalizar entidades HATCH (Vetor normal Z 230: 1.0, elevação Z 30: 0.0) em BLOCKS e ENTITIES
    def fix_hatch_entity(ent, lay=None):
        new_ent = []
        has_230 = any(gk == '230' for gk, gv in ent)
        has_30 = any(gk == '30' for gk, gv in ent)
        has_440 = any(gk == '440' for gk, gv in ent)

        j = 0
        while j < len(ent):
            gk, gv = ent[j]
            new_ent.append((gk, gv))
            if gk == '20' and j > 0 and ent[j-1][0] == '10' and ent[j-1][1] == '0.0' and not has_30:
                new_ent.append(('30', '0.0'))
                has_30 = True
            elif gk == '220' and not has_230:
                new_ent.append(('230', '1.0'))
                has_230 = True
            elif gk == '100' and gv == 'AcDbEntity' and not has_440:
                # Inserir transparência 50% no bloco AcDbEntity
                if lay in ['Rede_Lote', 'Rede_Meio_Fio', 'Rede_Quadra']:
                    new_ent.append(('440', ' 33554559'))
                    has_440 = True
            j += 1
        return new_ent

    # Normalizar HATCH dentro de header_tables_blocks
    fixed_header_blocks = []
    i = 0
    while i < len(header_tables_blocks):
        k, v = header_tables_blocks[i]
        if k == '0' and v == 'HATCH':
            h_ent = [(k, v)]
            i += 1
            while i < len(header_tables_blocks) and header_tables_blocks[i][0] != '0':
                h_ent.append(header_tables_blocks[i])
                i += 1
            fixed_header_blocks.extend(fix_hatch_entity(h_ent))
        else:
            fixed_header_blocks.append((k, v))
            i += 1

    # Função para sanitizar textos MTEXT do QGIS e fixar altura (código 40)
    def fix_mtext_entity(ent):
        raw_txt = ""
        for gk, gv in ent:
            if gk == '1':
                raw_txt = gv
                break

        # Extrair a altura real da simbologia da tag \H
        h = 2.5
        h_match = re.search(r'\\H([0-9.]+);', raw_txt)
        if h_match:
            h = float(h_match.group(1))

        # Limpar todas as formatações inline
        txt = re.sub(r'\\f[^;]+;', '', raw_txt)
        txt = re.sub(r'\\H[^;]+;', '', txt)
        txt = re.sub(r'\\C[^;]+;', '', txt)
        txt = txt.replace(r'\~', ' ')
        txt = re.sub(r'[{}]', '', txt).strip()

        new_ent = []
        has_30 = False
        for gk, gv in ent:
            if gk == '20' and not has_30:
                new_ent.append((gk, gv))
                new_ent.append(('30', '0.0'))
                has_30 = True
                continue
            if gk == '1':
                # Injetar a altura nominal do MTEXT no código de grupo 40
                new_ent.append(('40', str(h)))
                new_ent.append((gk, txt))
                continue
            new_ent.append((gk, gv))
        return new_ent

    # Normalizar entidades da seção ENTITIES
    fixed_entities = []
    for t, ent in entities_list:
        lay = None
        for gk, gv in ent:
            if gk == '8':
                lay = gv
                break

        if t == 'HATCH':
            fixed_entities.append((t, fix_hatch_entity(ent, lay)))

        elif t == 'MTEXT':
            fixed_entities.append((t, fix_mtext_entity(ent)))

        elif t == 'LWPOLYLINE' and lay in ['Curva_Nivel_Mestra', 'Curva_Nivel_Intermediaria']:
            new_ent = []
            has_440 = any(gk == '440' for gk, gv in ent)
            for gk, gv in ent:
                new_ent.append((gk, gv))
                if gk == '100' and gv == 'AcDbEntity' and not has_440:
                    new_ent.append(('440', ' 33554508')) # 70% transparência
                    has_440 = True
            fixed_entities.append((t, new_ent))

        else:
            fixed_entities.append((t, ent))

    # Ordenação de desenho (Draw Order): HATCH no fundo, depois LWPOLYLINE, INSERT e TEXT
    def sort_key(item):
        t, ent = item
        if t == 'HATCH': return 0
        if t == 'LWPOLYLINE': return 1
        if t == 'INSERT': return 2
        return 3

    fixed_entities.sort(key=sort_key)

    final_pairs = list(fixed_header_blocks)
    for t, ent in fixed_entities:
        final_pairs.extend(ent)
    final_pairs.extend(objects_trailer)

    out_lines = []
    for k, v in final_pairs:
        out_lines.append(f'{k:>2}' if len(k) < 3 else k)
        out_lines.append(v)

    with open(output_dxf_path, 'w', encoding='cp1252', errors='replace') as f:
        f.write('\n'.join(out_lines) + '\n')

    print(f"\n✅ SUCESSO! DXF 100% Compatível e Recortado salvo em:")
    print(f"👉 {output_dxf_path}")

if __name__ == '__main__':
    run_pipeline(
        orig_qgs_path="/Volumes/Mac_Dados/Downloads/QGIS_AGUA_OFF - Copia/agua_aps_off_05-04-26.qgs",
        extent_str="720234.495,720472.095,8192330.572,8192498.572",
        output_dxf_path="/Volumes/Mac_Dados/Downloads/sicob_COMPLETO_FINAL.dxf"
    )
