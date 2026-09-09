# LEONES RC4 — contrato permanente de la TUI

> **Regla normativa:** `scripts/rc4_tui.py` debe cumplir este documento. Ante cualquier cambio de TUI, revisar primero este archivo.

## 1. Idioma y primera pantalla

- La selección de idioma es la **primera y única pantalla sin menú de navegación**.
- Una vez elegido el idioma, el menú lateral permanece visible durante **toda la sesión**.
- Todas las etiquetas, estados, mensajes, ayudas y resultados generados por LEONES deben mostrarse en el idioma seleccionado.

## 2. Marco persistente y arquitectura de tres paneles

- La TUI es un **centro de control persistente**, no una sucesión de pantallas modales.
- Después de seleccionar idioma, el marco principal mantiene permanentemente el menú lateral y **tres paneles apilados a la derecha**:
  1. **OPERACIÓN / PROGRESO** — panel superior.
  2. **SELECCIÓN / INFORMACIÓN PRINCIPAL** — panel central.
  3. **ACCIÓN / ESCALADO / PRIVILEGIOS** — panel inferior.
- El menú lateral nunca desaparece al cambiar de sección.
- Ningún cuadro de confirmación o autorización puede superponerse al panel central ni mezclarse con otro cuadro de interacción.

### 2.1 Panel superior — OPERACIÓN / PROGRESO

- Es permanente y está dedicado exclusivamente al estado de las operaciones.
- Muestra las operaciones en marcha, tanto si fueron iniciadas desde segundo plano como si siguen ejecutándose mientras el usuario navega por otra sección.
- Debe mostrar, cuando estén disponibles:
  - indicador de actividad;
  - operación y elemento actual;
  - fase/estado;
  - porcentaje y barra de progreso;
  - datos transferidos;
  - velocidad;
  - resultado de la última operación.
- No contiene preguntas de aceptación ni solicitudes de contraseña.

### 2.2 Panel central — SELECCIÓN / INFORMACIÓN PRINCIPAL

- Contiene los selectores con los que interactúa directamente el usuario: intención, modelos recomendados, software IA, desinstalación u otros futuros selectores.
- Las selecciones múltiples se realizan aquí mediante `SPACE` o las teclas numéricas correspondientes.
- El panel central **no contiene prompts de privilegios ni solicitudes de contraseña**.
- Cuando el usuario coloca el foco sobre un elemento seleccionable, el panel inferior puede mostrar sus características, estado, requisitos y consecuencias, sin sustituir ni ocultar el selector.

### 2.3 Panel inferior — ACCIÓN / ESCALADO / PRIVILEGIOS

- Es el único panel destinado a las interacciones que materializan una acción.
- Muestra las características del elemento o elementos seleccionados en el panel central: estado, tamaño, requisitos, destino, dependencias, consecuencias y cualquier otra información relevante disponible.
- La **aceptación de la acción** y la **autorización de privilegios del sistema son pasos distintos y visualmente separados**.
- Nunca deben aparecer simultáneamente como cuadros superpuestos ni compartir el mismo recuadro de diálogo.
- Secuencia normativa:
  1. El usuario selecciona en el panel central.
  2. El panel inferior muestra qué se ha seleccionado y sus características.
  3. `ENTER` solicita la aceptación de la acción en el propio panel inferior.
  4. Tras una aceptación positiva mediante `Y`, si son necesarios privilegios, el panel inferior cambia a un **estado exclusivo de AUTORIZACIÓN DEL SISTEMA**.
  5. La autorización de `sudo` y su contraseña, si procede, se solicitan únicamente dentro de ese estado del panel inferior.
  6. Si la autorización es correcta, la operación pasa al panel superior y continúa en segundo plano; el panel inferior vuelve a mostrar información/estado de la selección.
  7. Si la autorización falla o se cancela, no se inicia ninguna operación y el panel inferior informa claramente del motivo.
- El prompt normal de `sudo` nunca puede escapar al terminal curses.

## 3. Foco y teclado

- Existen dos zonas de foco: **NAVEGACIÓN** y **CONTENIDO**.
- `TAB` alterna el foco entre ambas zonas.
- Con foco en NAVEGACIÓN, `↑/↓`, teclas numéricas y `ENTER` permiten desplazarse/abrir.
- Con foco en CONTENIDO, las teclas corresponden a las acciones del panel activo.
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
- Una operación completada permanece resumida en el panel superior, sin robar el foco al usuario.

## 6. Selección múltiple

- Propósitos de usuario: selección múltiple.
- Modelos recomendados: selección múltiple.
- Software IA: selección múltiple (`FitLLM`, `ODS`, `Magnitude`, `Hermes`, `OMH`).
- Desinstalación: selección múltiple de componentes instalados.
- `SPACE` marca/desmarca; `1–n` alterna la selección del elemento correspondiente; `ENTER` confirma la acción.

## 7. Seguridad de selección y privilegios

- La instalación de modelos requiere consentimiento explícito.
- Las recomendaciones RC4 siguen siendo `ESTIMATED` y no autorizan ejecución ni medición.
- Un modelo solo cuenta como instalado cuando existe `.leones-installed.json`.
- La desinstalación solo actúa sobre componentes explícitamente seleccionados y confirmados.
- **Toda interacción que requiera privilegios del sistema debe permanecer dentro de la TUI.**
- La confirmación explícita (`Y`) de instalación o desinstalación es la puerta de acción del usuario.
- Si el sistema requiere `sudo`, la petición de autorización y contraseña debe mostrarse **dentro del panel inferior de ACCIÓN / ESCALADO / PRIVILEGIOS**, nunca en el panel central ni directamente sobre el terminal curses.
- La aceptación (`Y`) y la autorización de privilegios son **dos estados consecutivos**, no dos diálogos simultáneos.
- Una autorización de privilegios correcta debe dejar la operación ejecutándose en segundo plano y devolver el control al centro de control.
- Si la autorización falla o el usuario cancela, la instalación/desinstalación no se inicia.

## 8. Regla de mantenimiento

Antes de modificar `scripts/rc4_tui.py` o cualquier lanzador que lo ejecute, comprobar este contrato y conservar todas sus reglas. Si una nueva funcionalidad entra en conflicto con él, el contrato prevalece hasta que se modifique explícitamente este documento.
