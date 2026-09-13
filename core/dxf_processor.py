# -*- coding: utf-8 -*-
"""Pós-processamento oficial do arquivo DXF gerado pelo QGIS para padrão AutoCAD 2018 (AC1032)."""

import os
import sys
import re
import math
import subprocess
import shutil

# Tentar importar ezdxf (incluindo caminhos comuns no macOS caso o QGIS tenha sys.path restrito)
try:
    import ezdxf
except ImportError:
    # Adicionar paths do usuário se necessário
    for extra_path in [
        f"/Users/{os.environ.get('USER', 'macbookmj')}/Library/Python/3.14/lib/python/site-packages",
        f"/Users/{os.environ.get('USER', 'macbookmj')}/Library/Python/3.13/lib/python/site-packages",
        f"/Users/{os.environ.get('USER', 'macbookmj')}/Library/Python/3.12/lib/python/site-packages",
        "/Library/Frameworks/Python.framework/Versions/3.12/lib/python3.12/site-packages",
    ]:
        if os.path.exists(extra_path) and extra_path not in sys.path:
            sys.path.append(extra_path)
    try:
        import ezdxf
    except ImportError:
        ezdxf = None


def is_ezdxf_available():
    return ezdxf is not None


def clean_layer_name(raw_name: str, name_rules=None) -> str:
    """Higieniza o nome da camada original do QGIS para o nome canônico do CAD."""
    r = raw_name.strip()

    # Se regras customizadas forem fornecidas
    if name_rules:
        for rule in name_rules:
            pat = rule.get('pattern', '')
            tgt = rule.get('target', '')
            if rule.get('regex', False):
                if re.search(pat, r):
                    return tgt
            else:
                if pat in r:
                    return tgt

    # Regras padrão de saneamento / cadastro urbano
    if '2_lote' in r or 'lote' in r.lower():
        return 'Rede_Lote'
    if '3_quadra' in r or 'quadra' in r.lower():
        return 'Rede_Quadra'
    if 'meio_fio' in r.lower():
        return 'Rede_Meio_Fio'
    if 'logradouro' in r.lower() or 'rua' in r.lower() or 'via' in r.lower():
        return 'Logradouro'
    if 'mestra' in r.lower():
        return 'Curva_Nivel_Mestra'
    if 'intermediaria' in r.lower():
        return 'Curva_Nivel_Intermediaria'
    if 'v_edit_node' in r or re.fullmatch(r'N.{0,3}s', r, re.IGNORECASE):
        return 'Nos'

    # Redes por diâmetro
    for dn in ['50', '75', '100', '150', '200', '250', '300']:
        if r == dn or r == f'Rede_DN{dn}':
            return f'Rede_DN{dn}'

    return r


