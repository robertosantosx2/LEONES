# LEONES — instalación mínima RC3

RC3 fija el arranque en capas: **Hermes descubre**, **Oh My Hermes organiza**, **LEONES verifica y mide**. LEONES ya no exige LLMFit/FitLLM para instalarse o arrancar.

## 1. Descargar e instalar LEONES

```bash
git clone https://github.com/robertosantosx2/LEONES.git
cd LEONES
./install.sh
```

El instalador de LEONES prepara automáticamente las dos primeras capas externas del RC3:

1. Hermes, mediante su instalador oficial.
2. Oh My Hermes (OMH), mediante su instalador oficial y `omh setup`.

No se instala una copia alternativa ni un wrapper propio de ninguno de los dos proyectos.

## 2. Hermes — descubrimiento y selección inicial

Hermes es el primer componente externo del flujo RC3 porque aporta descubrimiento de hardware y fit inicial de modelos locales.

Instalación oficial para Linux/macOS/WSL2:

```bash
curl -fsSL https://hermes-agent.nousresearch.com/install.sh | bash
```

Verificación:

```bash
hermes --version
hermes doctor
```

Hermes también dispone de Desktop para Linux, Windows y macOS. Su flujo Local Models gestiona `llama.cpp`, selecciona builds adecuados al hardware y comprueba memoria/contexto antes de descargar. citeturn0search0turn19file0L2-L2

**Nota:** el instalador de LEONES no duplica el instalador oficial de Hermes. Si Hermes ya está presente, LEONES lo reutiliza.

## 3. Oh My Hermes — capa de operación

Después de Hermes se instala **Oh My Hermes (OMH)**, la capa de operación sobre Hermes. OMH no sustituye Hermes: añade routing de workflows, capacidades, handoffs, memoria y límites explícitos entre preparación, observación y verificación. citeturn0search1turn0search6

Instalación oficial para Linux/macOS:

```bash
curl -fsSL https://raw.githubusercontent.com/rlaope/oh-my-hermes/main/install.sh | OMH_CHANNEL=stable sh
omh setup
omh doctor
```

LEONES ejecuta `omh setup` durante `./install.sh` para dejar OMH conectado a Hermes. La comprobación independiente `omh doctor` queda disponible para diagnóstico posterior. La documentación de OMH mantiene explícitamente separados `setup` y `doctor`. citeturn0search1

Si OMH ya está instalado, LEONES no lo reinstala; vuelve a ejecutar `omh setup` para asegurar la configuración gestionada.

## 4. Flujo RC3

```text
LEONES install
      ↓
HERMES DISCOVERY
      ↓
hardware-profile.v1
      ↓
OH MY HERMES
routing / workflow / handoff / evidence gates
      ↓
LEONES NORMALIZA
      ↓
candidate-set.v1
      ↓
ELEGIR MODELO / CONFIGURACIÓN
      ↓
┌─────────────────┬─────────────────┐
│ MAGNITUDE       │ ODS             │
│ profiling/tuning│ install/stack   │
└────────┬────────┴────────┬────────┘
         └─────────┬───────┘
                   ↓
            runtime elegido
                   ↓
             TAREAS LEONES
                   ↓
               MEDICIÓN
                   ↓
               EVIDENCIA
```

## 5. Magnitude u ODS

El usuario elige el camino después del descubrimiento y la normalización:

### Magnitude

Hermes entrega el perfil y la configuración inicial; OMH puede preparar el workflow/handoff; LEONES realiza el handoff al flujo canónico de Magnitude para perfilado, tuning y ejecución.

### ODS

Hermes entrega el perfil y la configuración inicial; OMH puede preparar el workflow/handoff; LEONES realiza el handoff al instalador/stack canónico de ODS.

LEONES **no crea otro instalador de Magnitude ni otro instalador de ODS**.

## 6. FitLLM / LLMFit

**Fuera de RC3.**

LLMFit/FitLLM ya no es dependencia dura, no se instala y no bloquea `./install.sh` ni `./leones`.

La integración histórica queda documentada únicamente para trazabilidad de RC2. Podrá volver como `CandidateProvider` opcional en una release futura, pero no forma parte del camino RC3.

## 7. Autoridad y evidencia

Hermes puede descubrir hardware y proponer una configuración compatible. OMH puede organizar el workflow y los handoffs. Ninguno de los dos sustituye la medición física de LEONES.

LEONES conserva el control de:

- verificación física del hardware crítico;
- ejecución de tareas;
- medición de latencia/throughput y métricas de tarea;
- `execution_id` y timestamps;
- evidencia reproducible;
- recomendación final.

Por tanto:

> **Hermes descubre → OMH organiza → usuario elige → Magnitude/ODS ejecuta → LEONES mide y sentencia.**

## 8. Gate físico RC3

La integración queda pendiente de validación física hasta probar una máquina real no previamente descrita al flujo:

```text
máquina desconocida
      ↓
Hermes discovery
      ↓
OMH workflow / handoff
      ↓
LEONES cross-check
      ↓
modelo/configuración
      ↓
Magnitude u ODS
      ↓
tarea real
      ↓
measured
      ↓
evidence
```

Una discrepancia entre Hermes y las sondas de LEONES no se convierte automáticamente en PASS: debe quedar como conflicto o requerir nueva verificación.

## Referencias oficiales

- urlOh My Hermes — repositorio oficialhttps://github.com/rlaope/oh-my-hermes
- urlOh My Hermes — documentación/web oficialhttps://rlaope.github.io/oh-my-hermes/
