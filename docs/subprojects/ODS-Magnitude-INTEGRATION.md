# Integración ODS y Magnitude en LEONES

Estado: diseño de integración fijado; implementación por fases.

## 1. Principio arquitectónico

ODS y Magnitude son subproyectos externos fijados por commit. LEONES no copia ni modifica su código. Los adaptadores viven en LEONES.

LEONES observa y certifica; el subproyecto ejecuta su propia instalación, lifecycle y runtime.

## 2. Contrato común

Cada adaptador debe poder producir cuatro estados independientes:

- `preflight`: capacidad del host antes de instalar/ejecutar;
- `health`: estado del servicio/runtime;
- `evidence`: modelo, versión, runtime, backend, cuantización, procedencia y fecha;
- `benchmark`: medición independiente reproducible.

Ningún campo `estimated` se promociona automáticamente a `measured`.

## 3. ODS

### Responsabilidad de ODS

- instalación y actualización del stack;
- detección/configuración de hardware;
- modelos y runtimes;
- servicios y health;
- UI y componentes del stack.

### Responsabilidad del adaptador LEONES

1. detectar sistema operativo y arquitectura;
2. ejecutar preflight sin modificar el host;
3. registrar versión/commit de ODS utilizado;
4. recoger estado y health mediante interfaces públicas;
5. recoger identidad de modelo/runtime/backend/cuanti­zación cuando esté disponible;
6. producir recibo de instalación y procedencia;
7. ejecutar benchmark LEONES independiente;
8. almacenar evidencia sin alterar el catálogo por sí solo.

### Seguridad

El preflight no debe ejecutar comandos arbitrarios proporcionados por el usuario. La instalación debe usar una release/ref explícitamente fijada y registrar la fuente.

## 4. Magnitude

### Responsabilidad de Magnitude

- CLI y lifecycle del agente;
- perfilado de hardware;
- catálogo/configuración de modelos;
- inferencia y ejecución del agente.

### Responsabilidad del adaptador LEONES

1. comprobar plataforma soportada;
2. registrar versión/ref del CLI;
3. capturar configuración efectiva sin secretos;
4. capturar modelo/runtime/backend y cualquier cuantización explícita;
5. separar recomendaciones de Magnitude de mediciones propias;
6. ejecutar benchmark LEONES fuera de las estimaciones del agente;
7. conservar procedencia y timestamp.

## 5. Matriz de estados

| Capa | Resultado | Puede certificar |
|---|---|---|
| Preflight | PASS/FAIL | capacidad del host |
| Health | HEALTHY/DEGRADED/FAILED | estado operativo |
| Evidence | REPORTED/UNKNOWN | hechos observados |
| Benchmark | MEASURED/UNAVAILABLE | rendimiento medido |

Un resultado desconocido no se convierte en negativo ni positivo por inferencia.

## 6. CI

Los tests unitarios de adaptadores deben ejecutarse sin ODS/Magnitude instalados. Las pruebas E2E de runtime real son una fase separada y requieren hardware/software explícito.

## 7. Fases de implementación

### Fase A — contratos
- dataclasses/esquemas de preflight, health, evidence y benchmark;
- validación de invariantes;
- tests de estados y procedencia.

### Fase B — adaptadores
- `ods_adapter.py`;
- `magnitude_adapter.py`;
- detección segura de versiones y estados;
- normalización a formato LEONES.

### Fase C — benchmark
- comando independiente;
- captura de stdout/stderr;
- regex declarativa;
- hardware y runtime obligatorios para T3;
- conservación del resultado bruto.

### Fase D — E2E
- instalación limpia;
- health;
- modelo de prueba;
- benchmark;
- rollback/desinstalación.

### Fase E — documentación
- Debian/Ubuntu/Rocky/RHEL donde el proyecto soporte esas plataformas;
- privacidad;
- rollback;
- troubleshooting;
- límites de certificación.

## 8. Criterio de cierre

ODS y Magnitude no se consideran integrados hasta que existan adaptadores, tests unitarios, E2E reproducible y documentación. CI verde es necesario pero no suficiente.
