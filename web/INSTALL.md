# LEONES — preparación e instalación RC4

La distribución actual de LEONES **no es una instalación automática de toda la pila IA**. RC4 separa diagnóstico, recomendación, elección, consentimiento, instalación, verificación, autorización y medición.

## 1. Preparar el repositorio

```bash
git clone https://github.com/robertosantosx2/LEONES.git
cd LEONES
```

La ruta canónica actual es `main` y el lanzador RC4 es:

```bash
./leones
```

La compatibilidad histórica se mantiene explícitamente con:

```bash
./leones --rc2
```

## 2. Dependencias

La base del diagnóstico utiliza las herramientas que el repositorio comprueba. **LLMFit no es una dependencia dura de arranque**.

Si está disponible, `llmfit` puede alimentar el preselector RC4; si no lo está, LEONES no debe inventar candidatos ni hardware.

La presencia de otros componentes —runtimes, modelos locales, ODS, Magnitude, harnesses, agentes, etc.— se observa mediante el inventario y el preflight. No se da por instalada una herramienta porque aparezca en documentación.

## 3. Arrancar

```bash
./leones
```

La TUI RC4 comienza por idioma y después muestra el **Estado de la máquina**: hardware, RAM/CPU/disco y componentes IA detectados cuando están disponibles.

Después se declara `USER_INTENT[]` mediante selección múltiple. La recomendación no aparece antes de esa declaración.

## 4. Recomendación

El recorrido es:

```text
HARDWARE + USER_INTENT[]
        ↓
HF + Artificial Analysis
        ↓
feed ≤100
        ↓
LLMFit opcional · catálogo ≤100
        ↓
intersección
        ↓
hasta 3 ESTIMATED | insufficient
        ↓
elección humana
```

`ESTIMATED` no significa rendimiento medido.

## 5. Instalación y verificación

La instalación de un componente solo debe ocurrir después de la elección y el consentimiento explícitos. La vía de instalación debe ser reversible/desinstalable.

```text
RECOMENDACIÓN
   ↓
ELECCIÓN
   ↓
CONSENTIMIENTO
   ↓
INSTALACIÓN
   ↓
VERIFICACIÓN FÍSICA
```

Instalar no autoriza un benchmark.

## 6. Medición

La medición física requiere gates posteriores y autorización explícita:

```text
VERIFICADO
   ↓
AUTORIZAR EJECUCIÓN
   ↓
AUTORIZAR MEDICIÓN
   ↓
EJECUCIÓN PROTOCOLIZADA
   ↓
MEASURED + EVIDENCIA
```

La frontera física RC4 sigue abierta hasta completar la validación E2E en Ubuntu.

## 7. Reglas

- No se rellenan candidatos cuando faltan coincidencias.
- RAM y VRAM se contabilizan por separado.
- El swap no cuenta como RAM física.
- Una fuente externa no autoriza ejecución.
- Una preflight no equivale a instalación verificada.
- Una instalación verificada no equivale a benchmark.
- Un benchmark histórico no se reutiliza como medición universal.

## Desinstalación

Cualquier componente que LEONES instale debe conservar una vía de desinstalación explícita. La desinstalación no borra la evidencia histórica del proyecto.