import re
dxf_file = "/Volumes/Mac_Dados/Downloads/sicob_headless_test3.dxf" # O exportado cru
new_dxf = "/Volumes/Mac_Dados/Downloads/sicob_AGENTE_LIMPO.dxf"

with open(dxf_file, 'r', encoding='CP1252', errors='replace') as f:
    texto = f.read().splitlines()

codigo_pronto = []
linha_idx = 0
in_entities = False
last_layer = ""

while linha_idx < len(texto):
    if linha_idx + 1 >= len(texto): break
    k = texto[linha_idx].strip()
    v = texto[linha_idx+1]
    pular = False
    
    # Corrige nome zoado de layer (problemas ANSI)
    if k == '  8':
        if "Urb_Aps_Final" in v:
            v_fix = v.replace("â€”", "-").replace("?", "-").strip()
            v = v_fix
            
    # Purificador ByLayer
    if k == '  0' and v == 'SECTION':
        if texto[linha_idx+3] == "ENTITIES": in_entities = True
    elif k == '  0' and v == 'ENDSEC':
        in_entities = False
        
    if in_entities and k in [' 62', '62', '420', ' 420', '370', ' 370']:
        pular = True
        linha_idx += 2
        
    if not pular:
        codigo_pronto.append(texto[linha_idx])
        codigo_pronto.append(v)
        linha_idx += 2

with open(new_dxf, 'w', encoding='CP1252') as f:
    f.write("\n".join(codigo_pronto) + "\n")
print("Feito.")
