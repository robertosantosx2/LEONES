#!/usr/bin/env python3
"""🦁 LEONES publish — último paso, siempre explícito.

ANTES: explica que publicar mueve un resultado fuera de la máquina y requiere
una revisión previa. Por defecto solo valida; nunca publica.
DURANTE: ejecuta la misma familia de comprobaciones de privacidad y, solo con
`--publish`, usa GitHub CLI para publicar el fichero indicado.
DESPUÉS: muestra la URL publicada y recuerda que publicación no equivale a
verificación.
"""
from __future__ import annotations
import argparse,base64,re,subprocess
from pathlib import Path
PATTERNS={'private key':r'-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----','email':r'\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b','token':r'(?i)\b(?:ghp_|github_pat_|xox[baprs]-)[A-Za-z0-9_-]+','secret-like field':r'(?i)\b(?:api[_-]?key|access[_-]?token|password|secret)\s*[:=]\s*[^\s`]+','home path':r'(?:/(?:home|Users)/[^\s`]+|[A-Za-z]:\\Users\\[^\s`]+)','MAC address':r'\b(?:[0-9A-F]{2}[:-]){5}[0-9A-F]{2}\b','IPv4 address':r'\b(?:\d{1,3}\.){3}\d{1,3}\b'}
def validate(text:str)->list[str]:return [name for name,pattern in PATTERNS.items() if re.search(pattern,text)]
def main()->int:
 p=argparse.ArgumentParser(description='Valida y publica voluntariamente un resultado LEONES')
 p.add_argument('report'); p.add_argument('--publish',action='store_true',help='Publicar realmente después de superar las comprobaciones')
 p.add_argument('--repo',default='robertosantosx2/LEONES'); p.add_argument('--path',default=''); p.add_argument('--explain',action='store_true')
 a=p.parse_args()
 print('🦁 LEONES · Publicación\nAntes: esto moverá un fichero fuera de tu máquina si eliges --publish. La publicación es voluntaria y no demuestra que el resultado sea correcto.\nDurante: revisaré patrones de privacidad.\nDespués: si publicas, recibirás la URL para conservarla y compartirla.\n')
 path=Path(a.report)
 try:text=path.read_text(encoding='utf-8',errors='replace')
 except OSError as exc: print(f'No se pudo leer el informe: {exc}'); return 2
 findings=validate(text)
 if findings:
  print('⛔ Publicación bloqueada por posibles datos sensibles:'); [print(f'- {x}') for x in findings]; return 2
 print('✅ Comprobación automática de privacidad superada.')
 print('⚠️ Esto no demuestra anonimato; revisa el contenido manualmente.')
 if not a.publish:
  print('\nModo revisión: no se ha publicado nada. Si decides continuar, añade --publish.')
  return 0
 try:
  subprocess.run(['gh','auth','status'],check=True,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,timeout=10)
 except Exception:
  print('No se ha detectado autenticación de GitHub CLI. Usa: gh auth login'); return 1
 target=a.path or f'results/metaLEONES/{path.name}'; encoded=base64.b64encode(path.read_bytes()).decode()
 try:
  subprocess.run(['gh','api',f'repos/{a.repo}/contents/{target}','--method','PUT','--field',f'message=metaLEONES: add {path.name}','--field',f'content={encoded}'],check=True,timeout=30)
 except (subprocess.SubprocessError,OSError) as exc:
  print(f'La publicación ha fallado: {exc}'); return 1
 url=f'https://github.com/{a.repo}/blob/main/{target}'
 print(f'\n🦁 Publicado: {url}\nSiguiente paso: conserva la URL y, si quieres, compártela con la Manada. Publicado ≠ verificado.')
 return 0
if __name__=='__main__': raise SystemExit(main())
