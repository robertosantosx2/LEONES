# Nota de reconciliación para NEPENTHES-INDEX — Software P0

**Fecha:** 2026-11-20

Insertar / considerar en la sección **Orden de trabajo vigente** del INDEX:

> **Software P0 (importer) cerrado en main (2026-11-20):** decodificación dinámica de enums Nsight, preservación de sentinelas, correlación NVTX explícita y atribución `windowed` están integrados y testados en `scripts/nepenthes_nsys_import.py` + `tests/test_nepenthes_nsys_import.py`. Ver [NEPENTHES-SOFTWARE-P0-STATUS-20261120.md](NEPENTHES-SOFTWARE-P0-STATUS-20261120.md). Las ramas históricas `feat/nepenthes-nsys-enum-decode-20261119` y `feat/nepenthes-nsys-nvtx-correlation-20261119` están **obsoletas** respecto a main. No implica aceptación física batch ni C08.

En documentos auxiliares, enlazar también `NEPENTHES-SOFTWARE-P0-STATUS-20261120.md`.

Esta nota existe porque el INDEX maestro es grande; el cambio canónico de estado software ya está en ROADMAP + SOFTWARE-P0-STATUS. Al editar el INDEX en una PR posterior o localmente, incorporar el párrafo anterior bajo el punto 5 del orden de trabajo vigente.
