#!/usr/bin/env python3
"""🦁 LEONES runtime — comprueba si ya existe un servicio local utilizable.

ANTES: explica que solo comprobará URLs locales; no instala, descarga, inicia
servicios ni envía prompts a Internet.
DURANTE: hace una petición HTTP simple a cada URL indicada.
DESPUÉS: indica qué endpoint responde y propone `infer` si alguno está vivo.
Que responda un endpoint NO demuestra que el modelo rinda bien.

Ejemplo: python3 scripts/leones-runtime.py --url http://127.0.0.1:8080/v1/models
"""
from __future__ import annotations
import argparse,json,time,urllib.error,urllib.request

def check(url:str,timeout:float)->dict:
 started=time.perf_counter()
 try:
  req=urllib.request.Request(url,headers={'Accept':'application/json'})
  with urllib.request.urlopen(req,timeout=timeout) as r:r.read(4096)
  return {'url':url,'reachable':True,'http_status':r.status,'elapsed_seconds':round(time.perf_counter()-started,3)}
 except (urllib.error.URLError,TimeoutError,OSError) as exc:
  return {'url':url,'reachable':False,'error':str(exc),'elapsed_seconds':round(time.perf_counter()-started,3)}

def main()->int:
 p=argparse.ArgumentParser(description='Comprueba un runtime local sin instalar ni ejecutar modelos')
 p.add_argument('--url',action='append',help='URL local a comprobar; puede repetirse')
 p.add_argument('--timeout',type=float,default=5);p.add_argument('--explain',action='store_true')
 a=p.parse_args();urls=a.url or ['http://127.0.0.1:8080/v1/models','http://127.0.0.1:11434/api/tags']
 print('🦁 LEONES · Runtime\nAntes: comprobaremos únicamente endpoints locales. No se instalará nada ni se enviarán prompts.\nDurante: una petición HTTP por URL.\n')
 results=[check(u,a.timeout) for u in urls];reachable=[r for r in results if r['reachable']]
 out={'schema_version':'1.0','tool':'leones-runtime','tool_version':'1.1','status':'ok' if reachable else 'no_runtime','endpoints':results,'next_step':'infer' if reachable else 'runtime setup'}
 print(json.dumps(out,indent=2,ensure_ascii=False));print('\nDespués: '+('hay un endpoint alcanzable; siguiente paso: infer.' if reachable else 'no hay endpoint alcanzable; primero necesitas configurar un runtime local.'))
 return 0 if reachable else 2
if __name__=='__main__':raise SystemExit(main())
