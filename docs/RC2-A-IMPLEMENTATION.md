# RC2-A — Bootstrap del flujo de usuario beta

**Estado:** implementado  
**Fecha:** 31 de agosto de 2026  
**Predecesor:** RC1 — ejecución efectiva validada  

## Objetivo

Construir el primer punto de entrada del flujo beta sin duplicar selección, perfilado, instalación, runtime ni benchmark.

## Implementación

`python3 scripts/rc2_beta.py` proporciona un orquestador CLI mínimo que:

1. inicia el recorrido beta;
2. muestra el preflight y el hardware básico observado por el host;
3. conserva lo desconocido como desconocido;
4. puede cargar un plan de selección ya validado;
5. presenta las capacidades funcionales de ODS y Magnitude antes de elegir;
6. registra una elección explícita de stack cuando se proporciona;
7. registra la decisión Sí/No sobre benchmark;
8. deriva explícitamente la ejecución futura al runner canónico.

## Límite deliberado

RC2-A **no instala software, no descarga modelos, no arranca servicios y no ejecuta benchmarks**. Es una frontera de orquestación verificable. Las operaciones con efectos laterales se incorporarán en RC2-E y la ejecución medida seguirá perteneciendo al runner canónico.

## Reutilización

La implementación se apoya conceptualmente en los contratos existentes de selección, decisión ODS/Magnitude y runner plan. Los adaptadores ODS/Magnitude siguen siendo dependency-free y no ejecutan instalación ni runtime por sí mismos.

## ODS / Magnitude

La interfaz ya prepara el requisito fundamental de RC2: antes de elegir se presentan las categorías funcionales relevantes de cada alternativa. La disponibilidad concreta queda condicionada a la versión/ref instalada y a la evidencia disponible.

## Validación

`tests/test_rc2_beta_flow.py` comprueba:

- arranque sin efectos laterales;
- presentación de capacidades ODS/Magnitude;
- carga de la fixture de selección RC1;
- elección explícita de stack;
- bifurcación benchmark Sí/No;
- continuidad hacia el runner canónico.

## Siguiente paso

**RC2-B — Hardware y perfilado real.**

Debe conectar el preflight con las capacidades verificadas de ODS/Magnitude y producir un perfil normalizado `observed`/`estimated`, sin crear un tercer perfilador.
