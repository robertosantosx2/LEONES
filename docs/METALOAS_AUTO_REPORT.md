# metaLOAS — Informe automático

Para simplificar las contribuciones de la comunidad, LOAS incluye un script que recopila automáticamente la información técnica básica de la máquina y del software relevante.

## Uso rápido

Desde la raíz del proyecto:

```bash
python3 scripts/metaloas-report.py
```

Genera:

```text
results/metaLOAS/auto-report.md
```

También se puede indicar el modelo y las rutas de los componentes:

```bash
python3 scripts/metaloas-report.py \
  --model ~/models/loas/Qwen3-8B-Q4_K_M.gguf \
  --llama-cpp ./llama.cpp \
  --buddy ./buddy \
  --output results/metaLOAS/H1/mi-prueba.md
```

## Qué obtiene automáticamente

### Máquina

- sistema operativo y versión;
- kernel;
- arquitectura;
- CPU;
- RAM;
- GPU cuando puede detectarse;
- VRAM/driver NVIDIA cuando `nvidia-smi` está disponible.

### Software

- versión de Python;
- versión de Git;
- commit de `llama.cpp`;
- presencia de `llama-server`;
- presencia de `llama-bench`;
- commit de Buddy.

### Modelo

Si se proporciona `--model`, registra:

- nombre del fichero;
- SHA-256;
- deja la cuantización para revisión cuando no pueda determinarse con seguridad.

### LOTB

Deja preparados los campos B01–B05 para incorporar los resultados del test agentivo.

## Privacidad

El script está diseñado para **no recopilar deliberadamente**:

- nombre de usuario;
- hostname;
- MAC/IP;
- números de serie;
- UUID;
- rutas personales;
- credenciales;
- tokens;
- ubicación;
- cuentas personales.

Además, el resultado siempre incluye una advertencia para hacer una revisión humana antes de publicarlo.

Esto es intencionado: **automatizar la captura técnica no significa publicar automáticamente los datos**.

## Flujo recomendado

```text
ejecutar metaloas-report.py
          ↓
revisar Markdown
          ↓
completar perfil H0/H1/H2/H3
          ↓
incorporar resultados LOTB B01-B05
          ↓
comprobar privacidad
          ↓
Pull Request a LOAS
```

## Filosofía

El objetivo es que aportar un experimento metaLOAS requiera **minutos y no una sesión de inventario manual**.

La información que una máquina puede conocer de forma objetiva debe capturarse automáticamente. Los datos que requieren interpretación —por ejemplo, qué perfil LOAS corresponde, qué tarea se ejecutó o qué observaciones merece el resultado— siguen siendo responsabilidad del usuario.
