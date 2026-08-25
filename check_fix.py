import re

caminho_salvar = "/Volumes/Mac_Dados/Downloads/sicob_headless_test3.dxf"
caminho_limpo = "/Volumes/Mac_Dados/Downloads/sicob_AGENTE_FINAL.dxf"

try:
    with open(caminho_salvar, 'r', encoding='CP1252', errors='replace') as f:
        texto = f.read().splitlines()
        
    codigo_pronto = []
    linha_idx = 0
    current_section = ""
    current_entity = ""
    last_table_layer = ""
    
    while linha_idx < len(texto):
        if linha_idx + 1 >= len(texto): break
        k = texto[linha_idx].strip()
        v = texto[linha_idx+1]
        pular = False
        
        if k == '0' and v == 'SECTION' and linha_idx+3 < len(texto): current_section = texto[linha_idx+3]
        elif k == '0' and v == 'ENDSEC': current_section = ""
        if k == '0': current_entity = v
        
        # Etapa 1: Colorir layer (Hardcoded Test)
        if current_section == 'TABLES' and current_entity == 'LAYER':
            if k == '2': last_table_layer = v 
            if k == '62': 
                cor = 7
                if last_table_layer.startswith("Tre"): cor = 5
                elif last_table_layer.startswith("Urb_Aps"): cor = 8
                v = str(cor)

        # Etapa 2: Clean entity logic
        if current_section in ['ENTITIES', 'BLOCKS']:
            if k in ['62', '420', '370']:
                pular = True
                linha_idx += 2
                
        if not pular:
            codigo_pronto.append(texto[linha_idx])
            codigo_pronto.append(v)
            linha_idx += 2
            
    with open(caminho_limpo, 'w', encoding='CP1252') as f:
        f.write("\n".join(codigo_pronto) + "\n")
    print("DXF CIRÚRGICO criado com sucesso pelo Agente: ", caminho_limpo)
except Exception as e:
    print(e)
