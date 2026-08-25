# MJ-PROJETOQGIS — Pipeline de Exportação QGIS para DXF (AutoCAD)

Pipeline automatizado para exportação de recortes georreferenciados de projetos de saneamento e cadastro técnico do QGIS diretamente para o padrão CAD (DXF/DWG).

---

## 📌 Principais Recursos Implementados

1. **Separação Automática de Redes por Diâmetro Nominal (`cat_dnom`):**
   - Criação automática dos layers individuais: `Rede_DN50`, `Rede_DN75`, `Rede_DN100`, `Rede_DN150`, `Rede_DN200`, `Rede_DN250`, `Rede_DN300`.
   - Cada layer recebe sua cor ACI e TrueColor 24-bit original do estilo do QGIS.

2. **Propriedades 100% ByLayer (Cor, Espessura e Tipo de Linha):**
   - Removidos todos os overrides de cor (`62`, `420`) e espessura (`370`) das entidades individuais.
   - Qualquer alteração na cor ou peso do layer no AutoCAD reflete instantaneamente em todos os objetos.

3. **Remoção Completa de `Global Width` das Polilinhas:**
   - Expurgo dos pares DXF `40`, `41` e `43` das polilinhas `LWPOLYLINE`, eliminando larguras geométricas fixas e restaurando o controle fino de espessura via Lineweight do Layer.

4. **Preservação de Hachuras Sólidas (`HATCH SOLID`):**
   - Exportação integral dos polígonos de Quadras, Lotes e Meio-Fio com preenchimento sólido no layer correspondente (81 hachuras sólidas no recorte).

5. **Ordenação de Desenho (Draw Order) Otimizada:**
   - **Fundo:** Hachuras (`HATCH`) de Quadras, Lotes e Meio-Fio.
   - **Camada Média 1:** Polilinhas de contorno (`LWPOLYLINE`) e Curvas de Nível (Mestra e Intermediária clippadas na extensão).
   - **Camada Média 2:** Redes de Água desmembradas por diâmetro.
   - **Topo:** Elementos pontuais/nós (`Nos`) e textos (`MTEXT` / `TEXT`).

6. **Exclusão de Camadas Desnecessárias:**
   - Camadas de cota/amarração (`v_edit_dimensions`) desativadas do fluxo de exportação.

---

## 🚀 Como Usar (Reaproveitamento para Novos Recortes)

### 1. Ajustar o Recorte / Extents
Edite o arquivo [export_params_ordered.json](export_params_ordered.json) alterando o campo `EXTENT` para as coordenadas desejadas no formato `"Xmin,Xmax,Ymin,Ymax"`:

```json
"EXTENT": "720234.495,720472.095,8192330.572,8192498.572"
```

### 2. Executar a Exportação do QGIS (Headless)
Execute via terminal:
```bash
/Applications/QGIS-final-4_2_0.app/Contents/MacOS/qgis_process run native:dxfexport - < /Volumes/Mac_Dados/Repos/MJ-PROJETOQGIS/export_params_ordered.json
```

### 3. Executar o Pós-Processador DXF
Rode o script de limpeza e conformidade ByLayer:
```bash
python3 /Volumes/Mac_Dados/Repos/MJ-PROJETOQGIS/generate_clean_dxf.py
```

O arquivo final limpo e pronto para uso no AutoCAD será gerado em:
`/Volumes/Mac_Dados/Downloads/sicob_COMPLETO_FINAL.dxf`
