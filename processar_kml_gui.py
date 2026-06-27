"""
processar_kml_gui.py
--------------------
Abre uma janela para selecionar arquivos .kml brutos,
corrige cada um (gera _corrigido.kml na mesma pasta)
e exibe extensão CP, quantidade de CH e TR.
"""

import os
import math
import xml.etree.ElementTree as ET
import tkinter as tk
from tkinter import filedialog, scrolledtext, messagebox

# ─── Configuração KML ────────────────────────────────────────────────────────

STYLE_MAP = {"CH": "CHAVE", "CP": "CABO", "TR": "TRAFO"}
RENAME_FROM_DESC = {"CH", "TR"}
ORDEM_PASTAS = ["CHAVE", "CABO", "TRAFO"]

ET.register_namespace("", "http://www.opengis.net/kml/2.2")
ET.register_namespace("gx", "http://www.google.com/kml/ext/2.2")
ET.register_namespace("atom", "http://www.w3.org/2005/Atom")

# ─── Helpers ─────────────────────────────────────────────────────────────────

def strip_ns(tag):
    return tag.split("}")[-1] if "}" in tag else tag

def get_child_text(elem, tag):
    for child in elem:
        if strip_ns(child.tag) == tag:
            return child.text
    return None

def set_child_text(elem, tag, value):
    for child in elem:
        if strip_ns(child.tag) == tag:
            child.text = value
            return

def extract_first_field(description):
    if not description:
        return None
    parts = description.split("/")
    return parts[0].strip() if parts else None

def haversine(lon1, lat1, lon2, lat2):
    R = 6371000
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlam = math.radians(lon2 - lon1)
    a = math.sin(dphi/2)**2 + math.cos(phi1)*math.cos(phi2)*math.sin(dlam/2)**2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))

# ─── Lógica de processamento ─────────────────────────────────────────────────

def _processar_placemark(pm, bucket):
    style_raw = get_child_text(pm, "styleUrl") or ""
    style_id = style_raw.lstrip("#").upper()
    destino = STYLE_MAP.get(style_id)
    if destino is None:
        return
    if style_id in RENAME_FROM_DESC:
        desc = get_child_text(pm, "description")
        novo = extract_first_field(desc)
        if novo:
            set_child_text(pm, "name", novo)
    bucket.setdefault(destino, []).append(pm)

def corrigir_kml(input_path):
    tree = ET.parse(input_path)
    root = tree.getroot()
    doc_elem = next((c for c in root if strip_ns(c.tag) == "Document"), None)
    if doc_elem is None:
        raise ValueError("Arquivo sem elemento <Document>.")

    styles, bucket = [], {}
    for child in doc_elem:
        tag = strip_ns(child.tag)
        if tag in ("Style", "StyleMap"):
            styles.append(child)
        elif tag == "Folder":
            for elem in child:
                if strip_ns(elem.tag) == "Placemark":
                    _processar_placemark(elem, bucket)
        elif tag == "Placemark":
            _processar_placemark(child, bucket)

    doc_elem.clear()
    for s in styles:
        doc_elem.append(s)
    for pasta in ORDEM_PASTAS:
        elems = bucket.get(pasta, [])
        if not elems:
            continue
        folder_el = ET.SubElement(doc_elem, "Folder")
        ET.SubElement(folder_el, "name").text = pasta
        for pm in elems:
            folder_el.append(pm)

    output_path = os.path.splitext(input_path)[0] + "_corrigido.kml"
    tree.write(output_path, encoding="UTF-8", xml_declaration=True)
    return output_path

def calcular_metricas(filepath):
    tree = ET.parse(filepath)
    root = tree.getroot()
    ns = {"kml": "http://www.opengis.net/kml/2.2"}
    ext_cp, cnt_ch, cnt_tr = 0.0, 0, 0

    for pm in root.findall(".//kml:Placemark", ns):
        su = pm.find("kml:styleUrl", ns)
        if su is None:
            continue
        estilo = su.text.strip()
        if estilo == "#CP":
            cel = pm.find(".//kml:LineString/kml:coordinates", ns)
            if cel is not None:
                pts = [tuple(map(float, p.split(","))) for p in cel.text.strip().split()]
                for i in range(len(pts)-1):
                    ext_cp += haversine(pts[i][0], pts[i][1], pts[i+1][0], pts[i+1][1])
        elif estilo == "#CH":
            cnt_ch += 1
        elif estilo == "#TR":
            cnt_tr += 1

    return ext_cp, cnt_ch, cnt_tr

