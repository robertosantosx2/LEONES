# LEONES RC4 — Especificación de elección, costes e instalación

**Estado:** 🔒 **FIJADO**  
**Fecha:** 2026-09-07  
**Ámbito:** selección de modelos, soluciones Personal AI / SOHO, costes, instalación y desinstalación  
**Regla:** LEONES informa, calcula y ejecuta la elección explícita del usuario; no decide por él qué solución instalar.

## 1. Principio rector

LEONES no tiene un componente canónico de despliegue impuesto al usuario.

El usuario decide independientemente:

1. para qué quiere usar la IA (`user_intent[]`);
2. qué modelo o modelos quiere utilizar;
3. qué solución quiere desplegar:
   - Asistente IA personal;
   - Servicio completo Small Office/Home Office (SOHO);
   - ambos.

Una recomendación automática puede reducir y ordenar opciones, pero **no equivale a elegir ni autoriza una instalación**.

```text
LEONES mide / observa
        ↓
LEONES informa
        ↓
LEONES propone opciones compatibles
        ↓
USUARIO ELIGE
  ├─ propósito(s)
  ├─ modelo(s)
  └─ solución(es)
        ↓
LEONES calcula impacto individual + conjunto
        ↓
LEONES informa costes y compatibilidad
        ↓
USUARIO CONFIRMA
        ↓
LEONES instala exactamente lo elegido
```

## 2. La máquina ya ha sido medida

RC4 no debe volver a introducir una herramienta de profiling como condición para seleccionar el LLM cuando ya existe medición válida del equipo.

ODS y Magnitude son **herramientas posibles**, no componentes canónicos obligatorios de LEONES.

Su eventual uso debe justificarse por una necesidad concreta de información/profiling/medición y no sustituye la evidencia física protocolizada de LEONES.

## 3. Selección múltiple de modelos

La selección de modelos es obligatoriamente múltiple: el usuario puede seleccionar uno, varios o cancelar.

Para cada modelo seleccionado LEONES debe mostrar, cuando esté disponible:

- nombre e identificador;
- runtime compatible;
- cuantización/formato;
- tamaño de artefacto en disco;
- RAM estimada en ejecución;
- VRAM estimada en ejecución, cuando aplique;
- carga CPU/GPU estimada, cuando pueda determinarse;
- contexto relevante;
- rendimiento externo/estimado claramente etiquetado;
- fuente y estado de evidencia.

Los datos desconocidos se presentan como `UNKNOWN`; nunca se inventan.

## 4. Impacto individual y conjunto

Antes de instalar, LEONES debe calcular dos vistas distintas.

### Individual

Para cada modelo:

```text
modelo
cuantización
artefacto en disco
RAM estimada
VRAM estimada
carga estimada
runtime/dependencias
```

### Conjunto

Para todos los modelos seleccionados:

```text
disco modelos
+ runtimes/dependencias necesarias
+ margen de seguridad
= espacio total requerido

RAM/carga simultánea
VRAM/carga simultánea
CPU/GPU
= carga conjunta según modo de ejecución
```

**No se debe sumar mecánicamente la RAM de modelos que se instalarán pero no estarán cargados simultáneamente.** La UI debe distinguir instalación, residencia y carga simultánea.

## 5. Gate de disco

Antes de confirmar la instalación se debe comprobar:

```text
disco libre actual
        ≥
modelos seleccionados
+ dependencias
+ runtime(s)
+ otros componentes seleccionados
+ margen de seguridad
```

Resultado explícito:

- `SUFICIENTE` → puede continuar;
- `INSUFICIENTE` → instalación bloqueada;
- `UNKNOWN` → no se afirma que quepa.

Si no cabe, LEONES no debe instalar parcialmente por defecto. Debe permitir modificar la selección o cancelar.

## 6. Soluciones de despliegue

### 6.1 Asistente IA personal

LEONES debe informar antes de instalar:

- componentes;
- funcionalidades;
- modelo(s) utilizados;
- runtime(s);
- espacio de disco;
- RAM en ejecución;
- VRAM, si aplica;
- CPU/GPU;
- servicios/procesos residentes;
- puertos, si aplica;
- dependencias;
- qué queda instalado;
- cómo se desinstala.

### 6.2 Servicio completo SOHO

LEONES debe informar antes de instalar:

- todos los componentes del servicio;
- funcionalidades de cada componente;
- modelos utilizados;
- runtimes;
- almacenamiento;
- servicios de red;
- procesos/daemons residentes;
- puertos;
- RAM/CPU/GPU/VRAM;
- espacio de disco;
- consumo individual y total;
- dependencias;
- qué queda instalado;
- cómo se desinstala.

### 6.3 Ambos

Cuando el usuario elige ambas soluciones, LEONES debe mostrar además:

