# LEONES — instalación mínima

La instalación beta debe ser pequeña: **Git + Python 3.10+ + LLMFit**. LEONES no instala automáticamente ODS, Magnitude ni modelos.

## 1. Descargar

```bash
git clone https://github.com/robertosantosx2/LEONES.git
cd LEONES
```

## 2. Preparar

```bash
./install.sh
```

El instalador comprueba Python, Git y LLMFit y deja preparado el lanzador `./leones`. No crea un entorno virtual ni descarga modelos.

LLMFit es una dependencia externa y canónica de LEONES; su instalación se realiza siguiendo su documentación oficial.

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

## Requisitos

- Linux para la validación RC2 actual.
- Git.
- Python 3.10 o superior.
- LLMFit instalado y accesible como `llmfit`.
- Internet cuando el flujo elegido necesite descargar componentes.

## Regla de distribución

El usuario beta necesita únicamente:

1. el repositorio GitHub;
2. `install.sh`;
3. `leones`;
4. este `INSTALL.md`;
5. la documentación RC2 enlazada desde el README.

El resto del repositorio es implementación, contratos, pruebas y evidencia; no forma parte de las instrucciones de instalación.
