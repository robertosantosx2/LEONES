# LEONES RC1 — superficie activa

> Documento operativo para impedir que el repositorio vuelva a crecer por inercia.

## Activo y prioritario

1. contratos de hardware/selection/runtime/evidence;
2. `runtime_selection` como frontera de autorización;
3. llama.cpp como ruta física canónica inicial;
4. Hermes como harness agentivo RC1;
5. LLMFit como estimador de fit;
6. Magnitude como fuente/instrumento de caracterización hardware cuando sea verificable;
7. ODS como stack externo candidato a instalación real;
8. Atlas como conocimiento canónico;
9. recomendador como consumidor de evidencia;
10. MANADA como destino de publicación.

## Compatible pero no prioritario

Ollama y otros runtimes/adapters ya existentes pueden permanecer mientras algún test o ruta vigente los necesite. No reciben expansión durante RC1 salvo que sean necesarios para un gate.

## Congelado / histórico

Las implementaciones experimentales de JALÓN 2–5 que fueron sustituidas por contratos finales no constituyen nuevas superficies de producto. Su valor es histórico, de regresión o de recuperación.

## Regla de limpieza

Un archivo sólo se elimina de la rama activa después de comprobar:

```text
referencias
 → imports
 → tests
 → workflows
 → documentación
 → runtime path
```

Si no tiene dependencia activa, puede moverse al archivo `deprecated/*` en un commit separado.

## Orden de ejecución

La rama `rc1-minimal-core` se utilizará para la reconstrucción mínima. No se abrirá otra oleada de funcionalidades hasta que el camino canónico sea ejecutable.

## Primer objetivo de código

Construir el recorrido sintético:

```text
hardware profile
 → model candidate
 → runtime plan
 → agent plan
 → execution reference
 → evidence reference
 → recommendation
```

Debe ser testeable sin instalar Magnitude, ODS, llama.cpp ni Hermes.

Cuando este gate esté verde, se pasa a los adapters. **Todavía no hace falta Ubuntu.**
