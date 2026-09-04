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

Desde la terminal:

```bash
git clone https://github.com/robertosantosx2/LEONES.git
cd LEONES
```

Si ya tienes un clon:

```bash
cd LEONES
git pull --ff-only origin main
```

Conserva la referencia Git que has probado. Un beta tester debe poder indicar posteriormente qué versión ejecutó.

## 4. Preflight

Comprueba primero el entorno sin instalar todavía un stack de inferencia:

```bash
python3 --version
git --version
command -v llmfit
uname -a
```

Después ejecuta:

```bash
./install.sh
```

Si LEONES informa de una dependencia ausente, **no la sustituyas silenciosamente**: registra el mensaje y sigue las instrucciones correspondientes (en particular, instalar LLMFit si falta).

## 5. Iniciar el recorrido RC2

El punto de entrada del beta tester es:

```bash
./leones
```

Equivalente interno (no necesario en el camino mínimo):

```bash
python3 scripts/rc2_wizard.py
```

La interfaz utiliza ASCII para hacer visibles las decisiones y sus consecuencias.

## 6. Declarar o comprobar el hardware

El objetivo es obtener, como mínimo:

- sistema operativo;
- arquitectura;
- CPU;
- RAM;
- GPU;
- VRAM;
- drivers/aceleración;
- almacenamiento relevante.

Cuando un dato no pueda determinarse, debe quedar como `unknown`/`null`; no inventes valores.

LLMFit es la fuente especializada de inteligencia hardware/model-fit de LEONES. LEONES consume y normaliza su salida; no sustituye sus heurísticas por otro sistema paralelo.

## 7. Revisar candidatos y elegir modelo

LEONES debe presentar candidatos con el contexto disponible:

- modelo;
- variante/cuanti;
- requisitos;
- runtime;
- fundamento de la recomendación;
- evidencia existente;
- diferencia entre `estimated` y `measured`.

La recomendación no sustituye la decisión del beta tester.

## 8. ODS frente a Magnitude

**Antes de elegir**, lee las funcionalidades que LEONES presente para la versión/ref concreta.

Como orientación, la integración puede exponer capacidades como:

### ODS
- inferencia local;
- Open WebUI;
- gateway;
- RAG/search;
- voz;
- agentes/workflows;
- generación de imágenes;
- privacidad;
- observabilidad;
- componentes y servicios disponibles en la integración concreta.

### Magnitude
- agente local;
- modelos locales;
- perfilado de hardware;
- recomendación de modelos;
- descarga/configuración;
- ejecución local;
- skills;
- endpoints OpenAI-compatible.

Estas listas son informativas y dependientes de versión/ref. La pantalla debe distinguir lo verificado de lo no disponible o no comprobado.

## 9. Consentimiento de instalación

Después de elegir stack, LEONES debe generar un plan concreto y enseñarlo antes de ejecutar efectos laterales.

Revisa:

- componentes;
- versiones/ref;
- descargas;
- almacenamiento;
- red;
- permisos;
- servicios que puedan arrancar;
- cambios locales;
- posibilidad de desinstalación/rollback.

Sólo autoriza si estás de acuerdo.

**Cancelar la instalación es una salida válida.**

## 10. Instalación: actividad visible y diagnóstico

Una instalación puede tardar varios minutos. **Nunca debe parecer que LEONES se ha quedado bloqueado.** Cuando la herramienta canónica proporcione progreso, la interfaz debe mostrarlo; para descargas largas, usa una barra/porcentaje visible.

Para el instalador oficial de ODS, evita `curl -fsSL`, porque oculta el progreso. Tras haber dado el consentimiento explícito y siguiendo la URL/ref indicada por la integración, descarga primero el instalador a un fichero temporal y **sólo ejecútalo si la descarga termina correctamente**.

**Importante:** LEONES no crea otro instalador de ODS ni otro de Magnitude; usa las interfaces canónicas del stack elegido.

## 11. Verificación

Una instalación autorizada no significa que esté lista. Debe pasar los health checks definidos por la integración:

```text
INSTALLING
    ↓
VERIFY
    ↓
INSTALL_VERIFIED
```

Si falla:

```text
INSTALL_FAILED / BLOCKED
```

No continúes con benchmark si la integración no está verificada.

## 12. Resolución modelo → runtime y benchmark opcional

Tras verificar el stack, LEONES resuelve de forma declarativa el runtime del modelo (Ollama-managed o GGUF→llama.cpp). **No convierte un id Hugging Face en un modelo Ollama.**

Cuando el preflight de runtime/artefacto pase, LEONES pregunta explícitamente si quieres medir A01. Si dices **No**, termina sin ejecutar. Si dices **Sí**, se entrega el plan al runner canónico de RC1.

## 13. Qué se mide

La evidencia debe distinguir medición real de estimación. Una ejecución válida conserva, cuando corresponda:

- `execution_id` nuevo;
- modelo y variante;
- runtime y versión/ref;
- hardware;
- protocolo;
- timestamps;
- métricas;
- outcome;
- artefactos;
- procedencia.

Una medición histórica **no sustituye una ejecución actual**.

## 14. Privacidad

- no compartas secretos ni API keys;
- no introduzcas contraseñas en informes;
- la contribución de evidencia al conocimiento colectivo debe ser opt-in.

## 15. Qué debe entregar un beta tester

1. versión/ref de LEONES;
2. sistema operativo y hardware declarado/observado;
3. modelo y runtime;
4. stack ODS/Magnitude elegido;
5. resultado de instalación/health check;
6. decisión de benchmark;
7. `execution_id` si se ejecutó;
8. resultado y errores;
9. evidencia generada.

## 16. Qué NO hacer

- No reutilizar una evidencia histórica como resultado actual.
- No convertir `estimated` en `measured`.
- No proporcionar credenciales en tickets o evidencias.
- No declarar RC2 validado por una prueba exclusivamente local del desarrollador.

## 17. Problemas

```text
LEONES ref:
SO / arquitectura:
CPU / RAM / GPU / VRAM:
Modelo:
Stack: ODS | Magnitude
Etapa: INSTALL | VERIFY | RESOLVE | BENCHMARK | EVIDENCE
Comando ejecutado:
Mensaje de error:
execution_id (si existe):
```

## 18. Criterio de éxito del piloto

```text
instalar → detectar hardware → candidatos → modelo → stack
  → consentir → verificar → resolver runtime → decidir A01
  → ejecutar si acepta → evidencia
```

RC2 no se considerará cerrada hasta que este recorrido sea reproducible en máquinas externas.
