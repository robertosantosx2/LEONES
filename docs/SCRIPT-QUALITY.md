# Calidad de scripts en LEONES

## Directiva

Los scripts de LEONES deben ser **minimalistas, legibles y fáciles de mantener**.
Deben poder entenderse por una persona con conocimientos básicos de programación.

### Reglas obligatorias

1. **Un paso lógico por instrucción.** Evita varias instrucciones separadas por `;`.
2. **Líneas cortas.** Mantén las líneas en 100 caracteres o menos cuando sea razonable.
3. **Propósito visible.** Todo script ejecutable debe tener shebang y un docstring inicial.
4. **Comentarios útiles.** Comenta el motivo de una decisión o un paso no evidente; no describas literalmente lo que ya dice el código.
5. **Nombres claros.** Prefiere nombres completos y comprensibles frente a abreviaturas crípticas.
6. **Funciones pequeñas.** Divide procesos largos en funciones con una responsabilidad clara.
7. **Sin complejidad accidental.** No introduzcas capas, abstracciones o dependencias si una solución directa es suficiente.
8. **Sin código muerto.** Elimina imports, variables, ramas y funciones que ya no tengan uso.
9. **Errores comprensibles.** Los mensajes de error deben explicar qué ocurrió y, cuando sea posible, cómo corregirlo.
10. **No ocultar comportamiento.** Un script no debe depender de efectos implícitos difíciles de descubrir.

## Comprobación automática

`python scripts/check_script_quality.py` revisa los scripts ejecutables de `scripts/`.

Con `--strict`, cualquier incumplimiento hace fallar la comprobación:

```bash
python scripts/check_script_quality.py --strict
```

La comprobación es deliberadamente pequeña. Su objetivo es detectar problemas evidentes,
no sustituir una revisión humana.

## Migración del código existente

La directiva se aplica a todo el proyecto, pero la limpieza del código histórico se hace de
forma incremental. Primero se corrigen los scripts tocados por un cambio; después se reduce
el inventario existente de avisos sin mezclar refactorizaciones no relacionadas.

La calidad debe mejorar sin cambiar el comportamiento salvo cuando una prueba demuestre que
el cambio corrige un defecto.
