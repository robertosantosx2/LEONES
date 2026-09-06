# LEONES · Reglas de interfaz (proyecto)

**Estado:** 🟢 **Fijado** · 2026-09-06 (rev. idiomas + install/uninstall + costes)  
**Origen:** feedback beta e interfaz RC2 (`./leones`, `scripts/rc2_ui.py`, `docs/RC2-*`) + feedback producto 2026-09-06  
**Ámbito:** CLI/wizard, mensajes de instalador y páginas web de operador  
**No sustituye:** contratos de datos, evidencia ni gates de release

Este documento es la **referencia de interfaz** para todo el proyecto (RC2 histórico, RC3 cerrada, RC4 en curso). Las fases cambian el *qué* se recomienda o mide; estas reglas fijan *cómo* se habla con el usuario.

---

## 1. Personalidad

- Terminal/ingenieril, legible en 80 columnas, usable **sin color**.
- ASCII (marcos, flechas, etapas) está permitido como **presentación**.
- El ASCII **nunca** sustituye estados, errores, costes ni consentimientos.
- Banner de sesión opcional; no es requisito funcional.
- Referencia histórica de mapa no ejecutable: `scripts/rc2_ui.py`.

---

## 2. Idioma

**Idiomas canónicos de interfaz (obligatorios en el catálogo):**

| Código | Idioma |
|--------|--------|
| `es` | Español |
| `en` | English |
| `zh` | 中文 (chino) |
| `ja` | 日本語 (japonés) |

Reglas:

1. Preguntar el idioma **una sola vez** al inicio de sesión.
2. A partir de esa elección, **un solo idioma** en pantalla.
3. Prohibido mostrar varios idiomas a la vez línea a línea (ruido beta RC2).
4. Identificadores técnicos, comandos, rutas y nombres de métrica permanecen **canónicos** (no se “traducen” `measured_tps`, `hardware_profile.py`, `Leo001`).
5. Cada clave de UI del catálogo debe existir en **es / en / zh / ja**.
6. Si falta una clave: degradar a una lengua de respaldo **explícita** (p. ej. `en`), nunca mezclar cuatro idiomas en la misma frase.

```text
ELIGE EL IDIOMA / CHOOSE LANGUAGE / 选择语言 / 言語を選択
┌──────────────────────────────────────────┐
│  [1] Español                             │
│  [2] English                             │
│  [3] 中文                                 │
│  [4] 日本語                               │
└──────────────────────────────────────────┘
```

---

## 3. Etapas visibles

El usuario debe saber **en qué etapa está** y **qué es lo siguiente**.

Estados visibles con texto equivalente (no solo icono):

| Señal | Significado |
|-------|-------------|
| `✓` / OK | Hecho u observado según el contrato de esa etapa |
| `!` / AVISO | Continuable con riesgo o dato incompleto |
| `?` / PENDIENTE | Falta decisión o dato del usuario |
| `✗` / BLOQUEADO | No se avanza; no se inventa éxito |

---

## 4. Decisiones humanas

1. **El usuario elige** modelo (cuando aplique) y stack (Magnitude / ODS / …).
2. Una recomendación automática (FitLLM, ranking, etc.) **no ejecuta** ni instala sola.
3. Toda opción de menú lleva **descripción breve en el propio menú**.
4. Cancelar es **válido**; no se presenta como fallo del sistema.
5. No hay “siguiente” implícito que instale o mida sin pregunta explícita.

---

## 5. Instalar y desinstalar (par obligatorio)

**Regla dura:** toda acción o componente que el producto ofrezca **instalar** debe ofrecer también **desinstalar** por la misma vía de interfaz (wizard, menú de mantenimiento o comando documentado en el mismo flujo).

Aplica, como mínimo, a:

- FitLLM / LLMFit  
- Hermes  
- OMH  
- Magnitude  
- ODS  
- cualquier otro runtime, agente o utilidad que LEONES proponga instalar  

Reglas:

1. No existe “solo install” sin camino de uninstall en el producto.
2. Desinstalar es **opt-in** y explícito (nunca silencioso ni como efecto colateral oculto).
3. Desinstalar **no** borra evidencia LEONES, perfiles de hardware ni consentimientos registrados, salvo que el usuario lo pida en un paso aparte y etiquetado.
4. Si el uninstall es parcial (p. ej. quita CLI pero deja imágenes Docker), la UI debe decir **qué queda** y cómo limpiarlo.
5. Tras un install exitoso, el cierre de etapa puede recordar que existe uninstall (sin forzar).

---

## 6. Costes antes de instalar (disco, RAM, residencia)

**Antes** de confirmar cualquier instalación ofrecida por LEONES, la interfaz **debe** informar, en el idioma de la sesión:

1. **Peso en disco** (espacio aproximado que ocupará el componente o la descarga principal).  
2. **Ocupación estimada de RAM en ejecución** (cuando el componente está activo / sirviendo).  
3. **Residencia / daemon:** si queda algo en marcha en reposo (servicio al login, proceso en background, puerto escuchando) **aunque el usuario no esté usándolo en ese momento**, distinto de “parado del todo”.

Plantilla mínima de presentación:

