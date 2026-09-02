# LEONES — instalación mínima

La instalación beta debe ser pequeña: **Git + Python 3.10+ + LLMFit**. LEONES no instala automáticamente ODS, Magnitude ni modelos.

## 0. Dependencia externa obligatoria: LLMFit

**LLMFit es una dependencia dura de LEONES.**

- Detecta hardware (CPU/RAM/GPU/VRAM).
- Propone candidatos de modelo y ajuste (fit).
- Sus cifras de velocidad son **ESTIMATED**, no mediciones LEONES.

LEONES **no instala ni sustituye** LLMFit. Debe estar en el `PATH` como comando `llmfit` antes de `./install.sh`.

### Instalar LLMFit (Linux / Fedora)

Opción recomendada (script oficial, sin sudo):

```bash
curl -fsSL https://llmfit.axjns.dev/install.sh | sh -s -- --local
```

Añade `~/.local/bin` al PATH si aún no lo está:

```bash
echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.bashrc
source ~/.bashrc
```

Otras opciones válidas:

```bash
# Con Homebrew (si lo usas en Linux)
brew install llmfit
# o
brew install AlexsJones/llmfit/llmfit

# Con uv
uv tool install -U llmfit
```

Comprueba:

```bash
llmfit --version
# o al menos:
command -v llmfit
```

Documentación oficial: https://www.llmfit.org/  
Repositorio: https://github.com/AlexsJones/llmfit

## 1. Descargar LEONES

```bash
git clone https://github.com/robertosantosx2/LEONES.git
cd LEONES
```

## 2. Preparar

```bash
./install.sh
```

El instalador comprueba Python, Git y LLMFit y deja preparado el lanzador `./leones`. No crea un entorno virtual ni descarga modelos.

Si LLMFit no está instalado, `./install.sh` falla de forma explícita y te indica que lo instales primero.

## 3. Ejecutar

```bash
./leones
```

El lanzador abre el wizard RC2. Si LLMFit no está disponible, LEONES se bloquea explícitamente y no inventa hardware ni candidatos.

## 4. Después

El wizard guía:

```text
HARDWARE → CANDIDATOS → MODELO → ODS/MAGNITUDE
        → CONSENTIMIENTO → INSTALAR/VERIFICAR
        → BENCHMARK OPCIONAL → EVIDENCIA
```

La instalación de ODS/Magnitude sólo se ejecuta después del consentimiento y mediante sus interfaces canónicas.

## 5. Runtime de contenedores para ODS

LEONES RC2 ya no presupone que Docker sea **rootless**.

La política es:

```text
CONTENEDORES
├── Docker directo             → válido
├── Docker mediante sudo       → válido
├── Docker rootless            → válido
└── Podman                     → detectado explícitamente
```

Un Docker rootful accesible mediante `sudo docker` **no es un error**. LEONES pasa al instalador ODS el estado ya observado para evitar que el instalador intente adivinar incorrectamente el modo rootless.

En Fedora/RHEL y derivados, si el equipo sólo dispone de Podman, LEONES lo detecta y lo informa. El ODS actual usa un contrato Docker + Compose; por tanto LEONES **no instala Docker silenciosamente ni declara Podman como ODS compatible sin verificar una interfaz Docker-compatible**. Esto evita sustituir la elección de runtime del sistema sin consentimiento.

La comprobación previa de ODS expone además:

- runtime detectado;
- acceso directo o mediante `sudo`;
- modo rootless/rootful cuando puede determinarse;
- Compose disponible;
- presencia de Podman;
- compatibilidad efectiva con el contrato de instalación de ODS.

## 6. Comprobación física

La verificación física de ODS es posterior a la instalación. Sólo puede producir `PASS` cuando se observa realmente el toolchain y una señal específica de ODS (CLI o imagen local). Un Docker operativo por sí solo **no equivale a ODS instalado**.

Por tanto:

```text
Docker/Podman detectado
        ↓
interfaz compatible con ODS
        ↓
instalación autorizada
        ↓
verificación física
        ↓
PASS → benchmark
FAIL → reparar / volver a verificar
```

## Requisitos

- Linux para la validación RC2 actual.
- Git.
- Python 3.10 o superior.
- **LLMFit instalado y accesible como `llmfit` en el PATH.**
- Internet cuando el flujo elegido necesite descargar componentes.

## Regla de distribución

El usuario beta necesita únicamente:

1. el repositorio GitHub;
2. `install.sh`;
3. `leones`;
4. este `INSTALL.md`;
5. la documentación RC2 enlazada desde el README.

El resto del repositorio es implementación, contratos, pruebas y evidencia; no forma parte de las instrucciones de instalación.