# ─── Interface gráfica ───────────────────────────────────────────────────────

def selecionar_e_processar(text_widget, btn):
    arquivos = filedialog.askopenfilenames(
        title="Selecione os arquivos KML brutos",
        filetypes=[("Arquivos KML", "*.kml"), ("Todos os arquivos", "*.*")]
    )

    # Filtra _corrigido.kml caso o usuário selecione por engano
    arquivos = [f for f in arquivos if not f.endswith("_corrigido.kml")]

    if not arquivos:
        return

    btn.config(state="disabled", text="Processando...")
    text_widget.config(state="normal")
    text_widget.delete("1.0", tk.END)

    soma_cp, soma_ch, soma_tr = 0.0, 0, 0
    separador = "─" * 52

    text_widget.insert(tk.END, f"{'─'*52}\n")

    for bruto in sorted(arquivos):
        nome = os.path.basename(bruto)
        text_widget.insert(tk.END, f"📄 {nome}\n")

        try:
            corrigido = corrigir_kml(bruto)
            text_widget.insert(tk.END, f"   ✅ Corrigido gerado\n")
        except Exception as e:
            text_widget.insert(tk.END, f"   ❌ Erro ao corrigir: {e}\n")
            text_widget.insert(tk.END, f"{separador}\n")
            continue

        try:
            ext_cp, cnt_ch, cnt_tr = calcular_metricas(corrigido)
            soma_cp += ext_cp
            soma_ch += cnt_ch
            soma_tr += cnt_tr
            text_widget.insert(tk.END, f"   📏 Extensão CP : {ext_cp/1000:.2f} km\n")
            text_widget.insert(tk.END, f"   🔌 Quantidade CH: {cnt_ch}\n")
            text_widget.insert(tk.END, f"   ⚡ Quantidade TR: {cnt_tr}\n")
        except Exception as e:
            text_widget.insert(tk.END, f"   ❌ Erro ao calcular: {e}\n")

        text_widget.insert(tk.END, f"{separador}\n")

    text_widget.insert(tk.END, f"\n📊 RESUMO FINAL\n{'═'*52}\n")
    text_widget.insert(tk.END, f"   Extensão TOTAL (CP) : {soma_cp/1000:.2f} km\n")
    text_widget.insert(tk.END, f"   Quantidade TOTAL CH : {soma_ch}\n")
    text_widget.insert(tk.END, f"   Quantidade TOTAL TR : {soma_tr}\n")
    text_widget.insert(tk.END, f"{'═'*52}\n")
    text_widget.config(state="disabled")

    btn.config(state="normal", text="📂  Selecionar arquivos KML")

def main():
    root = tk.Tk()
    root.title("Processador KML")
    root.resizable(False, False)
    root.configure(bg="#1e1e2e")

    # Cabeçalho
    header = tk.Frame(root, bg="#313244", pady=12)
    header.pack(fill="x")
    tk.Label(
        header, text="⚡  Processador KML",
        font=("Segoe UI", 15, "bold"),
        bg="#313244", fg="#cdd6f4"
    ).pack()
    tk.Label(
        header, text="Corrige o arquivo e calcula CP · CH · TR",
        font=("Segoe UI", 9),
        bg="#313244", fg="#a6adc8"
    ).pack()

    # Botão
    btn_frame = tk.Frame(root, bg="#1e1e2e", pady=14)
    btn_frame.pack()

    btn = tk.Button(
        btn_frame,
        text="📂  Selecionar arquivos KML",
        font=("Segoe UI", 11, "bold"),
        bg="#89b4fa", fg="#1e1e2e",
        activebackground="#74c7ec", activeforeground="#1e1e2e",
        relief="flat", padx=20, pady=10, cursor="hand2",
        bd=0
    )
    btn.pack()
    btn.config(command=lambda: selecionar_e_processar(resultado, btn))

    # Área de resultado
    resultado_frame = tk.Frame(root, bg="#1e1e2e", padx=16, pady=0)
    resultado_frame.pack(fill="both", expand=True)

    resultado = scrolledtext.ScrolledText(
        resultado_frame,
        width=58, height=22,
        font=("Consolas", 10),
        bg="#181825", fg="#cdd6f4",
        insertbackground="#cdd6f4",
        relief="flat", bd=0,
        state="disabled"
    )
    resultado.pack(pady=(0, 14))

    root.mainloop()

if __name__ == "__main__":
    main()
