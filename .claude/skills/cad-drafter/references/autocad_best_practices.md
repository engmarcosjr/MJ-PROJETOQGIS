# Boas Práticas e Diretrizes de Compatibilidade AutoCAD (Windows / macOS)

## 1. Problemas Críticos do AutoCAD no macOS e Soluções

O AutoCAD para macOS possui peculiaridades no renderizador de texto e na tabela de estilos que causam travamentos frequentes ou renderizações corrompidas se o DXF não for gerado rigorosamente:

### MTEXT vs TEXT
1. **Evitar criar novas STYLE tables com fontes TrueType:**
   - Não crie entradas `STYLE` personalizadas referenciando `.ttf` de sistema (ex: Arial.ttf), pois o motor Mac frequentemente falha ao resolver o arquivo no caminho Unix.
   - **Solução:** Mantenha o estilo do MTEXT apontando para `STANDARD` e injete a família tipográfica diretamente na formatação inline do MTEXT:
     `\fArial|i0|b0;Texto Aqui`
2. **Direção do Texto e Vetor de Extrusão:**
   - O AutoCAD Mac espera `text_direction` explícito como vetor tridimensional `(cos(rad), sin(rad), 0.0)` para textos rotacionados, em vez de apenas o código 50 (ângulo em graus).
3. **Atributos Canônicos de MTEXT:**
   - Preencher explicitamente `attachment_point` (ex: 5 para Middle Center, 1 para Top Left), `flow_direction` (5 = ByStyle), e `line_spacing_style` (1 = AtLeast).
   - Utilizar espaço não-separável `\~` em identificadores compostos para evitar quebras de linha automáticas no meio de siglas ou diâmetros.

---

## 2. Estrutura Canônica de Layers e DXF (ezdxf)

1. **Nunca Renomear Layers via `layer.dxf.name`:**
   - No `ezdxf`, renomear diretamente `dxf.name` corrompe a tabela de símbolos de camadas, deixando entradas duplicadas.
   - **Regra:** Crie as camadas canônicas do zero e reaponte as entidades (`entity.dxf.layer = novo_nome`).
2. **Propriedades ByLayer Rigorosas:**
   - Descarte overrides em entidades: limpe `color`, `true_color` e `lineweight` de cada entidade, deixando a gestão inteiramente para a camada.
   - Exceção: Hachuras com transparência ou cores de preenchimento específicas (ex: ACI 95 para lote, ACI 213 para calçada).
3. **Versão do DXF:**
   - Utilize a versão **AC1032 (AutoCAD 2018)**. Versões legadas (AC1018 / 2004) não suportam de forma estável o editor MTEXT in-place moderno do macOS.

---

## 3. Viewports e PaperSpace

1. **Camada da Moldura da Viewport:**
   - Sempre coloque a entidade `VIEWPORT` na camada `Defpoints` (ou crie uma camada `_VIEWPORT` com flag `no-plot`). Isso garante que a linha de contorno da janela não saia na plotagem/PDF.
2. **Flag PaperSpace:**
   - Entidades criadas para a folha, margens, carimbo e notas devem ter o atributo `dxf.paperspace = 1`.
3. **Parâmetros da VIEWPORT no ezdxf:**
   - `center`: Posição $(X, Y)$ do centro da janela na prancha (em mm).
   - `width`, `height`: Dimensões físicas da janela na folha (em mm).
   - `view_center_point`: Coordenadas $(X, Y)$ do ModelSpace focadas no centro da janela (em metros).
   - `view_height`: Altura visível do ModelSpace $=\frac{height}{custom\_scale}$.
   - `custom_scale`: Fator de escala da viewport $=\frac{1000.0}{\text{Escala}}$.
   - `status`: Flag ativa (geralmente $status > 0$).
