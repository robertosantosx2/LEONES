# tandem.cpp — instantánea preservada del código fuente

Este directorio conserva el repositorio upstream `ewhacc/tandem.cpp` tal como existía en el commit fijado a continuación.

- Upstream: https://github.com/ewhacc/tandem.cpp
- Commit upstream: `e1acb8877bfcf92b4ae7c9f0e0f1d896dbf6c683`
- Fecha de la instantánea: 2026-11-03
- Commit base upstream de llama.cpp: `f5222f25c` (véase `BASE_COMMIT`)
- Licencia upstream: `LICENSE` (MIT)
- Implementación principal: `tandem.patch`
- Ayudante de compilación: `build.sh`

## Notas de preservación

Este directorio es una instantánea del código fuente, no un submódulo Git. Los archivos fuente y el parche se conservan de forma independiente del historial upstream. El commit fijado es la referencia de procedencia; compáralo con upstream antes de actualizarlo.

## Alcance

El proyecto es un conjunto de parches que se aplica a una revisión concreta de llama.cpp. No es un motor de inferencia independiente y debe compilarse en un worktree aislado. El mero hecho de archivar este código fuente no implica que se haya ejecutado ningún benchmark en el MSI de LEONES.

## NEPENTHES

Documentación y evidencias de NEPENTHES:
- [Índice y estado de validación](NEPENTHES-INDEX.md)
- [Roadmap de implementación y criterios de aceptación](NEPENTHES-ROADMAP.md)
- [Contrato del importador Nsight/CUPTI y validación real en MSI](NEPENTHES-IMPORTER.md)
- [Instalador, CLI y paquete de captura](NEPENTHES-CLI.md)
- [Informe de captura histórica Qwen3.5-35B](NEPENTHES-QWEN35-HISTORICAL-REPORT-20261115.md)
- [Campañas de validación y experimentación](NEPENTHES-CAMPAIGNS.md)

## Versiones lingüísticas

El español es el original y la fuente de verdad. La traducción inglesa mantiene la misma estructura y las mismas rutas de documentos en la rama [docs/nepenthes-quickstart-index-20261115-en](https://github.com/robertosantosx2/LEONES/tree/docs/nepenthes-quickstart-index-20261115-en). Esta rama contiene los documentos originales en español: [docs/nepenthes-quickstart-index-20261115](https://github.com/robertosantosx2/LEONES/tree/docs/nepenthes-quickstart-index-20261115).

El runtime instrumentado y el sink JSONL universal se desarrollan en [Tandem.cpp PR #1](https://github.com/robertosantosx2/tandem.cpp/pull/1). La integración en LEONES se sigue en [PR #150](https://github.com/robertosantosx2/LEONES/pull/150), [#151](https://github.com/robertosantosx2/LEONES/pull/151), [#152](https://github.com/robertosantosx2/LEONES/pull/152) y [#153](https://github.com/robertosantosx2/LEONES/pull/153).
