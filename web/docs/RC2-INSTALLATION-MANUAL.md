# LEONES RC2 — Manual de instalación

**Estado:** RC2 en preparación / piloto beta  
**Público:** beta testers  
**Predecesor:** RC1 validado

> RC2 es una fase beta. El objetivo es validar el recorrido completo en máquinas externas. No se debe interpretar una estimación como una medición ni una instalación como autorización de benchmark.

## 1. Qué vas a hacer

El recorrido previsto es:

```text
INSTALAR LEONES
      ↓
PREFLIGHT
      ↓
HARDWARE
      ↓
PERFILADO
      ↓
MODELOS CANDIDATOS
      ↓
ELEGIR MODELO
      ↓
CONOCER ODS / MAGNITUDE
      ↓
ELEGIR STACK
      ↓
CONSENTIR INSTALACIÓN
      ↓
INSTALAR / VERIFICAR
      ↓
RESOLVER MODELO → RUNTIME
      ↓
PREFLIGHT RUNTIME / ARTEFACTO
      ↓
¿BENCHMARK A01?
      ↓
   SÍ → RUNNER RC1 → MEDICIÓN → EVIDENCIA
   NO → FIN
```

El benchmark siempre es opcional.

## 2. Requisitos iniciales

RC2 se está validando inicialmente sobre Linux. Antes de empezar necesitas:

- conexión a Internet para descargar el repositorio y los componentes que el stack elegido requiera;
- una terminal;
- Git;
- Python 3.10 o superior;
- **LLMFit instalado y accesible como `llmfit` en el PATH** (dependencia dura externa; LEONES no lo instala);
- espacio suficiente para el repositorio, dependencias, modelos y componentes que finalmente aceptes instalar;
- permisos suficientes para las operaciones que el plan de instalación indique.

### 2.1 Instalar LLMFit

```bash
curl -fsSL https://llmfit.axjns.dev/install.sh | sh -s -- --local
export PATH="$HOME/.local/bin:$PATH"
command -v llmfit
```

Alternativas: `brew install llmfit` o `uv tool install -U llmfit`.

Documentación oficial: https://www.llmfit.org/ · https://github.com/AlexsJones/llmfit

**No asumas que ODS y Magnitude tienen los mismos requisitos.** LEONES debe mostrar los requisitos del stack y de la versión/ref concretos antes del consentimiento.

## 3. Obtener LEONES

```bash
git clone https://github.com/robertosantosx2/LEONES.git
cd LEONES
```

Si ya tienes un clon:

```bash
cd LEONES
git pull --ff-only origin main
```

## 4. Preflight

```bash
python3 --version
git --version
command -v llmfit
./install.sh
```

## 5. Iniciar el recorrido RC2

```bash
./leones
```

## 6–18

Sigue el mismo contrato que el manual canónico en `docs/RC2-INSTALLATION-MANUAL.md`: hardware observado, candidatos ESTIMATED, elección de stack, consentimiento, verificación física, resolución modelo→runtime, A01 opcional, evidencia y no inventar MEASURED.
