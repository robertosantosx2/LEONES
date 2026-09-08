# LEONES RC4 — contrato permanente de la TUI

> **Regla normativa:** `scripts/rc4_tui.py` debe cumplir este documento. Ante cualquier cambio de TUI, revisar primero este archivo.

## 1. Idioma y primera pantalla

- La selección de idioma es la **primera y única pantalla sin menú de navegación**.
- Una vez elegido el idioma, el menú lateral permanece visible durante **toda la sesión**.
- Todas las etiquetas, estados, mensajes, ayudas y resultados generados por LEONES deben mostrarse en el idioma seleccionado.

## 2. Marco persistente

- La TUI es un **centro de control persistente**, no una sucesión de pantallas modales.
- El marco principal contiene permanentemente:
  - menú de navegación a la izquierda;
  - panel de operación en segundo plano;
  - panel de información/acción a la derecha.
- Cambiar de sección nunca debe ocultar el menú lateral.

## 3. Foco y teclado

- Existen dos zonas de foco: **NAVEGACIÓN** y **CONTENIDO**.
- `TAB` alterna el foco entre ambas zonas.
- Con foco en NAVEGACIÓN, `↑/↓`, `1–5` y `ENTER` permiten desplazarse/abrir.
- Con foco en CONTENIDO, las teclas corresponden a las acciones de la pantalla.
- Las indicaciones de teclas disponibles deben aparecer **siempre en la parte superior y en la parte inferior** de la pantalla.
- `Q` permite salir de la sesión; una operación en segundo plano no debe convertir la TUI en una espera bloqueante.

## 4. Cursor

- El cursor debe permanecer visible durante toda la sesión después de elegir idioma.
- Debe situarse en el elemento que tiene el foco.
- Se solicita cursor de terminal visible/parpadeante mediante curses (`curs_set(1)`); si el terminal no soporta parpadeo, el cliente de terminal determina su comportamiento visual.

## 5. Operaciones en segundo plano

- Descargas, instalaciones y desinstalaciones se ejecutan en segundo plano.
- El usuario puede navegar por el resto del centro de control mientras una operación está activa.
- Nunca se debe mostrar una pantalla modal que obligue a esperar a que termine una operación.
- El panel permanente **OPERACIÓN EN SEGUNDO PLANO** debe mostrar siempre:
  - indicador de actividad;
  - operación y elemento actual;
  - fase/estado;
  - porcentaje y barra cuando sea estimable;
  - datos transferidos y velocidad cuando estén disponibles.
- Una operación completada permanece resumida en el panel, sin robar el foco al usuario.

## 6. Selección múltiple

- Propósitos de usuario: selección múltiple.
- Modelos recomendados: selección múltiple.
- Software IA: selección múltiple (`FitLLM`, `ODS`, `Magnitude`, `Hermes`, `OMH`).
- Desinstalación: pantalla independiente con selección múltiple de componentes instalados.
- `SPACE` marca/desmarca; `1–n` alterna la selección del elemento correspondiente; `ENTER` confirma la acción.

## 7. Seguridad de selección y privilegios

- La instalación de modelos requiere consentimiento explícito.
- Las recomendaciones RC4 siguen siendo `ESTIMATED` y no autorizan ejecución ni medición.
- Un modelo solo cuenta como instalado cuando existe `.leones-installed.json`.
- La desinstalación solo actúa sobre componentes explícitamente seleccionados y confirmados.
- **Toda interacción que requiera privilegios del sistema debe permanecer dentro de la TUI.**
- La confirmación explícita (`Y`) de instalación o desinstalación es la puerta de acción del usuario.
- Si el sistema requiere `sudo`, la petición de autorización y contraseña debe mostrarse **dentro de un recuadro de la TUI**; nunca puede aparecer el prompt de `sudo` directamente sobre el terminal curses.
- Una autorización de privilegios correcta debe dejar la operación ejecutándose en segundo plano y devolver el control al centro de control.
- Si la autorización falla o el usuario cancela, la instalación/desinstalación no se inicia.

## 8. Regla de mantenimiento

Antes de modificar `scripts/rc4_tui.py` o cualquier lanzador que lo ejecute, comprobar este contrato y conservar todas sus reglas. Si una nueva funcionalidad entra en conflicto con él, el contrato prevalece hasta que se modifique explícitamente este documento.
