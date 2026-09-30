# llama.cpp expert paging PoC ↔ ODS ↔ LEONES
**Perfil:** PoC/discussion para paging de expertos MoE desde disco dentro del ecosistema llama.cpp.
**Estado LEONES:** 🟢 P1 estratégico · ⏳ no es backend estable.

## Resumen
La propuesta explora mantener un pool compacto de expertos y resolver bajo demanda los expertos seleccionados por el router, con LRU y lecturas desde almacenamiento. El interés para ODS es excepcional porque podría hacer innecesario mantener un runtime paralelo si una implementación suficientemente estable termina upstream.

## Arquitectura
`GGUF expert pool → router → expert IDs → CPU sidecar/index → pread → LRU → compute backend`.

## Encaje ODS
Debe seguirse como posible evolución del backend llama-server. ODS debería preferir capacidades upstream antes que forks permanentes.

## LEONES
Reproducir los escenarios publicados sobre el mismo hardware cuando sea posible. Medir RAM, VRAM, número de slots, bytes SSD, TTFT, prefill, decode y calidad.

## Riesgos
PoC, API cambiante, discusión comunitaria y resultados heterogéneos según plataforma. No tratar los comentarios como soporte oficial.

## Veredicto
**Clasificación:** P1 estratégico — vigilar y, si madura, priorizar frente a añadir otro runtime.
**Fuente:** https://github.com/ggml-org/llama.cpp/discussions/23324