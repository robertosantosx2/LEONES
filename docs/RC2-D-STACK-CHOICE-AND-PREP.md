# RC2-D — Stack choice and preparation

**Status:** 🟢 contrato fijado / implementación inicial

RC2-D convierte la elección informada de stack en una preparación explícita, reversible y verificable. LEONES no instala silenciosamente ODS o Magnitude y no ejecuta un benchmark como efecto colateral de la instalación.

## 1. Punto de entrada

RC2-D recibe:

- hardware efectivo y procedencia;
- modelo seleccionado y cuantización;
- fit y estimaciones procedentes de LLMFit;
- decisión explícita del usuario sobre `ods` o `magnitude`;
- consentimiento separado para preparar/instalar;
- decisión independiente sobre benchmark.

## 2. Elección informada

Antes de pedir la elección, LEONES presenta las capacidades de cada alternativa usando la referencia disponible en su integración, no una descripción inventada por LEONES.

### ODS

ODS se presenta como stack local completo: inferencia, Open WebUI, dashboard, agentes, workflows, RAG/search, voz, generación de imágenes, gestión operativa y privacidad. Su instalador detecta hardware y puede seleccionar modelo/contexto; también admite configuraciones con backend externo. La disponibilidad concreta depende de plataforma y versión.

### Magnitude

Magnitude se presenta como infraestructura de inferencia local orientada a agentes: perfila hardware, recomienda modelos, descarga/ajusta/ejecuta modelos, gestiona carga bajo demanda y ofrece integración con distintos harnesses de agentes. Es open source, local/offline después de la descarga y soporta modelos compatibles fuera de su catálogo.

Las descripciones deben enlazar a la documentación oficial vigente cuando el usuario necesite verificar detalles.

## 3. Separación de decisiones

RC2-D mantiene cuatro decisiones independientes:

```text
modelo elegido
     ↓
stack elegido
     ↓
¿preparar/instalar?
     ↓
¿hacer benchmark?
```

Aceptar una no implica aceptar las siguientes.

## 4. Plan de preparación

La preparación genera un `ExecutionSpec`/plan declarativo antes de ejecutar efectos laterales. Debe incluir como mínimo:

- stack;
- modelo;
- cuantización, si aplica;
- plataforma/hardware efectivo;
- versión/ref objetivo;
- comandos o instalador previsto;
- requisitos;
- permisos requeridos;
- red necesaria;
- almacenamiento estimado;
- componentes que se instalarán;
- procedencia de cada dato;
- estado `planned`.

No debe contener secretos.

## 5. Gate de instalación

La instalación sólo puede comenzar si:

- existe selección válida;
- el stack está explícitamente elegido;
- el plan de preparación ha sido generado;
- los requisitos conocidos son compatibles;
- el usuario ha confirmado la instalación.

Si falta información, el estado es `blocked` o `needs_confirmation`, nunca `installed`.

## 6. Benchmark separado

La instalación/preparación no equivale a benchmark.

Si el usuario responde **No**:

```text
prepare/install → success → FIN
```

Si responde **Sí**:

```text
prepare/install
      ↓
benchmark authorization
      ↓
runtime execution
      ↓
measurement
      ↓
evidence
```

La medición de RC1 sigue siendo la referencia para distinguir estimación de ejecución real.

## 7. No duplicar funciones

No debe crear otro instalador de ODS ni otro instalador de Magnitude.

Tampoco debe tratar una recomendación o estimación de ODS/Magnitude como medición LEONES.

La responsabilidad de instalación pertenece al proyecto elegido; LEONES prepara, valida, solicita consentimiento, invoca la interfaz soportada y verifica el resultado.

## 8. Estados mínimos

```text
not_selected
selected
plan_ready
needs_confirmation
blocked
installing
installed
install_failed
benchmark_pending
benchmark_authorized
```

Las transiciones deben ser explícitas y trazables.

## 9. Definition of Done RC2-D

- [x] Capacidades ODS/Magnitude expuestas antes de la elección.
- [x] Elección de stack separada de elección de modelo.
- [x] Instalación separada de benchmark.
- [x] Plan declarativo previo a efectos laterales.
- [x] No se inventa un instalador paralelo.
- [x] No se promocionan estimaciones a mediciones.
- [ ] Adaptadores de instalación reales para cada stack.
- [ ] Verificación real de instalación en hardware compatible.
- [ ] UI/CLI beta que ejecute el recorrido completo.

**RC2-D queda contractualmente fijado; las dos últimas capas requieren integración real y se validarán en fases posteriores.**
