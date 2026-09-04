# LEONES — instalación mínima RC3

RC3 cambia el orden de arranque: **Hermes es el bootstrap de descubrimiento**. LEONES ya no exige LLMFit/FitLLM para instalarse o arrancar.

## 1. Descargar LEONES

```bash
git clone https://github.com/robertosantosx2/LEONES.git
cd LEONES
./install.sh
```

## 2. Verificar / instalar Hermes

Hermes es el primer componente externo del flujo RC3 porque aporta el descubrimiento y fit inicial de modelos locales.

Instalación oficial para Linux/macOS/WSL2:

```bash
curl -fsSL https://hermes-agent.nousresearch.com/install.sh | bash
```

Después:

```bash
hermes --version
hermes doctor
```

Hermes también dispone de Desktop para Linux, Windows y macOS. Su flujo Local Models gestiona `llama.cpp`, selecciona builds adecuados al hardware y comprueba memoria/contexto antes de descargar. citeturn0search0turn19file0L2-L2

**Nota:** el instalador de LEONES no debe duplicar el instalador oficial de Hermes. La integración debe invocar el componente canónico y conservar su versión/ref.

## 3. Flujo RC3

```text
LEONES
  ↓
HERMES DISCOVERY
  ↓
hardware-profile.v1
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

## 4. Magnitude u ODS

El usuario elige el camino después del descubrimiento:

### Magnitude

Hermes entrega el perfil y la configuración inicial; LEONES realiza el handoff al flujo canónico de Magnitude para perfilado/tuning/ejecución.

### ODS

Hermes entrega el perfil y la configuración inicial; LEONES realiza el handoff al instalador/stack canónico de ODS.

LEONES **no crea otro instalador de Magnitude ni otro instalador de ODS**.

## 5. FitLLM / LLMFit

**Fuera de RC3.**

LLMFit/FitLLM ya no es dependencia dura, no se instala y no bloquea `./install.sh` ni `./leones`.

La integración histórica queda documentada únicamente para trazabilidad de RC2. Podrá volver como `CandidateProvider` opcional en una release futura, pero no forma parte del camino RC3.

## 6. Autoridad y evidencia

Hermes puede decir qué hardware observa y qué configuración parece compatible. Eso es **discovery / fit**, no evidencia física LEONES.

LEONES conserva el control de:

- verificación física del hardware crítico;
- ejecución de tareas;
- medición de latencia/throughput y métricas de tarea;
- `execution_id` y timestamps;
- evidencia reproducible;
- recomendación final.

Por tanto:

> **Hermes descubre → usuario elige → Magnitude/ODS ejecuta → LEONES mide.**

## 7. Gate físico RC3

La implementación queda pendiente de validación física hasta probar una máquina real no previamente descrita al flujo:

```text
máquina desconocida
      ↓
Hermes discovery
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
