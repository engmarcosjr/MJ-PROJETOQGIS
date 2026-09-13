# MJ-PROJETOQGIS — Extensão QGIS e Pipeline DXF/DWG Pro (AutoCAD)

Extensão oficial e pipeline automatizado para o **QGIS (3.28+ e 4.x / Qt6)** para recorte e exportação georreferenciada de projetos de saneamento e cadastro técnico diretamente para o padrão Autodesk, gerando **DXF (AC1032 / AutoCAD 2018)** e **DWG nativo via ODA File Converter**.

---

## ⚡ Novidade: Plugin Nativo do QGIS (`Exportador DXF / CAD Pro`)

Agora o projeto conta com uma extensão completa para a interface do QGIS com:
1. **Captura Visual de Extensão:**
   - Botão para capturar a extensão exata da tela visível no mapa (`Canvas Extent`).
   - Ferramenta interativa de clique e arrasto para desenhar um retângulo de recorte no mapa (`RubberBand`).
2. **Detecção Automática de Camadas Ativas:**
   - Exporta automaticamente apenas as camadas vetoriais ligadas/visíveis no painel de camadas do QGIS.
3. **Escalas Dinâmicas e Alturas de Texto Proporcionais:**
   - Você escolhe a escala alvo da prancha (1:500, 1:800, 1:1000, 1:2000, etc.).
   - A geometria mantém-se 1:1 e todas as alturas de texto em metros são recalculadas matematicamente a partir da altura técnica no papel (em mm).
4. **Gerenciador de Cores (ACI) e Penas:**
   - Aba visual para editar cores ACI, espessuras e alturas de texto, com salvamento persistente (`QgsSettings`) e botão de restaurar padrões.
5. **Conversão Nativa para DWG:**
   - Checkbox integrado que aciona o ODA File Converter e gera o arquivo `.dwg` lado a lado com o `.dxf`.
6. **Execução em Segundo Plano (`QgsTask`):**
   - Não congela a interface do QGIS e mostra o progresso passo a passo.

---

## 📌 Recursos e Conformidade Técnica AutoCAD

1. **Recorte Geométrico Rigoroso (Vector Clipping):**
   `native:extractbyextent` com `--CLIP=true` em todas as camadas vetoriais (exceto os nós, recortados por extensão sem clip geométrico). Curvas de nível e perímetros de quadra/lote são cortados na fronteira da Bounding Box, sem linhas extrapolando o desenho.

2. **Separação Automática de Redes por Diâmetro Nominal (`cat_dnom`):**
   Layers individuais `Rede_DN50` … `Rede_DN300`, cada um com cor ACI e espessura de pena próprias.

3. **Propriedades 100% ByLayer:**
   Todos os overrides de cor (`color`, `true_color`) e espessura (`lineweight`) são descartados das entidades. Alterar a cor ou o peso do layer no AutoCAD reflete em todos os objetos.

4. **Remoção do `Global Width` das Polilinhas:**
   `const_width` é expurgado das `LWPOLYLINE`, restaurando o controle de espessura via Lineweight do Layer.

5. **Hachuras Sólidas de Lote e Meio-Fio:**
   Lotes (ACI 95) e meio-fio (ACI 213) saem com preenchimento sólido a 50% de transparência.
   **As hachuras de quadra são removidas** — sobrepunham o desenho sem ganho de leitura.

6. **Textos como MTEXT nativo editável:**
   Todo `TEXT`/`MTEXT` é reconstruído com a estrutura de grupos do gabarito que não trava no AutoCAD Mac: fonte Arial via código inline `\f` (sem STYLE dedicada), vetor `text_direction` em vez do ângulo de rotação, e `width`/`defined_height`/`flow_direction`/`line_spacing` explícitos.

7. **Integridade Estrutural Autodesk:**
   Layers canônicas são **criadas do zero** (nunca renomeadas — renomear via `dxf.name` não atualiza o índice da tabela LAYER do `ezdxf` e produzia nomes duplicados), e as layers órfãs do QGIS são removidas ao final.

8. **DWG nativo via ODA File Converter:**
   Ao final, o DXF é convertido para DWG (ACAD2018) pelo motor oficial da Open Design Alliance, eliminando a etapa de reinterpretação do importador do AutoCAD. Etapa opcional — é pulada se o ODA não estiver instalado.

---

## 🚀 Como Usar no QGIS

O plugin já está vinculado aos perfis do seu QGIS.

