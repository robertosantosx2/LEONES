# LEONES RC2 — Manual de usuario beta

**Estado:** 🟡 RC2-B → RC2-H en validación física  
**Público:** beta testers  
**Predecesor:** RC1 validado

> RC2 es una beta física. El objetivo es comprobar que un usuario externo puede completar el recorrido sin conocer la arquitectura interna de LEONES.

## 1. Qué hace RC2

RC2 convierte la cadena validada en RC1 en un recorrido guiado:

```text
HARDWARE → PERFILADO → CANDIDATOS → ELEGIR MODELO
                                      ↓
                              ODS / MAGNITUDE
                                      ↓
                                ELEGIR STACK
                                      ↓
                              CONSENTIMIENTO
                                      ↓
                             INSTALAR / VERIFICAR
                                      ↓
                              ¿BENCHMARK REAL?
                               ↙             ↘
                             NO               SÍ
                             ↓                 ↓
                            FIN       RUNNER RC1 → EVIDENCIA
```

**Estimado ≠ medido.** La elección de un modelo o stack no ejecuta por sí sola un benchmark.

## 2. Antes de empezar

Necesitas una máquina compatible con la versión/ref que estés probando, una terminal, Git, Python compatible y conexión a Internet cuando el stack elegido necesite descargas.

El procedimiento técnico completo está en el [Manual de instalación de RC2](RC2-INSTALLATION-MANUAL.md).

## 3. Ejecutar LEONES

Desde el repositorio:

```bash
source .venv/bin/activate
python scripts/rc2_wizard.py
```

Si la instalación de la beta todavía no ha creado el entorno virtual, sigue primero el [Manual de instalación de RC2](RC2-INSTALLATION-MANUAL.md).

## 4. Hardware y candidatos

LEONES obtiene el hardware disponible y utiliza **LLMFit como fuente especializada de inteligencia hardware/model-fit**.

Los datos observados deben conservar su procedencia. Si un dato no está disponible, debe permanecer desconocido (`null`/`unknown`) en vez de inventarse.

Los candidatos pueden mostrar una velocidad aproximada procedente de LLMFit:

```text
fit=Perfect · ~28.2 tok/s · llmfit · ESTIMATED
```

Esa cifra es una **estimación**. No es una medición de tu máquina.

## 5. Elegir modelo

La recomendación ayuda a decidir, pero la elección final es tuya.

Al comparar candidatos, revisa:

- modelo y variante;
- cuantización;
- memoria requerida/disponible;
- runtime;
- `fit`;
- procedencia;
- `estimated` frente a `measured`.

## 6. Elegir ODS o Magnitude

LEONES debe mostrar las funcionalidades disponibles para la versión/ref concreta antes de pedirte que elijas.

### ODS
Integración orientada al stack local y a la ejecución local, según la versión/ref utilizada.

### Magnitude
Integración orientada a agente/asistente y ejecución local, según la versión/ref utilizada.

Las capacidades no verificadas no deben presentarse como garantizadas.

**LEONES no crea un instalador paralelo de ODS ni de Magnitude.** Utiliza las interfaces y proyectos canónicos del stack elegido.

## 7. Consentimiento

Después de elegir el stack aparece una autorización separada para las operaciones que puedan producir efectos laterales.

Lee el plan antes de aceptar. **Cancelar es una salida válida.**

La autorización de instalación no autoriza automáticamente el benchmark.

## 8. Instalación: saber que sigue trabajando

Una instalación puede tardar. LEONES debe mostrar siempre actividad visible durante operaciones largas.

El indicador de progreso representa **fases del flujo de LEONES**, no un porcentaje interno inventado del instalador externo.

Ejemplo:

```text
[  0%] Preparando instalación ODS
[ 10%] Conectando con el instalador oficial
[ 20%] Descargando bootstrap ODS
[ 35%] Instalando ODS ... /
[ 35%] Instalando ODS ... -
[ 35%] Instalando ODS ... \
[ 35%] Instalando ODS ... |
[ 85%] Ejecutando health check
[100%] Instalación ODS verificada
```

Si la operación externa no ofrece progreso real, **no se debe fingir un porcentaje de descarga**. Se muestra una fase estable más un indicador de actividad.

## 9. Verificación

Una instalación aceptada todavía no equivale a una instalación válida.

El flujo debe llegar a:

```text
INSTALLING → VERIFY → INSTALL_VERIFIED
```

Si termina en `INSTALL_FAILED` o `BLOCKED`, no continúes al benchmark.

## 10. Benchmark real

LEONES pregunta explícitamente si quieres medir la combinación en tu equipo.

### NO
Termina el recorrido sin benchmark.

### SÍ
Se autoriza el benchmark concreto y se reutiliza el **runner canónico de RC1**. RC2 no crea un runner paralelo.

Una ejecución real debe producir evidencia nueva y conservar, cuando corresponda:

- `execution_id`;
- modelo/variante;
- runtime y versión/ref;
- hardware;
- protocolo;
- timestamps;
- métricas;
- resultado;
- procedencia y artefactos.

## 11. Cómo interpretar los resultados

```text
ESTIMATED  ≠  MEASURED
HISTÓRICO  ≠  ACTUAL
INSTALADO  ≠  BENCHMARK AUTORIZADO
```

Una cifra histórica o procedente de LLMFit no sustituye una ejecución actual.

## 12. Si algo falla

No ocultes el error. Conserva el mensaje original y anota:

```text
LEONES ref:
SO / arquitectura:
CPU / RAM / GPU / VRAM:
Modelo:
Stack: ODS | Magnitude
Etapa: PREFLIGHT | INSTALL | VERIFY | BENCHMARK | EVIDENCE
Comando:
Error original:
Resultado esperado:
Resultado obtenido:
execution_id (si existe):
```

Un fallo de instalación o conectividad también es evidencia útil para el piloto.

## 13. Privacidad

No compartas contraseñas, API keys, tokens ni datos privados en logs o incidencias. La contribución de resultados al conocimiento colectivo es voluntaria.

## 14. Criterio de éxito de RC2

RC2 avanzará hacia cierre cuando un beta tester externo pueda completar de forma reproducible:

```text
hardware
 → candidatos
 → modelo
 → ODS/Magnitude
 → stack
 → consentimiento
 → instalación
 → verificación
 → benchmark opcional
 → medición
 → evidencia
```

El [flujo contractual RC2](RC2-BETA-USER-FLOW.md) contiene los gates y estados detallados.
