# LEONES · RC4 · Validación de interfaz TUI · 2026-09-07

**Estado:** VALIDADA para la capa TUI en `rc4-tui-choice-flow`.

## Alcance

Esta acta fija la revisión de la TUI RC4 contra `docs/LEONES-INTERFACE-RULES.md`.

- Inicio: selección de idioma.
- Después del idioma: **Estado de la máquina**.
- El estado de máquina presenta hardware, RAM/CPU/disco en uso e inventario de software IA detectado.
- Los agentes se muestran por nombre cuando están presentes.
- Los LLM locales se muestran desde el inventario cuando están presentes.
- La navegación mantiene foco visible y usa `TAB`, flechas, `ESPACIO` y `ENTER` según la etapa.
- La intención de uso es selección múltiple y precede a la recomendación.
- La TUI es presentación: no convierte una recomendación en instalación, ejecución o medición.

## Reglas aplicadas

La referencia normativa es `docs/LEONES-INTERFACE-RULES.md`.

Se preservan especialmente estas separaciones:

```text
recomendar != elegir
conseguir consentimiento != instalar
instalar != verificar
verificar != autorizar medición
elegir != ejecutar
ESTIMATED != MEASURED
```

La frontera física permanece fuera de la TUI. La recomendación RC4 conserva el estado `ESTIMATED` hasta que exista ejecución física registrada por LEONES.

## Estado de evidencia

- No se modifica JALÓN 2.
- No se convierte evidencia externa en medición local.
- No se presenta una recomendación como rendimiento medido del host.
- La validación física final de RC4 permanece pendiente del host Ubuntu.

## Publicación

La página `web/rc4.html` describe el flujo RC4, la TUI, la frontera `ESTIMATED/MEASURED` y enlaza las reglas de interfaz. Esta acta queda como trazabilidad de la revisión de interfaz.

## Siguiente paso

Sincronizar el árbol Ubuntu con la rama publicada y ejecutar la validación física final de RC4. La integración en `main` y la publicación efectiva mediante GitHub Pages quedan sujetas al gate de integración correspondiente.
