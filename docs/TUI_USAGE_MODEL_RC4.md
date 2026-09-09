# LEONES RC4 — Modelo de uso de la TUI

**Estado: FIJADO A FUEGO / NORMATIVO**

Este documento convierte el comportamiento observado durante el desarrollo y las pruebas de la TUI RC4 en un modelo de uso estable. Toda nueva versión de la TUI debe revisarlo antes de modificar `scripts/rc4_tui.py` o su lanzador.

## 1. Principio

LEONES es una **TUI persistente de control**, no una sucesión de pantallas modales.

Después de seleccionar el idioma, la interfaz conserva siempre:

1. menú de navegación a la izquierda;
2. `OPERACIÓN / PROGRESO` arriba;
3. `SELECCIÓN / INFORMACIÓN PRINCIPAL` en el centro;
4. `ACCIÓN / ESCALADO / PRIVILEGIOS` abajo.

El usuario debe poder entender en todo momento **dónde está, qué ha seleccionado, qué está ocurriendo y qué acción va a autorizar**.

## 2. Cursor: contrato visual y funcional

El cursor tiene dos expresiones complementarias:

- **cursor lógico:** `▶` delante del elemento actualmente enfocado;
- **cursor del terminal:** posición física del cursor de curses sobre ese mismo elemento.

El cursor lógico es obligatorio en todos los selectores:

- `[3] INTENCIÓN`;
- `[5] LLMs / INSTALACIÓN`;
- `[6] INST IA LOCAL`;
- `[7] DESINSTALACIÓN`;
- recomendaciones y cualquier selector futuro.

Ejemplo canónico:

```text
  [ ] Programación
▶ [X] Razonamiento
  [X] Investigación
```

`↑/↓` mueve el foco. El foco **no equivale a selección**.

`SPACE` cambia exclusivamente la selección del elemento enfocado.

`ENTER` nunca significa «seleccionar»: significa cruzar la frontera de acción/ejecución.

## 3. Estado instalado: punto blanco

El estado de instalación es información independiente de la selección.

- `•` = componente realmente instalado/detectado localmente.
- ausencia de `•` = no instalado/detectado.
- `[X]` = seleccionado por el usuario.
- `[ ]` = no seleccionado.

Nunca se debe inferir «instalado» porque un elemento esté seleccionado.

### LLMs

Un LLM local gestionado por LEONES cuenta como instalado cuando existe su marcador `.leones-installed.json` dentro de su directorio de modelo.

### Software IA local

`[6] INST IA LOCAL` muestra **todos los componentes conocidos**, con `•` cuando la instalación real puede verificarse localmente. La detección debe seguir las mismas señales que utiliza el instalador siempre que sea posible.

## 4. Desinstalación

`[7] DESINSTALACIÓN` muestra **solo componentes que estén realmente instalados/detectados**.

No se debe presentar una lista genérica de componentes inexistentes como si fueran candidatos válidos.

Cada elemento mostrado conserva el `•` de instalado y permite seleccionarlo con `SPACE`.

Si no hay nada instalado, la TUI informa de ello y no ofrece una ejecución vacía.

La limpieza continúa siendo independiente por componente y respeta el contrato de `scripts/uninstall.sh`.

## 5. Secuencia de interacción obligatoria

La secuencia canónica es:

```text
IDIOMA
  ↓
ESTADO DE LA MÁQUINA
  ↓
INTENCIÓN (selección múltiple)
  ↓ ENTER
RECOMENDACIÓN RC4
  ↓
SELECCIÓN HUMANA
  ↓ ENTER
ACEPTACIÓN [Y/N]
  ↓ Y, si requiere privilegios
AUTORIZACIÓN DEL SISTEMA
  ↓ contraseña sudo dentro de curses
OPERACIÓN EN SEGUNDO PLANO
  ↓
RESULTADO
```

No se debe saltar una frontera de autorización.

## 6. Privilegios

Una petición de contraseña del sistema **nunca debe escapar de curses**.

Cuando una operación requiera privilegios:

1. la TUI muestra `AUTORIZACIÓN DEL SISTEMA` en el panel inferior;
2. solicita la autorización allí;
3. valida la autorización;
4. solo entonces inicia la operación;
5. si se cancela o falla, no se ejecuta ninguna operación.

La aceptación de la operación y la autorización de privilegios son estados distintos.

## 7. Operaciones largas y actividad visible

Instalaciones, descargas, recomendaciones y desinstalaciones se ejecutan de forma asíncrona.

Al pulsar `ENTER` no basta con lanzar un hilo y decir «completado».

La TUI debe mostrar inmediatamente:

- `● ACTIVA`;
- operación y elemento actual;
- fase;
- progreso determinado cuando exista;
- barra de actividad/progreso;
- datos descargados y velocidad cuando estén disponibles;
- último mensaje recibido.

La operación solo puede pasar a `COMPLETADA` cuando el proceso real haya terminado correctamente.

Si el proceso termina con error, el estado es `FALLIDA`.

Mientras una operación está activa, la TUI continúa siendo navegable y el usuario no queda bloqueado esperando el proceso.

## 8. Recomendador RC4

La intención de usuario es obligatoria y de selección múltiple.

La recomendación se ejecuta después de `ENTER` sobre la selección de intención.

Las recomendaciones RC4 siguen siendo:

- `ESTIMATED`;
- `execution_authorized=False`;
- `measurement_authorized=False`;
- `measured=False`;
- `user_choice_required=True`.

La TUI nunca debe presentar una recomendación estimada como medición real ni autorizar automáticamente su ejecución.

## 9. Estado de la máquina

Después del idioma, el estado debe permitir comprender el entorno local: hardware, recursos y software IA detectado.

Como mínimo se muestran:

- CPU y CPU lógicas;
- GPU cuando sea detectable;
- RAM ocupada/total;
- disco ocupado/total;
- LLMs locales instalados y cuáles son;
- software IA local instalado y cuáles son.

El patrón esperado es explícito, por ejemplo:

```text
Agentes          3 instalados   (lista)
LLMs locales     2 modelos      (lista)
```

Los nombres concretos deben proceder de detección real, no de valores ficticios.

## 10. Internacionalización

El idioma elegido en la pantalla inicial permanece durante toda la sesión.

Todos los textos de interfaz, estados, confirmaciones, autorizaciones y resultados deben respetar el idioma seleccionado.

No se deben introducir mensajes en inglés en una sesión española salvo que formen parte de un identificador técnico que el usuario necesite ver literalmente.

## 11. Reglas de teclado

```text
TAB       cambiar foco entre navegación y contenido
↑ / ↓     mover cursor lógico
SPACE     seleccionar/deseleccionar
ENTER     ejecutar / cruzar frontera de acción
Y         aceptar una acción explícita
N / ESC   cancelar / volver
Q         salir
```

El teclado debe comportarse de forma estable independientemente de que una operación esté activa.

## 12. Regla para futuras versiones

Antes de modificar la TUI, revisar conjuntamente:

- `docs/TUI_RULES_RC4.md` — contrato estructural/normativo;
- `docs/TUI_USAGE_MODEL_RC4.md` — modelo de uso y comportamiento observado;
- `scripts/rc4_tui.py` — implementación actual;
- tests de TUI y de integración de operaciones.

Una nueva versión **no puede eliminar** cursor visible, selección múltiple, estado instalado, autorización en curses, actividad de fondo ni separación entre aceptación y ejecución sin una revisión explícita del contrato.

Este documento queda fijado como referencia de regresión para RC4 y las versiones posteriores.
