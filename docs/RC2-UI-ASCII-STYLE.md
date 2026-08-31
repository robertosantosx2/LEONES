# RC2 — ASCII-Art Interface Style

**Estado:** 🟢 Fijado

La interfaz de beta de LEONES tendrá una personalidad terminal propia: clara, técnica y reconocible, con **ASCII art**, marcos, flechas, estados y señales visuales. Las florituras son de presentación y nunca sustituyen a los contratos ni a los consentimientos.

## Principios

- Banner LEONES al iniciar una sesión.
- Marcos ASCII para separar etapas y decisiones.
- Flechas para representar el recorrido.
- Estados visibles (`✓`, `!`, `?`, `✗`) con texto equivalente para accesibilidad.
- El usuario siempre sabe en qué etapa está.
- Las decisiones irreversibles se muestran dentro de un bloque destacado.
- El ASCII art no debe contener información funcional que no exista en el estado canónico.
- No usar arte decorativo para ocultar errores, requisitos o costes.

## Personalidad

LEONES puede tener una estética de consola retro/ingenieril, pero debe seguir siendo legible en terminales estrechos y sin colores. Los colores, si se añaden posteriormente, son una mejora y no un requisito.

## Referencia

`scripts/rc2_ui.py` contiene la primera pantalla de referencia. Es deliberadamente de solo presentación: no instala, no descarga y no ejecuta benchmarks.
