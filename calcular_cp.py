import glob
import os
import xml.etree.ElementTree as ET
import math

def haversine(lon1, lat1, lon2, lat2):
    R = 6371000
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)
    a = math.sin(delta_phi/2.0)**2 + math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda/2.0)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
    return R * c

def processar_kml(filepath):
    tree = ET.parse(filepath)
    root = tree.getroot()
    ns = {'kml': 'http://www.opengis.net/kml/2.2'}
    extensao_cp_metros = 0.0
    contagem_ch = 0
    contagem_tr = 0

    for placemark in root.findall('.//kml:Placemark', ns):
        style_url = placemark.find('kml:styleUrl', ns)
        if style_url is not None:
            estilo = style_url.text.strip()
            if estilo == '#CP':
                line_string = placemark.find('.//kml:LineString/kml:coordinates', ns)
                if line_string is not None:
                    coords_text = line_string.text.strip().split()
                    coords = [tuple(map(float, pt.split(','))) for pt in coords_text]
                    for i in range(len(coords) - 1):
                        lon1, lat1 = coords[i][:2]
                        lon2, lat2 = coords[i+1][:2]
                        extensao_cp_metros += haversine(lon1, lat1, lon2, lat2)
            elif estilo == '#CH':
                contagem_ch += 1
            elif estilo == '#TR':
                contagem_tr += 1

    return extensao_cp_metros, contagem_ch, contagem_tr

# --- Início do processamento ---

# Quando rodado pelo IDLE (F5), usa a pasta onde o script está salvo
pasta = os.path.dirname(os.path.abspath(__file__))
arquivos_kml = glob.glob(os.path.join(pasta, '*_corrigido.kml'))

if not arquivos_kml:
    print("Nenhum arquivo '_corrigido.kml' foi encontrado nesta pasta.")
else:
    soma_total_cp = 0.0
    soma_total_ch = 0
    soma_total_tr = 0

    print(f"Foram encontrados {len(arquivos_kml)} arquivo(s) corrigido(s). Iniciando a leitura...\n")
    print("-" * 50)

    for arquivo in arquivos_kml:
        try:
            ext_cp, cont_ch, cont_tr = processar_kml(arquivo)
            soma_total_cp += ext_cp
            soma_total_ch += cont_ch
            soma_total_tr += cont_tr

            print(f"Arquivo: {os.path.basename(arquivo)}")
            print(f" -> Extensão da rede CP: {ext_cp / 1000:.2f} km")
            print(f" -> Quantidade de CH: {cont_ch}")
            print(f" -> Quantidade de TR: {cont_tr}")
            print("-" * 50)
        except Exception as e:
            print(f"Erro ao ler o arquivo {os.path.basename(arquivo)}: {e}")
            print("-" * 50)

    print(f"\nRESUMO FINAL DE TODOS OS ARQUIVOS:")
    print(f"Extensão TOTAL (CP): {soma_total_cp / 1000:.2f} km")
    print(f"Quantidade TOTAL (CH): {soma_total_ch}")
    print(f"Quantidade TOTAL (TR): {soma_total_tr}")
