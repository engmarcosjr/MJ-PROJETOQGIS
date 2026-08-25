# MJ-PROJETOQGIS — Pipeline de Exportação QGIS para DXF (AutoCAD)

Pipeline automatizado para recorte e exportação georreferenciada de projetos de saneamento e cadastro técnico municipal do QGIS diretamente para o padrão Autodesk DXF (AutoCAD 2000+ / AC1015).

---

## 📌 Recursos e Conformidade Técnica

1. **Recorte Geométrico Rigoroso (Vector Clipping):**
   - Execução prévia de `native:extractbyextent` com `--CLIP=true` em todas as camadas vetoriais (poligonais e lineares).
   - As curvas de nível (Mestra e Intermediária) e perímetros de quadra/lote são cortados rigorosamente na fronteira da Bounding Box informada, evitando linhas extrapolando o desenho.

2. **Separação Automática de Redes por Diâmetro Nominal (`cat_dnom`):**
   - Criação automática dos layers individuais: `Rede_DN50`, `Rede_DN75`, `Rede_DN100`, `Rede_DN150`, `Rede_DN200`, `Rede_DN250`, `Rede_DN300`.
   - Cada layer recebe sua cor ACI e espessura de pena de projeto padronizada.

3. **Propriedades 100% ByLayer (Cor, Espessura e Tipo de Linha):**
   - Removidos todos os overrides de cor (`62`, `420`) e espessura (`370`) das entidades individuais no `ENTITIES`.
   - Qualquer alteração na cor ou peso do layer no AutoCAD reflete instantaneamente em todos os objetos.

4. **Remoção Completa de `Global Width` das Polilinhas:**
   - Expurgo dos pares DXF `40`, `41` e `43` das polilinhas `LWPOLYLINE`, eliminando larguras geométricas fixas e restaurando o controle fino de espessura via Lineweight do Layer.

5. **Preservação de Hachuras Sólidas (`HATCH SOLID`):**
   - Exportação integral dos polígonos de Quadras, Lotes e Meio-Fio com preenchimento sólido no layer correspondente (132 hachuras sólidas no recorte de teste).

6. **Integridade Estrutural Autodesk DXF (Sem travamento / "Press ENTER"):**
   - O DXF é gerado através do motor nativo do QGIS (`native:dxfexport`) sobre as camadas clippadas, preservando tabelas vitais de `BLOCK_RECORD`, `BLOCKS`, `OBJECTS` e dicionários de layout, garantindo abertura instantânea em qualquer versão do AutoCAD (incluindo AutoCAD 2025).

---

## 🚀 Como Executar o Pipeline Completo

O script [pipeline_export_recorte.py](pipeline_export_recorte.py) unifica todas as etapas (Clipping -> Projeto Temporário -> Exportação DXF Nativa -> Pós-processamento ByLayer).

### Execução Direta:

```bash
python3 /Volumes/Mac_Dados/Repos/MJ-PROJETOQGIS/pipeline_export_recorte.py
```

### Parâmetros Padrão:

- **Bounding Box (EPSG:31982 - SIRGAS 2000 / UTM Zone 22S):**
  - Xmin: `720234.495`
  - Ymin: `8192330.572`
  - Xmax: `720472.095`
  - Ymax: `8192498.572`
- **Escala de Simbologia:** `1:800`
- **Arquivo de Saída:** `/Volumes/Mac_Dados/Downloads/sicob_COMPLETO_FINAL.dxf`

---

## 📐 Tabela de Layers e Penas Configuradas

| Layer | Cor AutoCAD (ACI) | Espessura (Lineweight) | Descrição |
|---|---|---|---|
| `Rede_Lote` | 72 (Verde Claro) | 0.20 mm | Lotes cadastrais e hachuras |
| `Rede_Quadra` | 32 (Marrom/Laranja) | 0.30 mm | Perímetros e hachuras de quadra |
| `Rede_Meio_Fio` | 221 (Cinza/Azulado) | 0.25 mm | Meio-fio e calçadas |
| `Logradouro` | 8 (Cinza Escuro) | 0.18 mm | Textos de vias e eixos |
| `Curva_Nivel_Mestra` | 30 (Laranja) | 0.35 mm | Curvas mestras (cotas principais) |
| `Curva_Nivel_Intermediaria` | 64 (Verde Escuro) | 0.15 mm | Curvas intermediárias |
| `Nos` | 7 (Branco/Preto) | 0.25 mm | Nós e conexões da rede |
| `Rede_DN50` | 4 (Ciano) | 0.40 mm | Rede de água DN 50 |
| `Rede_DN75` | 3 (Verde) | 0.40 mm | Rede de água DN 75 |
| `Rede_DN100` | 1 (Vermelho) | 0.50 mm | Rede de água DN 100 |
| `Rede_DN150` | 5 (Azul) | 0.50 mm | Rede de água DN 150 |
| `Rede_DN200` | 6 (Magenta) | 0.50 mm | Rede de água DN 200 |
| `Rede_DN250` | 14 (Laranja Vivo) | 0.60 mm | Rede de água DN 250 |
| `Rede_DN300` | 5 (Azul) | 0.60 mm | Rede de água DN 300 |