```text
┌─ COSTE · <nombre componente> ─────────────────────┐
│ Disco (aprox.):     <N> (paquete + datos tipicos) │
│ RAM en ejecución:   <N> (estimación; depende host)│
│ En reposo:          <nada | servicio/daemon …>    │
│ Arranque al login:  <sí | no>                     │
└───────────────────────────────────────────────────┘
¿Instalar <nombre>? [s/N]
```

Reglas:

1. Si una cifra **no se conoce**, se muestra `UNKNOWN` / “desconocido” — **no se inventa** un número.
2. Distinguir con claridad:  
   - **parado** = no consume (proceso ausente);  
   - **en reposo / idle residente** = sigue habiendo proceso o servicio vivo.
3. Las cifras son **orientativas** (ESTIMATED de coste), no MEASURED del host del usuario, salvo que se midan en ese host y se etiqueten.
4. No se confirma el install hasta que el usuario haya podido ver este bloque (o un equivalente accesible sin ASCII).

---

## 7. Consentimientos (separados)

```text
consentir instalación  ≠  instalar
instalar               ≠  verificar
verificar              ≠  autorizar medición / benchmark
recomendar             ≠  elegir
elegir                 ≠  ejecutar
```

1. No hay consentimiento genérico que autorice todo el pipeline.
2. El consentimiento de medición es **específico**.
3. Por defecto **no** se ejecuta benchmark.
4. Acciones con coste (descarga, disco, daemon) van en **bloque destacado** antes de confirmar.

---

## 8. Honestidad de estados (copy)

| Término | Uso en interfaz |
|---------|------------------|
| ESTIMATED | Fit, ranking o coste orientativo; no “velocidad medida de tu PC” |
| OBSERVED | Visto en el host; no implica VALIDATED LEONES |
| MEASURED | Solo tras ejecución real registrada por LEONES |
| UNKNOWN | No se pudo comprobar |
| BLOQUEADO | Falta runtime/artefacto/consentimiento |

Prohibido presentar exit 0 del instalador como “PASS LEONES”, o un timeout como medición válida.

---

## 9. Errores y bloqueos

1. Mensaje **original** del fallo + etapa + siguiente paso posible.
2. Runtime/artefacto ausente → bloqueo, no MEASURED inventado.
3. Dependencia opcional ausente → falla solo ese paso (p. ej. recomendación FitLLM).
4. No imprimir secretos ni `.env` completo.

---

## 10. Cierre de sesión / “qué ha pasado”

1. Qué se instaló o no.  
2. Qué se verificó (OBSERVED) y qué no.  
3. Qué quedó pendiente.  
4. **Siguiente paso** concreto.  
5. Recordatorio de que existe **desinstalación** de lo instalado vía LEONES, si aplica.

---

## 11. Web de operador

1. Misma semántica ESTIMATED / OBSERVED / MEASURED.  
2. No presentar fases cerradas como abiertas.  
3. Enlazar contratos en `docs/`.  
4. Un `lang` de página; sin párrafos enteros cuadruplicados.

---

## 12. Relación con el código

| Pieza | Rol |
|-------|-----|
| `scripts/rc2_ui.py` | Mapa ASCII histórico |
| `scripts/rc2_wizard.py` / `./leones` | Operador beta RC2 (histórico) |
| `scripts/rc2_i18n.py` | Catálogo multilingüe (ampliar a **ja**) |
| Este documento | **Norma de interfaz de proyecto** |

Wizards nuevos (RC4+) cumplen este documento. Excepciones solo en acta de fase, sin silenciar costes ni uninstall.

---

## 13. Checklist rápido (PR / revisión)

- [ ] ¿Idioma de sesión en **es / en / zh / ja** (uno solo en pantalla)?
- [ ] ¿Cada clave de UI tiene las cuatro lenguas?
- [ ] ¿Cada opción de menú tiene descripción?
- [ ] ¿Todo lo instalable tiene **desinstalable** en el producto?
- [ ] ¿Antes de instalar se muestran **disco**, **RAM en ejecución** y **residencia/daemon** (o UNKNOWN)?
- [ ] ¿Se distingue parado vs idle residente?
- [ ] ¿Instalar / verificar / medir separados?
- [ ] ¿Estados etiquetados ESTIMATED/OBSERVED/MEASURED?
- [ ] ¿Cancelar seguro y explícito?
- [ ] ¿Errores con mensaje original y etapa?
- [ ] ¿El final dice qué pasó, siguiente paso y que existe uninstall?

---

## Procedencia

- Feedback beta instalador (idioma único, descripciones de stack, cierre confuso).
- `docs/RC2-UI-ASCII-STYLE.md`, `docs/RC2-K-MULTILINGUAL-UI.md`, `docs/RC2-H-STACK-CAPABILITY-PRESENTATION.md`, `docs/RC2-I-INSTALLATION-CONSENT.md`, `docs/RC2-F-BENCHMARK-CONSENT.md`.
- Producto 2026-09-06: idiomas **es/en/zh/ja**; **install ↔ uninstall**; costes **disco / RAM ejecución / daemon en reposo**.
- Metodología LEONES: ESTIMATED ≠ MEASURED; DESCUBRIR ≠ ACEPTAR.
