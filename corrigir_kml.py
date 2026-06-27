"""
corrigir_kml.py
---------------
Converte arquivos KML do formato BRUTO (exportado do sistema) para o
formato CORRIGIDO, aplicando as seguintes transformações:

1. REORGANIZAÇÃO EM PASTAS POR TIPO:
   - Pasta "CHAVE"  → elementos com styleUrl #CH
   - Pasta "CABO"   → elementos com styleUrl #CP
   - Pasta "TRAFO"  → elementos com styleUrl #TR

2. ELEMENTOS REMOVIDOS (não entram no arquivo final):
   - #AP  → Aterramento Primário
   - #CS  → Cabo Secundário (tensão 440V)
   - #JP  → Jumper Primário
   - #JS  → Jumper Secundário
   - #PR  → Para-raio
   - #PT  → Poste
   - (e demais styles não mapeados acima)

3. CORREÇÃO DO CAMPO <name> NOS ELEMENTOS CHAVE E TRAFO:
   - BRUTO:     <name> contém o ID interno do sistema (ex: 84869354)
   - CORRIGIDO: <name> passa a ser o primeiro campo da <description>
                Ex: desc "0300873077 / F / IND" → name = "0300873077"

4. CABOS (#CP): name e description permanecem iguais — apenas mudam de pasta.

USO:
   python corrigir_kml.py                  → processa todos os .kml da pasta atual
   python corrigir_kml.py /caminho/pasta   → processa todos os .kml da pasta indicada

Saída: cada arquivo "nome.kml" gera "nome_corrigido.kml" na mesma pasta.
       Arquivos que já terminam com "_corrigido.kml" são ignorados.

REQUISITOS: Python 3.8+ (apenas biblioteca padrão)
"""

import sys
import xml.etree.ElementTree as ET
from pathlib import Path

# ─── Configuração ────────────────────────────────────────────────────────────

# Mapeamento: styleUrl → nome da pasta de destino (None = elemento removido)
STYLE_MAP = {
    "CH": "CHAVE",
    "CP": "CABO",
    "TR": "TRAFO",
}

# Estilos cujo <name> deve ser substituído pelo primeiro campo da <description>
RENAME_FROM_DESC = {"CH", "TR"}

# Ordem das pastas no arquivo de saída
ORDEM_PASTAS = ["CHAVE", "CABO", "TRAFO"]

# Namespaces KML para registro (evita prefixos ns0, ns1...)
ET.register_namespace("", "http://www.opengis.net/kml/2.2")
ET.register_namespace("gx", "http://www.google.com/kml/ext/2.2")
ET.register_namespace("atom", "http://www.w3.org/2005/Atom")

# ─── Helpers ─────────────────────────────────────────────────────────────────

def strip_ns(tag: str) -> str:
    """Remove o namespace de uma tag XML."""
    return tag.split("}")[-1] if "}" in tag else tag


def get_child_text(elem: ET.Element, tag: str) -> str | None:
    """Retorna o texto do primeiro filho com a tag indicada."""
    for child in elem:
        if strip_ns(child.tag) == tag:
            return child.text
    return None


def set_child_text(elem: ET.Element, tag: str, value: str) -> None:
    """Define o texto do primeiro filho com a tag indicada."""
    for child in elem:
        if strip_ns(child.tag) == tag:
            child.text = value
            return


def extract_first_field(description: str) -> str | None:
    """Extrai o primeiro campo antes de ' / ' da descrição."""
    if not description:
        return None
    parts = description.split("/")
    return parts[0].strip() if parts else None

# ─── Processamento ───────────────────────────────────────────────────────────

def corrigir_kml(input_path: Path) -> Path:
    """
    Lê um KML bruto, aplica as correções e salva o arquivo corrigido.
    Retorna o caminho do arquivo gerado.
    """
    print(f"  Processando: {input_path.name}")

    tree = ET.parse(input_path)
    root = tree.getroot()

    # Localiza o elemento <Document>
    doc_elem = None
    for child in root:
        if strip_ns(child.tag) == "Document":
            doc_elem = child
            break

    if doc_elem is None:
        raise ValueError("Arquivo KML sem elemento <Document>.")

    # ── Coleta Styles e classifica Placemarks ─────────────────────────────────
    styles = []
    placemarks_by_folder: dict[str, list[ET.Element]] = {}

    for child in doc_elem:
        tag = strip_ns(child.tag)

        if tag in ("Style", "StyleMap"):
            styles.append(child)

        elif tag == "Folder":
            for elem in child:
                if strip_ns(elem.tag) == "Placemark":
                    _processar_placemark(elem, placemarks_by_folder)

        elif tag == "Placemark":
            # Placemarks diretamente no Document (sem Folder intermediária)
            _processar_placemark(child, placemarks_by_folder)

    # ── Reconstrói o <Document> ───────────────────────────────────────────────
    doc_elem.clear()   # limpa tudo (styles + folders antigas)

    for s in styles:
        doc_elem.append(s)

    for pasta in ORDEM_PASTAS:
        elementos = placemarks_by_folder.get(pasta, [])
        if not elementos:
            continue
        folder_el = ET.SubElement(doc_elem, "Folder")
        name_el = ET.SubElement(folder_el, "name")
        name_el.text = pasta
        for pm in elementos:
            folder_el.append(pm)

    # ── Salva ─────────────────────────────────────────────────────────────────
    output_path = input_path.parent / (input_path.stem + "_corrigido.kml")
    tree.write(output_path, encoding="UTF-8", xml_declaration=True)

    stats = {p: len(placemarks_by_folder.get(p, [])) for p in ORDEM_PASTAS}
    print(f"    → {output_path.name}")
    print(f"       CHAVE: {stats['CHAVE']} | CABO: {stats['CABO']} | TRAFO: {stats['TRAFO']}")
    return output_path


def _processar_placemark(pm: ET.Element, bucket: dict) -> None:
    """Classifica e (se necessário) corrige o nome de um Placemark."""
    style_raw = get_child_text(pm, "styleUrl") or ""
    style_id = style_raw.lstrip("#").upper()

    destino = STYLE_MAP.get(style_id)
    if destino is None:
        return  # elemento removido ou estilo desconhecido

    if style_id in RENAME_FROM_DESC:
        desc = get_child_text(pm, "description")
        novo_nome = extract_first_field(desc)
        if novo_nome:
            set_child_text(pm, "name", novo_nome)

    bucket.setdefault(destino, []).append(pm)

# ─── Entrypoint ──────────────────────────────────────────────────────────────

def main():
    if len(sys.argv) > 1:
        pasta = Path(sys.argv[1])
    else:
        # Quando rodado pelo IDLE (F5), usa a pasta onde o próprio script está salvo
        pasta = Path(__file__).parent

    if not pasta.is_dir():
        print(f"Erro: '{pasta}' não é um diretório válido.")
        sys.exit(1)

    arquivos = [
        f for f in sorted(pasta.glob("*.kml"))
        if not f.stem.endswith("_corrigido")
    ]

    if not arquivos:
        print(f"Nenhum arquivo .kml encontrado em '{pasta}'.")
        return

    print(f"Encontrados {len(arquivos)} arquivo(s) .kml para processar.\n")

    sucesso, erros = 0, 0
    for arq in arquivos:
        try:
            corrigir_kml(arq)
            sucesso += 1
        except Exception as e:
            print(f"    ERRO ao processar {arq.name}: {e}")
            erros += 1

    print(f"\nConcluído: {sucesso} corrigido(s), {erros} com erro(s).")


if __name__ == "__main__":
    main()
