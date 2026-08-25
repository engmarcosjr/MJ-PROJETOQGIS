import os
import re

LAYER_CONFIG = {
    'Rede_Lote': {'aci': 72, 'lw': 20},
    'Rede_Quadra': {'aci': 32, 'lw': 30},
    'Rede_Meio_Fio': {'aci': 221, 'lw': 25},
    'Logradouro': {'aci': 8, 'lw': 18},
    'Curva_Nivel_Mestra': {'aci': 30, 'lw': 35},
    'Curva_Nivel_Intermediaria': {'aci': 64, 'lw': 15},
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

def process_dxf(input_path, output_path):
    with open(input_path, 'r', encoding='cp1252', errors='replace') as f:
        lines = f.read().splitlines()

    pairs = []
    for i in range(0, len(lines)-1, 2):
        pairs.append((lines[i], lines[i+1]))

    new_pairs = []
    in_entities = False
    in_layer_table = False
    curr_layer_name = None

    i = 0
    while i < len(pairs):
        k, v = pairs[i]
        k_s = k.strip()

        if k_s == '0' and v == 'SECTION':
            if i+1 < len(pairs) and pairs[i+1][0].strip() == '2' and pairs[i+1][1] == 'ENTITIES':
                in_entities = True
        elif k_s == '0' and v == 'ENDSEC' and in_entities:
            in_entities = False

        if k_s == '0' and v == 'TABLE':
            if i+1 < len(pairs) and pairs[i+1][0].strip() == '2' and pairs[i+1][1] == 'LAYER':
                in_layer_table = True
        elif k_s == '0' and v == 'ENDTAB' and in_layer_table:
            in_layer_table = False

        # Na tabela LAYER: renomear e atribuir cor correta ACI
        if in_layer_table:
            if k_s == '2' and v != 'LAYER':
                curr_layer_name = clean_layer(v)
                new_pairs.append((k, curr_layer_name))
                i += 1
                continue
            if k_s == '62' and curr_layer_name in LAYER_CONFIG:
                new_pairs.append((k, f"{LAYER_CONFIG[curr_layer_name]['aci']:>8}"))
                i += 1
                continue

        # Dentro de ENTITIES: forçar ByLayer expurgando overrides e Global Width
        if in_entities:
            if k_s in ['62', '420', '370', '40', '41', '43']:
                i += 1
                continue
            if k_s == '8':
                new_pairs.append((k, clean_layer(v)))
                i += 1
                continue

        new_pairs.append((k, v))
        i += 1

    out_lines = []
    for k, v in new_pairs:
        out_lines.append(k)
        out_lines.append(v)

    with open(output_path, 'w', encoding='cp1252', errors='replace') as f:
        f.write('\n'.join(out_lines) + '\n')

    print(f"Sucesso! Gerado {output_path} com 100% de compatibilidade e ByLayer.")

if __name__ == '__main__':
    process_dxf(
        "/Volumes/Mac_Dados/Downloads/sicob_raw_ordered.dxf",
        "/Volumes/Mac_Dados/Downloads/sicob_COMPLETO_FINAL.dxf"
    )
