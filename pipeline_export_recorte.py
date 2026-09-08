import os
import sys
import re
import math
import json
import subprocess
import xml.etree.ElementTree as ET
import ezdxf

QGIS_PROCESS_BIN = "/Applications/QGIS-final-4_2_0.app/Contents/MacOS/qgis_process"
ODA_FILE_CONVERTER_BIN = "/Applications/ODAFileConverter.app/Contents/MacOS/ODAFileConverter"

# Tabela de Layers e Cores ACI
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

    # Alinhar a versão do DXF com o gabarito que não trava no AutoCAD Mac
    # (QGIS exporta em AC1018/AutoCAD 2004; o editor MTEXT in-place do
    # AutoCAD Mac espera a estrutura mais recente do formato).
    doc.dxfversion = "AC1032"  # AutoCAD 2018 (R2018)

    # Criar Layers canônicos com ACI exatos.
    # IMPORTANTE: NÃO renomear as layers originais do QGIS via
    # `l.dxf.name = novo_nome` — isso só altera o atributo do objeto, mas
    # não atualiza o índice interno (nome -> entrada) da tabela LAYER do
    # ezdxf. A entrada antiga continua "indexada" pelo nome velho, então o
    # `has_entry(novo_nome)` do laço seguinte retorna False e uma SEGUNDA
    # layer com o mesmo nome (porém com a cor certa) acaba sendo criada —
    # resultando em DUAS entradas LAYER com o nome duplicado no arquivo.
    # O ODA File Converter expôs isso: "Duplicate record name ... Ignored".
    # Uma tabela de camadas com nomes duplicados é estrutura DXF ambígua:
    # as entidades acabam resolvendo ora para uma, ora para outra cópia —
    # o que explica tanto as cores erradas (a cópia "fantasma" mantém a
    # cor padrão vermelha do QGIS) quanto contribui para a instabilidade
    # do arquivo no AutoCAD. A correção é criar as layers canônicas do
    # zero (exceto a "0", que é especial e sempre existe) e nunca renomear
    # as originais — as entidades já são todas realocadas para o nome
    # canônico via `e.dxf.layer = new_lay` mais abaixo, então as layers
    # originais do QGIS ficam órfãs e são removidas ao final.
    original_layer_names = {l.dxf.name for l in doc.layers}

    for name, cfg in LAYER_CONFIG.items():
        if name == "0":
            l = doc.layers.get("0")
            l.dxf.color = cfg["aci"]
            l.dxf.lineweight = cfg["lw"]
        elif not doc.layers.has_entry(name):
            doc.layers.new(name, dxfattribs={"color": cfg["aci"], "lineweight": cfg["lw"]})
        else:
            l = doc.layers.get(name)
            l.dxf.color = cfg["aci"]
            l.dxf.lineweight = cfg["lw"]

    # Fonte TrueType dos MTEXT: NÃO usar uma STYLE table dedicada (nem
    # sobrescrever STANDARD). O gabarito funcional (SICOOB-Final.dxf) nunca
    # cria um estilo próprio para as fontes TrueType que usa — em todas as
    # 70 entidades MTEXT ele mantém STANDARD intocado (romans.shx, sem
    # atributo 'style' no MTEXT) e troca a fonte por entidade através do
    # código de formatação inline \f do próprio MTEXT, exatamente como o
    # AutoCAD grava quando você escolhe uma fonte no editor. Reproduzimos a
    # mesma técnica abaixo.
    MTEXT_FONT = "Arial"

    # Sanitizar blocos auxiliares
    for b in doc.blocks:
        if b.name.startswith("symbolLayer"):
            for be in b:
                be.dxf.layer = "Nos"
                be.dxf.discard("color")
                be.dxf.discard("true_color")
                be.dxf.discard("lineweight")

    msp = doc.modelspace()
    text_entities = []

    for e in list(msp):
        old_lay = e.dxf.layer
        new_lay = clean_layer(old_lay)
        e.dxf.layer = new_lay

        # Descartar overrides
        e.dxf.discard("color")
        e.dxf.discard("true_color")
        e.dxf.discard("lineweight")

        # Excluir hachura sobreposta de quadra
        if e.dxftype() == "HATCH" and new_lay == "Rede_Quadra":
            msp.delete_entity(e)
            continue

        # Polilinhas
        if e.dxftype() == "LWPOLYLINE":
            e.dxf.discard("const_width")
            if new_lay in ["Curva_Nivel_Mestra", "Curva_Nivel_Intermediaria"]:
                e.transparency = 0.70

        # Hachuras
        elif e.dxftype() == "HATCH":
            e.dxf.elevation = (0, 0, 0)
            e.dxf.extrusion = (0, 0, 1)
            if new_lay == "Rede_Lote":
                e.dxf.color = 95
                e.transparency = 0.50
            elif new_lay == "Rede_Meio_Fio":
                e.dxf.color = 213
                e.transparency = 0.50

        # Blocos (Nós)
        elif e.dxftype() == "INSERT":
            e.dxf.layer = "Nos"

        # Coletar e converter TEXT para MTEXT robusto e editável
        elif e.dxftype() in ["TEXT", "MTEXT"]:
            text_entities.append(e)

    # Converter todos os textos para MTEXT nativo com vetor de rotação canônico
    for te in text_entities:
        old_lay = te.dxf.layer
        new_lay = "Texto_Lote" if old_lay in ["Rede_Lote", "Texto_Lote"] else clean_layer(old_lay)
        raw_val = te.dxf.text if te.dxftype() == "TEXT" else te.text
        pos = te.dxf.insert
        rot_deg = getattr(te.dxf, 'rotation', 0.0) or 0.0

        try:
            raw_val = raw_val.encode("cp1252").decode("utf-8")
        except Exception:
            pass
        raw_val = raw_val.replace("Ø", "%%C").replace("ø", "%%c").replace("Ã˜", "%%C")

        # Espaço não separável (\~), igual ao gabarito, evita quebra de
        # linha indevida dentro do MTEXT.
        mtext_content = f"\\f{MTEXT_FONT}|i0|b0;" + raw_val.replace(" ", "\\~")

        # Limpar do modelspace a entidade legada
        msp.delete_entity(te)

        # Criar MTEXT com a mesma estrutura de grupos DXF do gabarito que não
        # trava (SICOOB-Final.dxf): todos os seus 70 MTEXT trazem width,
        # defined_height, flow_direction e line_spacing explícitos, usam o
        # vetor text_direction em vez do ângulo de rotação (50), NUNCA
        # referenciam uma STYLE dedicada (ficam em STANDARD) e trocam a
        # fonte via código inline \f dentro do próprio texto.
        target_h = TEXT_HEIGHTS.get(new_lay, 1.60)
        mtext = msp.add_mtext(mtext_content, dxfattribs={
            'layer': new_lay,
            'char_height': target_h,
            'attachment_point': 5, # Middle Center (alinhamento ideal para edição)
            'width': 0.0,
            'defined_height': 0.0,
            'flow_direction': 5,       # ByStyle, igual ao gabarito
            'line_spacing_style': 1,   # AtLeast, igual ao gabarito
            'line_spacing_factor': 1.0,
        })
        mtext.dxf.insert = pos
        if rot_deg != 0.0:
            rad = math.radians(rot_deg)
            mtext.dxf.text_direction = (math.cos(rad), math.sin(rad), 0.0)

    # Remover as layers originais do QGIS: todas as entidades já foram
    # realocadas para os nomes canônicos acima, então essas entradas ficam
    # órfãs. Removê-las evita nomes duplicados na tabela LAYER (ver nota
    # acima) e limpa o arquivo de lixo do processo de exportação do QGIS.
    canonical_names = set(LAYER_CONFIG.keys()) | {"Defpoints"}
    for old_name in list(original_layer_names):
        if old_name not in canonical_names and doc.layers.has_entry(old_name):
            try:
                doc.layers.remove(old_name)
            except Exception as ex:
                print(f"  ⚠️ Não foi possível remover layer órfã '{old_name}': {ex}")

    doc.saveas(output_dxf_path)

    print(f"\n✅ SUCESSO! DXF 100% Compatível e Recortado salvo em:")
    print(f"👉 {output_dxf_path}")

    # 5. Converter para DWG nativo via ODA File Converter (motor oficial da
    # Open Design Alliance, mesma base usada pelo AutoCAD). Um DXF, mesmo
    # estruturalmente válido, ainda é reinterpretado pelo importador do
    # AutoCAD ao ser aberto; um DWG nativo evita essa etapa de conversão e
    # tende a eliminar problemas de edição in-place que só aparecem em
    # arquivos de origem DXF.
    if os.path.exists(ODA_FILE_CONVERTER_BIN):
        oda_in = f'{temp_dir}/oda_in'
        oda_out = f'{temp_dir}/oda_out'
        os.makedirs(oda_in, exist_ok=True)
        os.makedirs(oda_out, exist_ok=True)
        import shutil
        oda_input_dxf = f'{oda_in}/{os.path.basename(output_dxf_path)}'
        shutil.copy(output_dxf_path, oda_input_dxf)

        oda_cmd = [
            ODA_FILE_CONVERTER_BIN,
            oda_in, oda_out,
            "ACAD2018", "DWG", "0", "1"
        ]
        subprocess.run(oda_cmd, capture_output=True, text=True)

        output_dwg_path = os.path.splitext(output_dxf_path)[0] + ".dwg"
        generated_dwg = f'{oda_out}/{os.path.splitext(os.path.basename(output_dxf_path))[0]}.dwg'
        if os.path.exists(generated_dwg):
            shutil.copy(generated_dwg, output_dwg_path)
            print(f"\n✅ DWG nativo gerado via ODA File Converter:")
            print(f"👉 {output_dwg_path}")
        else:
            print("\n⚠️ ODA File Converter não gerou o DWG esperado.")

if __name__ == '__main__':
    run_pipeline(
        orig_qgs_path="/Volumes/Mac_Dados/Downloads/QGIS_AGUA_OFF - Copia/agua_aps_off_05-04-26.qgs",
        extent_str="720234.495,720472.095,8192330.572,8192498.572",
        output_dxf_path="/Volumes/Mac_Dados/Downloads/sicob_COMPLETO_FINAL.dxf"
    )
