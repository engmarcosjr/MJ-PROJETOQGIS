import re

dxf_file = "/Volumes/Mac_Dados/Downloads/sicob_AGENTE_FINAL.dxf"

with open(dxf_file, 'r', encoding='CP1252', errors='replace') as f:
    lines = f.read().splitlines()

layers_encontrados = set()
hatches_count = 0
bylayer_violations = 0
texts = []
in_entities = False

for i in range(len(lines)):
    if lines[i] == "  0" and lines[i+1] == "SECTION":
        if lines[i+3] == "ENTITIES":
            in_entities = True
    elif lines[i] == "  0" and lines[i+1] == "ENDSEC" and in_entities:
        in_entities = False
        
    # Pega os layers da tabela
    if lines[i] == "  0" and lines[i+1] == "LAYER":
        layers_encontrados.add(lines[i+3]) # o valor logo após o AcDbSymbolTableRecord -> nome
        # Na vdd o codigo 2 é o nome do layer
        
    if in_entities:
        if lines[i] == "  8":
            layers_encontrados.add(lines[i+1])
        if lines[i] == "100" and lines[i+1] == "AcDbHatch":
            hatches_count += 1
        if lines[i] in [' 62', '370', '420']:
            bylayer_violations += 1
        # Pega textos
        if lines[i] == "  1":
            texts.append(lines[i+1])

print(f"--- RELATÓRIO DO DXF ---")
print(f"Total de Hachuras (AcDbHatch) geradas: {hatches_count}")
print(f"Violações ByLayer (cores/espessuras hardcoded nos elementos): {bylayer_violations}")
print(f"Alguns Layers encontrados: {sorted(list(layers_encontrados))[:10]}")
print(f"Amostra de Textos (MTEXT): {texts[:5]}")