def post_process_dxf(
    dxf_path: str,
    output_dxf_path: str,
    layer_config: dict,
    text_heights_in_m: dict,
    name_rules=None,
    raster_info: dict = None,
    progress_callback=None
):
    """Aplica higienização ByLayer, MTEXT nativo com Arial inline, cores ACI, padronização AC1032 e imagem raster."""
    if not is_ezdxf_available():
        raise RuntimeError(
            "Biblioteca 'ezdxf' não encontrada no ambiente Python do QGIS.\n"
            "Instale-a via terminal executando: pip install ezdxf"
        )

    if progress_callback:
        progress_callback(10, "Lendo DXF gerado pelo QGIS...")

    doc = ezdxf.readfile(dxf_path)
    # AutoCAD 2018 (AC1032) para total compatibilidade com AutoCAD Mac e Windows
    doc.dxfversion = "AC1032"

    original_layer_names = {l.dxf.name for l in doc.layers}

    # Criar camada dedicada para imagem de satélite se fornecida
    if raster_info:
        if not doc.layers.has_entry("Imagem_Satelite"):
            doc.layers.new("Imagem_Satelite", dxfattribs={"color": 7, "lineweight": -3})

    # Criar camadas canônicas com as cores ACI e Lineweight configurados
    for name, cfg in layer_config.items():
        aci = cfg.get('aci', 7)
        lw = cfg.get('lw', -3)
        if name == "0":
            l = doc.layers.get("0")
            l.dxf.color = aci
            l.dxf.lineweight = lw
        elif not doc.layers.has_entry(name):
            doc.layers.new(name, dxfattribs={"color": aci, "lineweight": lw})
        else:
            l = doc.layers.get(name)
            l.dxf.color = aci
            l.dxf.lineweight = lw

    # Sanitizar blocos auxiliares (nós da rede)
    for b in doc.blocks:
        if b.name.startswith("symbolLayer"):
            for be in b:
                be.dxf.layer = "Nos"
                be.dxf.discard("color")
                be.dxf.discard("true_color")
                be.dxf.discard("lineweight")

    msp = doc.modelspace()
    text_entities = []

    if progress_callback:
        progress_callback(30, "Processando entidades e hachuras...")

    for e in list(msp):
        old_lay = e.dxf.layer
        new_lay = clean_layer_name(old_lay, name_rules)
        e.dxf.layer = new_lay

        # 100% ByLayer: descartar overrides individuais
        e.dxf.discard("color")
        e.dxf.discard("true_color")
        e.dxf.discard("lineweight")

        # Excluir hachura sobreposta de quadra
        if e.dxftype() == "HATCH" and new_lay == "Rede_Quadra":
            msp.delete_entity(e)
            continue

        # Polilinhas: remover const_width e ajustar transparência de curvas de nível
        if e.dxftype() == "LWPOLYLINE":
            e.dxf.discard("const_width")
            if new_lay in ["Curva_Nivel_Mestra", "Curva_Nivel_Intermediaria"]:
                e.transparency = 0.70

        # Hachuras sólidas
        elif e.dxftype() == "HATCH":
            e.dxf.elevation = (0, 0, 0)
            e.dxf.extrusion = (0, 0, 1)
            if new_lay == "Rede_Lote":
                e.dxf.color = 95
                e.transparency = 0.50
            elif new_lay == "Rede_Meio_Fio":
                e.dxf.color = 213
                e.transparency = 0.50

        # Nós / Acessórios
        elif e.dxftype() == "INSERT":
            e.dxf.layer = "Nos"

        # Coletar textos para reconstrução MTEXT
        elif e.dxftype() in ["TEXT", "MTEXT"]:
            text_entities.append(e)

    if progress_callback:
        progress_callback(60, "Formatando textos em MTEXT nativo proporcional...")

    # Reconstrução MTEXT com fonte Arial e altura proporcional à escala
    MTEXT_FONT = "Arial"
    for te in text_entities:
        old_lay = te.dxf.layer
        new_lay = "Texto_Lote" if old_lay in ["Rede_Lote", "Texto_Lote"] else clean_layer_name(old_lay, name_rules)
        raw_val = te.dxf.text if te.dxftype() == "TEXT" else te.text
        pos = te.dxf.insert
        rot_deg = getattr(te.dxf, 'rotation', 0.0) or 0.0

        try:
            raw_val = raw_val.encode("cp1252").decode("utf-8")
        except Exception:
            pass
        raw_val = raw_val.replace("Ø", "%%C").replace("ø", "%%c").replace("Ã˜", "%%C")

        # Espaço não separável (\~) para não quebrar linhas indevidamente
        mtext_content = f"\\f{MTEXT_FONT}|i0|b0;" + raw_val.replace(" ", "\\~")

        # Remover a entidade antiga
        msp.delete_entity(te)

        # Buscar altura em metros calculada para a escala
        target_h = text_heights_in_m.get(new_lay, text_heights_in_m.get('Texto_Lote', 1.60))

        mtext = msp.add_mtext(mtext_content, dxfattribs={
            'layer': new_lay,
            'char_height': target_h,
            'attachment_point': 5,  # Middle Center
            'width': 0.0,
            'defined_height': 0.0,
            'flow_direction': 5,
            'line_spacing_style': 1,
            'line_spacing_factor': 1.0,
        })
        mtext.dxf.insert = pos
        if rot_deg != 0.0:
            rad = math.radians(rot_deg)
            mtext.dxf.text_direction = (math.cos(rad), math.sin(rad), 0.0)

    # Remover layers órfãs para evitar duplicatas e conflitos no AutoCAD
    canonical_names = set(layer_config.keys()) | {"Defpoints", "Imagem_Satelite"}
    for old_name in list(original_layer_names):
        if old_name not in canonical_names and doc.layers.has_entry(old_name):
            try:
                doc.layers.remove(old_name)
            except Exception:
                pass

    # Inserir imagem de satélite georreferenciada no ModelSpace
    if raster_info:
        try:
            image_name = raster_info['image_name']
            w_px, h_px = raster_info['size_in_pixel']
            w_m, h_m = raster_info['size_in_units']
            ins_pt = raster_info['insert_point']

            image_def = doc.add_image_def(filename=image_name, size_in_pixel=(w_px, h_px))
            msp.add_image(
                image_def=image_def,
                insert=ins_pt,
                size_in_units=(w_m, h_m),
                dxfattribs={'layer': 'Imagem_Satelite'}
            )
        except Exception as ex:
            print(f"  ⚠️ Aviso ao inserir imagem raster no DXF: {ex}")

    if progress_callback:
        progress_callback(85, "Gravando DXF final...")

    doc.saveas(output_dxf_path)


def convert_to_dwg_with_oda(dxf_path: str, oda_bin_path: str, output_dir: str = None) -> str:
    """Converte o arquivo DXF para DWG 2018 usando o executável do ODA File Converter."""
    if not os.path.exists(oda_bin_path):
        raise FileNotFoundError(f"Executável do ODA File Converter não encontrado em: {oda_bin_path}")

    dxf_dir = os.path.dirname(dxf_path)
    dxf_name = os.path.basename(dxf_path)
    stem = os.path.splitext(dxf_name)[0]

    target_dir = output_dir or dxf_dir
    temp_in = os.path.join(target_dir, "_oda_tmp_in")
    temp_out = os.path.join(target_dir, "_oda_tmp_out")
    os.makedirs(temp_in, exist_ok=True)
    os.makedirs(temp_out, exist_ok=True)

    try:
        shutil.copy(dxf_path, os.path.join(temp_in, dxf_name))

        # ODAFileConverter <input_dir> <output_dir> <version> <type> <recurse> <audit>
        cmd = [
            oda_bin_path,
            temp_in,
            temp_out,
            "ACAD2018",
            "DWG",
            "0",
            "1"
        ]
        res = subprocess.run(cmd, capture_output=True, text=True)
        if res.returncode != 0:
            raise RuntimeError(f"Erro na conversão ODA: {res.stderr}")

        gen_dwg = os.path.join(temp_out, f"{stem}.dwg")
        final_dwg = os.path.join(target_dir, f"{stem}.dwg")

        if os.path.exists(gen_dwg):
            shutil.move(gen_dwg, final_dwg)
            return final_dwg
        else:
            raise FileNotFoundError("O arquivo DWG não foi gerado pelo ODA File Converter.")
    finally:
        shutil.rmtree(temp_in, ignore_errors=True)
        shutil.rmtree(temp_out, ignore_errors=True)
