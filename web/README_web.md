# ⚡ Processador KML — Web

Aplicação web para corrigir arquivos KML brutos e calcular métricas de rede elétrica.

## Funcionalidades

- Upload de um ou mais arquivos `.kml`
- Correção automática (reorganiza por CHAVE, CABO, TRAFO)
- Exibe extensão CP (km), quantidade de CH e TR
- Download do arquivo corrigido direto pelo navegador

## Deploy local

```bash
pip install -r requirements.txt
python app.py
# Acesse http://localhost:5000
```
