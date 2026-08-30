# LEONES V1 — Guía de uso

## Estado

Esta guía describe la superficie de usuario que se está cerrando para V1.

La primera operación disponible es el **preflight**. Sirve para comprobar qué puede observar LEONES en el ordenador antes de pedir una ejecución física.

## 1. Preparar el entorno

Desde la raíz del repositorio:

```bash
python3 scripts/leones_v1.py preflight --pretty
```

Si se utiliza el entorno virtual del proyecto:

```bash
source .venv/bin/activate
python scripts/leones_v1.py preflight --pretty
```

## 2. Qué hace el preflight

Muestra información que el ordenador puede proporcionar directamente, como:

- versión de Python;
- sistema y arquitectura;
- procesador disponible para el sistema operativo;
- número de CPUs que Python puede observar;
- presencia de algunos ejecutables de runtime;
- presencia de los contratos canónicos de LEONES.

El resultado tiene formato JSON para que pueda ser leído tanto por una persona como por otro programa.

## 3. Qué NO hace

El preflight **no**:

- mide tokens por segundo;
- estima TPS;
- ejecuta un benchmark;
- crea una recomendación;
- sustituye ODS/Magnitude o LLMFit;
- convierte una detección de runtime en evidencia física;
- inventa resultados cuando un runtime o modelo no está disponible.

Es solamente la puerta de entrada de usuario.

## 4. Ejemplo de interpretación

Si aparece un ejecutable como `llama-cli`, eso significa solamente que el sistema puede localizar ese ejecutable. Para afirmar rendimiento real todavía hace falta ejecutar el runtime con un modelo y conservar la evidencia correspondiente.

Del mismo modo, que un contrato aparezca como presente significa que el contrato existe en el repositorio; no significa que una operación física haya sido ejecutada.

## 5. Camino hacia la V1 completa

La superficie V1 se ampliará sobre la misma cadena ya fijada:

```text
entrada del usuario
  ↓
preflight
  ↓
selección
  ↓
runtime autorizado
  ↓
ejecución
  ↓
medición
  ↓
evidencia
  ↓
decisión ODS/Magnitude → LEONES
  ↓
recomendación
  ↓
publicación
  ↓
salida
  ↓
traza E2E
```

Cada etapa reutiliza su contrato existente. La interfaz de usuario no crea un segundo sistema de decisión o medición.

## 6. Si algo falla

1. Ejecuta primero el preflight.
2. Comprueba el mensaje de error.
3. No rellenes manualmente una evidencia física.
4. Si el problema requiere hardware real, la ejecución física se realiza en la plataforma canónica y se conserva su evidencia.

**Regla sencilla:** si LEONES no lo ha observado o medido realmente, debe decirlo.
