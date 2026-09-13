dxf_file = "/Volumes/Mac_Dados/Downloads/sicob_AGENTE_FINAL.dxf"

with open(dxf_file, 'r', encoding='CP1252', errors='replace') as f:
    lines = f.read().splitlines()

real_layers = set()
for i in range(len(lines)):
    if lines[i] == "  8":
        real_layers.add(lines[i+1])

print(f"LAYERS REAIS NO DESENHO:")
for l in sorted(list(real_layers)):
    print(l)