1. Abra o QGIS.
2. Acesse o menu **Complementos > Gerenciar e Instalar Complementos > Instalados**.
3. Marque a caixa de seleção ao lado de **Exportador DXF/CAD Pro**.
4. Um novo botão com o ícone CAD surgirá na barra de ferramentas e no menu **Exportador CAD > Exportar Recorte para DXF / CAD Pro**.
5. Na janela aberta:
   - Clique em **Capturar Extensão da Tela Visível** ou em **Desenhar Retângulo no Mapa**.
   - Defina a **Escala Alvo** (ex: `800`).
   - Escolha o arquivo de saída `.dxf` (e marque se deseja o `.dwg` simultâneo).
   - Clique em **Exportar para DXF/DWG**.

---

## 💻 Execução via Script Standalone (Legado / Linha de Comando)

Caso queira rodar o pipeline fora da interface do QGIS (batch/headless):

```bash
pip3 install -r requirements.txt
python3 /Volumes/Mac_Dados/Repos/MJ-PROJETOQGIS/pipeline_export_recorte.py
```

### Pré-requisitos

- QGIS em `/Applications/QGIS-final-4_2_0.app` (constante `QGIS_PROCESS_BIN`)
- ODA File Converter em `/Applications/ODAFileConverter.app` (opcional, constante `ODA_FILE_CONVERTER_BIN`)

### Parâmetros Padrão

- **Bounding Box (EPSG:31982 — SIRGAS 2000 / UTM 22S):** `720234.495, 720472.095, 8192330.572, 8192498.572`
- **Escala de Simbologia:** `1:800`
- **Saída:** `/Volumes/Mac_Dados/Downloads/sicob_COMPLETO_FINAL.dxf` (+ `.dwg`)

---

## 📐 Tabela de Layers e Penas

Fonte da verdade: `LAYER_CONFIG` e `TEXT_HEIGHTS` em [pipeline_export_recorte.py](pipeline_export_recorte.py).

| Layer | Cor (ACI) | Espessura | Altura do texto | Descrição |
|---|---|---|---|---|
| `0` | 7 | Padrão | — | Layer default |
| `Rede_Lote` | 72 | 0.20 mm | 1.60 | Lotes cadastrais e hachuras |
| `Texto_Lote` | 7 | 0.20 mm | 1.60 | Textos de lote (separados do desenho) |
| `Rede_Quadra` | 32 | 0.25 mm | 3.00 | Perímetros de quadra |
| `Rede_Meio_Fio` | 221 | 0.25 mm | — | Meio-fio e calçadas |
| `Logradouro` | 8 | 0.18 mm | 2.20 | Textos de vias e eixos |
| `Curva_Nivel_Mestra` | 14 | 0.35 mm | — | Curvas mestras |
| `Curva_Nivel_Intermediaria` | 252 | 0.15 mm | — | Curvas intermediárias |
| `Nos` | 7 | 0.25 mm | — | Nós e conexões da rede |
| `Rede_DN50` | 4 (ciano) | 0.40 mm | 1.60 | Rede de água DN 50 |
| `Rede_DN75` | 3 (verde) | 0.40 mm | 1.60 | Rede de água DN 75 |
| `Rede_DN100` | 1 (vermelho) | 0.50 mm | 1.60 | Rede de água DN 100 |
| `Rede_DN150` | 5 (azul) | 0.50 mm | 1.60 | Rede de água DN 150 |
| `Rede_DN200` | 6 (magenta) | 0.50 mm | 1.60 | Rede de água DN 200 |
| `Rede_DN250` | 14 (laranja) | 0.60 mm | 1.60 | Rede de água DN 250 |
| `Rede_DN300` | 5 (azul) | 0.60 mm | 1.60 | Rede de água DN 300 |

As curvas de nível recebem 70% de transparência de entidade.

---

## ⚠️ Limitações conhecidas

- **Caminhos e IDs fixos:** as camadas de origem (`.gpkg` de Anápolis e do projeto de água) e os IDs UUID das camadas do QGIS estão embutidos em `run_pipeline`. O script serve um único projeto.
- **Alturas de texto acopladas à escala:** `TEXT_HEIGHTS` está em metros, calibrado para 1:800. Mudar `SYMBOLOGY_SCALE` descalibra os textos sem aviso.
- **Sem testes automatizados.** A validação até aqui foi visual, no AutoCAD.

---

## 📁 `legado/`

Tentativas anteriores baseadas em manipulação textual do DXF (regex sobre pares de códigos), substituídas pelo pós-processador `ezdxf`. Mantidas só como histórico — **não use**, a `LAYER_CONFIG` delas está desatualizada.
