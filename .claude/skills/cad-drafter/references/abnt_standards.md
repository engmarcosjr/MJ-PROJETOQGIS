# Normas Técnicas Aplicadas ao Projeto CAD (ABNT)

## 1. Formatos de Papel e Margens (ABNT NBR 16752)

A norma fixa as dimensões das folhas da série A (em milímetros) e suas margens para arquivo/perfuração e corte:

| Formato | Largura total ($W$) | Altura total ($H$) | Margem Esquerda ($M_E$) | Margens Superior / Inferior / Direita ($M$) |
|---|---|---|---|---|
| **A0** | 1189 mm | 841 mm | 25 mm | 10 mm |
| **A1** | 841 mm | 594 mm | 25 mm | 10 mm |
| **A2** | 594 mm | 420 mm | 25 mm | 7 mm |
| **A3** | 420 mm | 297 mm | 25 mm | 7 mm |
| **A4** | 210 mm | 297 mm | 25 mm | 7 mm |

### Dimensões da Área Útil de Desenho
A área interna da margem é dada por:
$$W_{util} = W - (M_E + M)$$
$$H_{util} = H - (M + M)$$

* **A0:** $1154 \times 821$ mm
* **A1:** $806 \times 574$ mm
* **A2:** $562 \times 406$ mm
* **A3:** $388 \times 283$ mm
* **A4:** $178 \times 283$ mm

---

## 2. Carimbo / Selo de Identificação (NBR 16861 / NBR 16752)

- **Localização:** Canto inferior direito da folha, encostado nas margens direita e inferior.
- **Largura padrão:** $178\text{ mm}$ (compatível com a dobra para A4).
- **Campos obrigatórios:**
  1. Identificação do cliente/proprietário;
  2. Título do projeto / Obra;
  3. Conteúdo da prancha (ex: Planta Baixa, Perfil Longitudinal, Rede de Água);
  4. Escala(s) indicada(s) (ex: `1:500`, `INDICADA`);
  5. Data e número da revisão;
  6. Identificação do Responsável Técnico (Nome, Título, Registro CREA/CAU);
  7. Número da prancha e total (ex: `01/03`).

---

## 3. Escalas Padronizadas (ABNT NBR 16861)

As escalas recomendadas para desenhos técnicos em engenharia e arquitetura são:

### Redução para Detalhes / Peças Especiais:
`1:1`, `1:2`, `1:5`, `1:10`, `1:20`, `1:25`, `1:50`, `1:75`

### Redução para Plantas Baixas e Redes Prediais/Urbanas:
`1:100`, `1:125`, `1:200`, `1:250`, `1:500`, `1:750`, `1:1000`

### Redução para Cadastro Urbano e Cartografia:
`1:1250`, `1:1500`, `1:2000`, `1:2500`, `1:5000`, `1:10000`

---

## 4. Relação ModelSpace (Metros) vs PaperSpace (Milímetros)

No fluxo de projetos de infraestrutura / topografia / saneamento:
- **ModelSpace:** Unidades em **Metros** ($1 \text{ unit} = 1\text{ m}$).
- **PaperSpace:** Unidades em **Milímetros** ($1 \text{ unit} = 1\text{ mm}$).
- **Conversão:**
  $$1\text{ m} = 1000\text{ mm}$$
  Para um objeto de tamanho real $D\text{ metros}$, seu tamanho na escala $1:E$ no papel será:
  $$D_{papel} (\text{mm}) = \frac{D \times 1000}{E}$$
- **Fator CustomScale da Viewport:**
  $$\text{CustomScale} = \frac{1000.0}{E}$$
- **Equivalência AutoCAD Zoom XP:**
  $$\text{Zoom } \left(\frac{1000}{E}\right)\text{xp}$$
  * Exemplo Escala 1:500: Zoom $(1000/500)\text{xp} \rightarrow 2\text{xp}$ (CustomScale = 2.0).
  * Exemplo Escala 1:1000: Zoom $(1000/1000)\text{xp} \rightarrow 1\text{xp}$ (CustomScale = 1.0).
  * Exemplo Escala 1:200: Zoom $(1000/200)\text{xp} \rightarrow 5\text{xp}$ (CustomScale = 5.0).
