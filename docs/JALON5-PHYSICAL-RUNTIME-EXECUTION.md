# JALÓN 5 — Ejecución física de runtimes

## Objetivo

Convertir la selección declarativa de JALÓN 4 en evidencia física comparable, sin modificar contratos ni seleccionar runtimes durante la prueba.

## Alcance operativo

### SOHO / workstation

1. `llama.cpp`
2. `ollama`
3. `AirLLM`
4. `FreeToken`

### CPD / servidor multiusuario

5. `vLLM`
6. `SGLang`

Los runtimes fuera de esta lista permanecen únicamente como conocimiento técnico de referencia.

## Regla de oro

Una estimación, benchmark externo o ficha del runtime nunca se convierte en medición local. Sólo una ejecución autorizada en el host produce evidencia `measured`.

## Orden de ejecución

`llama.cpp → ollama → AirLLM → FreeToken → vLLM → SGLang`

El orden minimiza variables: primero el runtime base ya probado físicamente, después SOHO local, y finalmente los servidores multiusuario.

## Contrato común de cada ejecución

Cada ejecución debe conservar:

- `execution_id` único;
- runtime, adapter y versión exacta;
- modelo, revisión y fuente;
- formato/cuanti­zación;
- contexto y protocolo de prompt;
- warm-up e iteraciones;
- TTFT;
- tiempo de generación;
- tokens/s;
- tiempo total;
- RAM pico;
- VRAM pico cuando exista;
- potencia cuando el host permita medirla;
- hardware y sistema operativo;
- comando o configuración efectiva;
- stdout/stderr íntegros;
- timestamp RFC3339;
- SHA-256 del artefacto del modelo;
- SHA-256 de la evidencia final.

## Comparabilidad

No se compararán cifras entre runtimes si cambia alguno de los siguientes elementos sin quedar explícitamente registrado: modelo/revisión, cuantización, contexto, protocolo, número de iteraciones, hardware, versión del runtime o configuración relevante.

## Política de Ubuntu

Hasta aquí todo es preparación verificable fuera del host físico. Ubuntu sólo debe intervenir para:

1. ejecutar `jalon4_preflight.py`;
2. comprobar las dependencias reales del host;
3. instalar o activar exclusivamente lo que el runtime necesite;
4. ejecutar cada benchmark;
5. conservar la evidencia generada.

El preflight no instala paquetes, no descarga modelos y no altera el sistema.

## Criterio de entrada a Ubuntu

Se considera preparado cuando CI esté verde y el host sólo tenga que ejecutar preflight → runtime → medición → evidencia.