- componentes compartidos;
- componentes duplicados;
- consumo adicional;
- consumo total;
- espacio total requerido;
- posibles conflictos de puertos/servicios;
- qué puede arrancarse simultáneamente.

## 7. Coste antes de instalar

El bloque de confirmación debe mostrar, como mínimo:

```text
+-- COSTE DE LA SELECCIÓN --------------------------+
| Modelos:                 <N>                      |
| Disco modelos:           <N / UNKNOWN>            |
| Dependencias/runtime:    <N / UNKNOWN>            |
| TOTAL DISCO:             <N / UNKNOWN>            |
| Disco disponible:        <N / UNKNOWN>            |
| Después de instalar:     <N / UNKNOWN>            |
| RAM en ejecución:        <N / UNKNOWN>            |
| VRAM en ejecución:       <N / UNKNOWN>            |
| CPU/GPU:                 <estimado/UNKNOWN>       |
| Residencia/daemon:       <detalle>                |
| Estado:                  SUFICIENTE/BLOQUEADO     |
+---------------------------------------------------+
```

Los costes son `ESTIMATED` salvo que hayan sido medidos específicamente en el host y exista evidencia `MEASURED` correspondiente.

## 8. Instalación

Instalar no es seleccionar.

Seleccionar no es consentir.

Consentir no es verificar.

Verificar no es medir.

La secuencia obligatoria es:

```text
SELECCIÓN
  ↓
CÁLCULO DE COSTES
  ↓
INFORMACIÓN
  ↓
CONFIRMACIÓN EXPLÍCITA
  ↓
INSTALACIÓN
  ↓
VERIFICACIÓN
  ↓
[opcional y con autorización separada]
MEDICIÓN
```

LEONES instala **exactamente** los modelos y soluciones confirmados. No añade modelos, runtimes o servicios por conveniencia sin informar y pedir confirmación cuando constituyan una nueva decisión/coste.

## 9. Desinstalación

Todo lo que LEONES ofrezca instalar debe tener camino de desinstalación.

La desinstalación debe indicar:

- qué se elimina;
- qué queda;
- espacio recuperado, si se conoce;
- servicios/daemons detenidos;
- datos/modelos conservados, si corresponde;
- cómo limpiar restos opcionales.

Nunca debe borrar automáticamente:

- evidencia histórica LEONES;
- mediciones validadas;
- perfiles de hardware;
- consentimientos/registro de decisiones;

salvo que el usuario solicite explícitamente esa limpieza como acción independiente.

## 10. Estados y honestidad

| Estado | Significado |
|---|---|
| `DECLARED` | dato declarado por usuario/fuente |
| `ESTIMATED` | estimación, ranking o coste orientativo |
| `OBSERVED` | observado en host/fuente sin constituir benchmark final |
| `MEASURED` | ejecución física protocolizada registrada por LEONES |
| `UNKNOWN` | no comprobado o no disponible |
| `BLOCKED` | no puede continuar sin resolver requisito |

Los benchmarks externos nunca se presentan como medición del equipo del usuario.

## 11. ODS / Magnitude

ODS y Magnitude quedan fuera de la decisión de qué LLM o solución debe escoger el usuario.

Si se evalúan o instalan, LEONES debe informar de cada uno como cualquier otro componente:

- función;
- utilidad concreta para LEONES;
- dependencias;
- tamaño en disco;
- RAM/residencia;
- impacto de instalación/actualización;
- compatibilidad;
- uninstall;
- relación con la medición existente.

La elección entre ODS y Magnitude, si ambos son válidos, también pertenece al usuario salvo que una decisión de arquitectura posterior y explícitamente documentada establezca otra cosa.

## 12. Criterio de cierre RC4 de esta capa

RC4 no se considera completo en esta dimensión hasta que exista:

1. catálogo de Personal AI y SOHO;
2. descripción de componentes y funcionalidades;
3. selección múltiple de modelos;
4. cálculo individual y conjunto de espacio;
5. cálculo de carga de ejecución individual y conjunta;
6. comprobación de espacio disponible;
7. bloqueo cuando no cabe o el dato crítico es `UNKNOWN`;
8. elección explícita Personal / SOHO / Ambos;
9. confirmación previa a instalación;
10. instalación exactamente de la selección confirmada;
11. verificación posterior;
12. uninstall equivalente;
13. separación estricta entre ESTIMATED / OBSERVED / MEASURED;
14. ODS/Magnitude tratados como opciones de tooling, no como selector canónico de producto.

## 13. Regla de memoria de proyecto

**Este fichero es la referencia normativa de RC4 para elección, costes e instalación.**

Antes de modificar la selección, catálogo, TUI, instalador, lifecycle, desinstalador o documentación/web relacionada con estas materias, debe leerse este documento y comprobarse que el cambio no contradice sus reglas.
