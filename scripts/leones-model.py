#!/usr/bin/env python3
"""🦁 LEONES · Model identity probe.

ANTES: responde «¿qué archivo de modelo voy a medir?». No lo ejecuta, descarga
ni modifica. Calcula tamaño y SHA-256 para identificar exactamente el archivo.

DURANTE: lee el fichero local por bloques para calcular su hash. Puede tardar
en modelos grandes; eso es normal.

DESPUÉS: el hash permite reproducibilidad. La extensión solo orienta sobre el
formato: no demuestra compatibilidad con un runtime. El siguiente paso es
comprobar runtime y después inferencia.
"""
from __future__ import annotations
from pathlib import Path
import argparse,hashlib,json

def sha256(path):
 h=hashlib.sha256()
 with path.open('rb') as f:
  for chunk in iter(lambda:f.read(1024*1024),b''): h.update(chunk)
 return h.hexdigest()
def main():
 p=argparse.ArgumentParser(description='Identifica un archivo de modelo sin ejecutarlo')
 p.add_argument('model'); p.add_argument('--json',action='store_true'); p.add_argument('--explain',action='store_true'); a=p.parse_args()
 path=Path(a.model).expanduser()
 if not path.is_file():
  print(f'ERROR: no existe un archivo regular en: {path}\nSiguiente paso: comprueba la ruta y vuelve a intentarlo.'); return 2
 if a.explain and not a.json: print('🦁 LEONES · Identificación de modelo\nVoy a leer el archivo para obtener tamaño, extensión y SHA-256. No ejecutaré el modelo ni lo publicaré.\n')
 data={'tool':'leones-model','tool_version':'1.1','status':'ok','model':{'name':path.name,'path':str(path),'size_bytes':path.stat().st_size,'sha256':sha256(path),'format':path.suffix.lower().lstrip('.') or None},'next_step':'runtime'}
 if a.json: print(json.dumps(data,indent=2,ensure_ascii=False)); return 0
 m=data['model']; print(f"Archivo: {m['name']}\nTamaño: {m['size_bytes']/1024**3:.2f} GB\nFormato indicado por extensión: {m['format'] or 'desconocido'}\nSHA-256: {m['sha256']}\n\nSiguiente paso recomendado: comprobar un runtime local compatible.")
 return 0
if __name__=='__main__': raise SystemExit(main())
