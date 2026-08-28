# LEONES — mapa de deprecación pre-RC1

> **Estado: ACTIVO.** Esta página define qué se conserva, qué queda histórico y qué no debe volver a entrar en el camino canónico.

## 1. Regla principal

No se borra historia para conseguir minimalismo.

El minimalismo de RC1 se obtiene haciendo que exista **un solo camino activo**, mientras que las decisiones descartadas permanecen recuperables en una rama `deprecated/*` y en el historial Git.

## 2. Rama de archivo

`deprecated/pre-rc1-legacy` conserva una instantánea del estado inmediatamente anterior a la reorganización RC1 y contiene el manifiesto de archivo.

Las ramas históricas `jalon2-*`, `jalon3-*`, `jalon4-*` y `jalon5-*` se consideran ramas de desarrollo histórico. No son arquitectura activa de RC1.

## 3. Criterio para retirar código

Un componente puede pasar a `deprecated/*` cuando:

- duplica una capacidad externa que ahora integraremos mediante adapter;
- implementa una ruta de selección/runtime sustituida por el camino canónico;
- pertenece a un experimento cerrado sin dependencia actual;
- mantiene una integración no validada que no es necesaria para RC1;
- añade superficie de mantenimiento sin aportar al recorrido mínimo.

## 4. Criterio de conservación

Se mantiene activo si el componente:

- protege un contrato vigente;
- es necesario para Atlas/Prospector actualmente usados;
- participa en la evidencia de JALÓN 3;
- es requerido por el camino directo llama.cpp;
- es necesario para Hermes/LLMFit/Magnitude/ODS adapters;
- publica o valida resultados del recorrido canónico.

## 5. Qué NO hacemos ahora

No vamos a mover a ciegas cientos de archivos basándonos en nombres de fases. Eso podría romper imports, tests o contratos históricos que todavía alimentan RC1.

La limpieza se ejecutará por lotes:

```text
inventario
 → dependencia
 → test
 → deprecación
 → eliminación del camino activo
 → CI
```

Cada lote será un commit pequeño y reversible.

## 6. Camino canónico que queda protegido

```text
hardware
 → fit
 → selection
 → runtime
 → Hermes
 → execution
 → measurement
 → evidence
 → recommendation
 → MANADA
```

Todo lo que no contribuya a este recorrido, a su documentación o a sus fuentes de evidencia es candidato a archivo.

## 7. Prohibición de expansión prematura

No se incorporarán nuevas capas de producto sólo porque sean interesantes. Antes debe demostrarse que resuelven una necesidad del camino RC1 que no pueda cubrir una herramienta existente.
