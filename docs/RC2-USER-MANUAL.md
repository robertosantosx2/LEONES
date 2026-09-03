# LEONES RC2 — Manual de usuario beta

**Estado:** 🟡 RC2 en validación física  
**Público:** beta testers  
**Operador canónico:** `./leones`

> RC2 es una beta física. El objetivo es comprobar que un usuario externo puede completar el recorrido sin conocer la arquitectura interna de LEONES.

## 1. Qué hace RC2

```text
IDIOMA → HARDWARE → CANDIDATOS → MODELO → STACK
                                      ↓
                              CONSENTIMIENTO
                                      ↓
                         INSTALAR / VERIFICAR STACK
                                      ↓
                         RESOLVER MODELO → RUNTIME
                                      ↓
                              ¿BENCHMARK A01?
                               ↙             ↘
                             NO               SÍ
                             ↓                 ↓
                            FIN       RUNNER RC1 → EVIDENCIA
```

**Estimado ≠ medido.** Elegir modelo o stack no ejecuta un benchmark.

## 2. Antes de empezar

- Git, Python, terminal Linux
- **LLMFit** en PATH (dependencia dura de `./install.sh`)
- Internet si el stack o el runtime necesitan descargas

Procedimiento técnico: [Manual de instalación RC2](RC2-INSTALLATION-MANUAL.md).

## 3. Ejecutar LEONES

```bash
./install.sh
./leones
```

Primera pregunta: **idioma** (Español / English / 中文). El resto del wizard usa solo ese idioma.

## 4. Hardware y candidatos

LLMFit aporta hardware y candidatos. Las velocidades que veas son **ESTIMATED**, no mediciones de tu máquina.

## 5. Elegir modelo y stack

La elección es tuya. El menú de stack incluye una descripción breve de ODS y Magnitude.

## 6. Consentimiento e instalación

Autorizar instalación ≠ instalar automáticamente. Tras autorizar verás el comando canónico y podrás ejecutarlo ahora o más tarde. Cancelar es válido.

## 7. Verificación física del stack

LEONES **observa el host**. Un instalador con código 0 no basta. Sin PASS de verificación no hay benchmark.

## 8. Resolución modelo → runtime

Antes de A01, LEONES resuelve de forma declarativa qué runtime corresponde al modelo (p. ej. Ollama-managed vs GGUF→llama.cpp). **No convierte un id de Hugging Face en un modelo Ollama.**

Si el runtime o el artefacto no están disponibles, el benchmark queda **bloqueado** (no se inventa MEASURED).

## 9. Benchmark A01

Pregunta explícita. Si dices que no, la instalación sigue válida y no se mide nada.

Si dices que sí y el preflight pasa, se usa el **runner RC1** (`a01_runtime_benchmark.py`) con el puente del runtime resuelto.

## 10. Cómo interpretar resultados

```text
ESTIMATED  ≠  MEASURED
HISTÓRICO  ≠  ACTUAL
INSTALADO  ≠  VERIFICADO  ≠  BENCHMARK AUTORIZADO
```

## 11. Si algo falla

Conserva el mensaje original:

```text
Etapa: PREFLIGHT | INSTALL | VERIFY | RESOLVE | BENCHMARK | EVIDENCE
Comando:
Error original:
execution_id (si existe):
```

## 12. Criterio de éxito

Un beta tester externo completa de forma reproducible el recorrido hasta evidencia o hasta un bloqueo honesto cuando falta runtime/artefacto.
