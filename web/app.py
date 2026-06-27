import os
import math
import uuid
import xml.etree.ElementTree as ET
from flask import Flask, request, jsonify, send_file, render_template
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 50 * 1024 * 1024  # 50MB max
UPLOAD_FOLDER = '/tmp/kml_uploads'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# ─── KML Logic ───────────────────────────────────────────────────────────────

STYLE_MAP = {"CH": "CHAVE", "CP": "CABO", "TR": "TRAFO"}
RENAME_FROM_DESC = {"CH", "TR"}
ORDEM_PASTAS = ["CHAVE", "CABO", "TRAFO"]

ET.register_namespace("", "http://www.opengis.net/kml/2.2")
ET.register_namespace("gx", "http://www.google.com/kml/ext/2.2")
ET.register_namespace("atom", "http://www.w3.org/2005/Atom")

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

def corrigir_kml(input_path, output_path):
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

    tree.write(output_path, encoding="UTF-8", xml_declaration=True)

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

# ─── Routes ──────────────────────────────────────────────────────────────────

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/processar", methods=["POST"])
def processar():
    if "files" not in request.files:
        return jsonify({"error": "Nenhum arquivo enviado."}), 400

    files = request.files.getlist("files")
    resultados = []
    session_id = str(uuid.uuid4())
    session_dir = os.path.join(UPLOAD_FOLDER, session_id)
    os.makedirs(session_dir, exist_ok=True)

    for f in files:
        if not f.filename.endswith(".kml"):
            continue
        nome = secure_filename(f.filename)
        if nome.endswith("_corrigido.kml"):
            continue

        input_path = os.path.join(session_dir, nome)
        output_name = nome.replace(".kml", "_corrigido.kml")
        output_path = os.path.join(session_dir, output_name)
        f.save(input_path)

        try:
            corrigir_kml(input_path, output_path)
            ext_cp, cnt_ch, cnt_tr = calcular_metricas(output_path)
            resultados.append({
                "nome": nome,
                "sucesso": True,
                "ext_cp_km": round(ext_cp / 1000, 2),
                "cnt_ch": cnt_ch,
                "cnt_tr": cnt_tr,
                "download_id": session_id,
                "download_file": output_name,
            })
        except Exception as e:
            resultados.append({"nome": nome, "sucesso": False, "erro": str(e)})

    return jsonify({"resultados": resultados})

@app.route("/download/<session_id>/<filename>")
def download(session_id, filename):
    path = os.path.join(UPLOAD_FOLDER, session_id, secure_filename(filename))
    if not os.path.exists(path):
        return "Arquivo não encontrado.", 404
    return send_file(path, as_attachment=True, download_name=filename)

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
