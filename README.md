# 🗺️ Processador KML

Ferramentas Python para corrigir arquivos KML exportados do sistema e calcular métricas de rede elétrica.

---

## 📦 Scripts disponíveis

| Arquivo | Descrição |
|---|---|
| `corrigir_kml.py` | Corrige arquivos KML brutos — reorganiza por pasta (CHAVE, CABO, TRAFO) e corrige os nomes |
| `calcular_cp.py` | Calcula extensão CP (km), quantidade de CH e TR nos arquivos corrigidos |
| `processar_kml_gui.py` | Interface gráfica — faz a correção e o cálculo em uma única execução |

---

## ⚙️ O que a correção faz

| Transformação | BRUTO | CORRIGIDO |
|---|---|---|
| Estrutura | 1 pasta única com tudo misturado | 3 pastas: CHAVE, CABO, TRAFO |
| `<name>` das CHAVES | ID interno do sistema | Código operacional (da description) |
| `<name>` dos TRAFOS | ID interno do sistema | Código operacional (da description) |
| Elementos removidos | AP, CS, JP, JS, PR, PT e outros | Não aparecem |

---

## 🚀 Como usar

### Opção 1 — Interface gráfica (recomendado)
```bash
python processar_kml_gui.py
```
1. Clique em **Selecionar arquivos KML**
2. Escolha os arquivos `.kml` brutos
3. O resultado aparece na tela e o `_corrigido.kml` é salvo na mesma pasta

### Opção 2 — Linha de comando
```bash
# Corrigir todos os .kml de uma pasta
python corrigir_kml.py /caminho/da/pasta

# Calcular métricas dos corrigidos
python calcular_cp.py /caminho/da/pasta
```

### No IDLE (F5)
Coloque o script na mesma pasta dos arquivos `.kml` e pressione **F5**.

---

## 📋 Requisitos

- Python 3.8+
- Apenas biblioteca padrão (sem instalação de pacotes)
- Para a interface gráfica: `tkinter` (já incluso no Python)

---

## 📊 Exemplo de saída

```
📄 CH_4000637077_-_BRUTO.kml
   ✅ Corrigido gerado
   📏 Extensão CP : 68.72 km
   🔌 Quantidade CH: 33
   ⚡ Quantidade TR: 41

📊 RESUMO FINAL
   Extensão TOTAL (CP) : 68.72 km
   Quantidade TOTAL CH : 33
   Quantidade TOTAL TR : 41
```
