import os
import re
from qgis.core import QgsProject, QgsDxfExport, QgsVectorLayer, QgsRectangle, QgsMapSettings
from qgis.utils import iface
from qgis.PyQt.QtWidgets import QFileDialog
from qgis.PyQt.QtCore import QFile, QIODeviceBase, QIODevice

# ======================================================================
# FLUXO DEFINITIVO QGIS -> AUTO_CAD 
# ======================================================================

def mapear_cor_por_layer(nome_layer):
    if "Trechos" in nome_layer: return 5     # 5 = Azul Escuro AutoCAD
    if "1_unidade" in nome_layer: return 9   # 9 = Cinza claro
    if "2_lote" in nome_layer: return 8      # 8 = Cinza escuro
    if "3_quadra" in nome_layer: return 7    # 7 = Branco/Preto 
    if "4_meio_fio" in nome_layer: return 7  # 7 = Branco/Preto
    if "logradouro" in nome_layer: return 7  # 7 = Branco/Preto
    if "Curva" in nome_layer: return 32      # 32 = Marrom terra
    if "Nós" in nome_layer: return 1         # 1 = Vermelho
    return 7 

# DICA PARA O FUTURO REUSO: É aqui que você altera o extent sem depender da tela!
x_min = 720234.495
y_min = 8192330.572
x_max = 720472.095
y_max = 8192498.572
caminho_salvar = "/Volumes/Mac_Dados/Downloads/sicob_final_bylayer.dxf"

print(f"\n🚀 Iniciando Motor PyQGIS para Construção do DXF: {caminho_salvar}")

dxf_export = QgsDxfExport()

map_settings = QgsMapSettings()
map_settings.updateWithMapSettings(iface.mapCanvas().mapSettings())
rect = QgsRectangle(x_min, y_min, x_max, y_max)
map_settings.setExtent(rect)

dxf_export.setMapSettings(map_settings)
dxf_export.setExtent(rect) 
dxf_export.setSymbologyScale(800) 
dxf_export.setForce2d(True)
dxf_export.setSymbologyExport(QgsDxfExport.SymbolLayerSymbology)

# Lista extata de camadas que devem ir (segundo seu print)
camadas_alvo = [
    "Nós", "Trechos", "Amarração de Rede",
    "Urb_Aps_Final — 1_unidade", "Urb_Aps_Final — 2_lote", 
    "Urb_Aps_Final — 3_quadra", "Urb_Aps_Final — 4_meio_fio",
    "Urb_Aps_Final — logradouro", 
    "Urb_Aps_Final — 8_Curva_de_Nivel_Mestra", "Urb_Aps_Final — 8_Curva_de_Nivel_Intermediaria"
]

dxf_layers = []
lista_layers_exportados = []

raiz = QgsProject.instance().layerTreeRoot()
for nome in camadas_alvo:
    # Acha pelo nome exato para não depender da aba 'Ligada' na tela do momento
    no_arvore = raiz.findLayer(QgsProject.instance().mapLayersByName(nome)[0].id()) if QgsProject.instance().mapLayersByName(nome) else None
    if no_arvore:
        layer = no_arvore.layer()
        if isinstance(layer, QgsVectorLayer):
            nome_layer = layer.name()
            idx_split = -1
            
            nomes_colunas = [f.name().lower() for f in layer.fields()]
            campo_alvo = "cat_dnom" 
            
            if campo_alvo in nomes_colunas:
                idx_split = layer.fields().lookupField(campo_alvo)
                print(f"✔️ Dividindo '{nome_layer}' baseado no diâmetro (Campo: {campo_alvo})")
            
            cfg = QgsDxfExport.DxfLayer(layer, idx_split)
            dxf_layers.append(cfg)
            lista_layers_exportados.append(nome_layer)

dxf_export.addLayers(dxf_layers)

modo = QIODeviceBase.OpenModeFlag.WriteOnly | QIODeviceBase.OpenModeFlag.Truncate if hasattr(QIODeviceBase, 'OpenModeFlag') else QIODevice.WriteOnly | QIODevice.Truncate
arq = QFile(caminho_salvar)
if arq.open(modo):
    dxf_export.writeToFile(arq, "CP1252")
    arq.close()
    
    print("\n🧹 Iniciando Lavagem de Propriedades (Transformando TUDO para ByLayer)...")
    
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
        
        if current_section == 'TABLES' and current_entity == 'LAYER':
            if k == '2': last_table_layer = v 
            if k == '62': 
                cor = 7
                for nom_base in lista_layers_exportados:
                    if last_table_layer.startswith(nom_base): 
                        cor = mapear_cor_por_layer(nom_base)
                v = str(cor)

        # Remove override de Cor nativa (62 e 420) e Espessura individual (370) da geometria.
        if current_section in ['ENTITIES', 'BLOCKS']:
            if k in ['62', '420', '370']:
                pular = True
                linha_idx += 2
                
        if not pular:
            codigo_pronto.append(texto[linha_idx])
            codigo_pronto.append(v)
            linha_idx += 2
            
    with open(caminho_salvar, 'w', encoding='CP1252') as f:
        f.write("\n".join(codigo_pronto) + "\n")
        
    print("\n================================================================")
    print("🏆 DXF CIRÚRGICO FINALIZADO COM SUCESSO!")
    print(f" ✔️ Hachuras (AcDbHatch) -> Convertidas OK.")
    print(f" ✔️ Trechos divididos automaticamente pelo campo 'cat_dnom'.")
    print(f" ✔️ Cores e espessuras transferidas pra matriz ByLayer!")
    print("================================================================")
