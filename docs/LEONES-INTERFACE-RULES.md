# LEONES · Reglas de interfaz (proyecto)

**Estado:** 🟢 **Fijado** · 2026-09-06  
**Origen:** feedback beta e interfaz RC2 (`./leones`, `scripts/rc2_ui.py`, `docs/RC2-*`)  
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

1. Preguntar el idioma **una sola vez** al inicio de sesión (p. ej. ES / EN / ZH).
2. A partir de ahí, **un solo idioma** en pantalla.
3. Prohibido el trilingüe línea a línea (ruido beta RC2).
4. Identificadores técnicos, comandos, rutas y nombres de métrica permanecen **canónicos** (no se “traducen” `measured_tps`, `hardware_profile.py`, `Leo001`).
5. Si falta una clave de traducción: degradar a una lengua de respaldo **explícita**, no mezclar tres en la misma frase.

---

## 3. Etapas visibles

El usuario debe saber **en qué etapa está** y **qué es lo siguiente**.

Patrón mínimo:

```text
[etapa actual]
  ↓
[siguiente]
```

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
2. Una recomendación automática (FitLLM, ranking, Hermes histórico) **no ejecuta** ni instala sola.
3. Toda opción de menú lleva **descripción breve en el propio menú** (lección RC2: ODS vs Magnitude sin salir a buscar docs).
4. Cancelar es **válido**; no se presenta como fallo del sistema.
5. No hay “siguiente” implícito que instale o mida sin pregunta explícita.

---

## 5. Consentimientos (separados)

Cada uno es una barrera propia:

```text
consentir instalación  ≠  instalar
instalar               ≠  verificar
verificar              ≠  autorizar medición / benchmark
recomendar             ≠  elegir
elegir                 ≠  ejecutar
```

Reglas:

1. No hay consentimiento genérico que autorice todo el pipeline.
2. El consentimiento de medición (p. ej. A01 / Leo*) es **específico** y posterior a verify/preflight cuando el contrato lo exija.
3. Por defecto **no** se ejecuta benchmark.
4. Las acciones irreversibles o con coste (descarga, disco, daemon) se muestran en un **bloque destacado** antes de confirmar.

---

## 6. Honestidad de estados (copy)

En UI y logs orientados a humano:

| Término | Uso en interfaz |
|---------|------------------|
| ESTIMATED | Fit / ranking / fuente externa; nunca como “velocidad de tu PC medida” |
| OBSERVED | Visto en el host (doctor, status, sonda); no implica VALIDATED LEONES |
| MEASURED | Solo tras ejecución real registrada por LEONES |
| UNKNOWN | Si no se pudo comprobar |
| BLOQUEADO | Falta runtime/artefacto/consentimiento; no se fabrica resultado |

Prohibido:

- Presentar exit code 0 del instalador como “PASS LEONES”.
- Presentar un fallo o timeout como medición válida.
- Mezclar cifras ESTIMATED y MEASURED en la misma frase sin etiquetar.

---

## 7. Errores y bloqueos

1. Mostrar el **mensaje original** del fallo (comando, stderr relevante), no solo un eufemismo.
2. Indicar **qué etapa falló** y **qué puede hacer el usuario** después.
3. Runtime o artefacto ausente → bloqueo explícito, no MEASURED inventado.
4. Dependencia opcional ausente (p. ej. FitLLM en RC4) → error **solo** en el paso de recomendación; el resto del producto sigue usable.
5. No imprimir secretos, tokens ni contenido completo de `.env`.

---

## 8. Costes y componentes opcionales

Cuando se proponga instalar o activar algo opcional (Hermes, OMH, FitLLM, stacks):

1. Decir **para qué sirve** en una o dos frases.
2. Advertir **peso en disco** y **RAM** si se conoce o es material.
3. Decir si deja **proceso residente / daemon / servicio al login**.
4. Ofrecer desinstalación **opt-in** cuando el componente deje de aportar (p. ej. FitLLM tras stack instalado en RC4); nunca borrar en silencio.

---

## 9. Cierre de sesión / “qué ha pasado”

Al terminar un recorrido, la interfaz resume:

1. Qué se instaló o no.
2. Qué se verificó (OBSERVED) y qué no.
3. Qué quedó pendiente.
4. Cuál es el **siguiente paso** concreto (comando o decisión), no un “éxito” vacío.

---

## 10. Web de operador

Las páginas `inicio-rapido`, `operacion`, `estado`, `rc3`, `rc4`, `app`:

1. Usan la misma semántica ESTIMATED / OBSERVED / MEASURED.
2. No presentan fases cerradas como abiertas (p. ej. RC3 CERRADA).
3. Enlazan contratos (`docs/…`) en lugar de reinventar reglas.
4. Un idioma de página (`lang=…`); no duplicar párrafos enteros en tres idiomas.

---

## 11. Relación con el código

| Pieza | Rol |
|-------|-----|
| `scripts/rc2_ui.py` | Mapa ASCII histórico; no ejecuta |
| `scripts/rc2_wizard.py` / `./leones` | Operador beta RC2 (histórico) |
| `scripts/rc2_i18n.py` | Catálogo multilingüe de referencia |
| Docs `RC2-K`, `RC2-H`, `RC2-I`, `RC2-F`, `RC2-UI-ASCII-STYLE` | Origen de estas reglas |
| Este documento | **Norma de interfaz de proyecto** |

Cualquier wizard o CLI nuevo (RC4+) debe cumplir este documento. Si una fase necesita una excepción, se documenta en su acta **sin** silenciar consentimientos ni fronteras de evidencia.

---

## 12. Checklist rápido (PR / revisión)

- [ ] ¿Un idioma por sesión?
- [ ] ¿Cada opción de menú tiene descripción?
- [ ] ¿Instalar / verificar / medir están separados?
- [ ] ¿Los estados están etiquetados (ESTIMATED/OBSERVED/MEASURED)?
- [ ] ¿Cancelar es seguro y explícito?
- [ ] ¿Errores conservan mensaje original y etapa?
- [ ] ¿Opcionales declaran disco/RAM/daemon?
- [ ] ¿El final dice qué pasó y el siguiente paso?

---

## Procedencia

- Feedback beta instalador (idioma único, descripciones de stack, cierre confuso).
- `docs/RC2-UI-ASCII-STYLE.md`, `docs/RC2-K-MULTILINGUAL-UI.md`, `docs/RC2-H-STACK-CAPABILITY-PRESENTATION.md`, `docs/RC2-I-INSTALLATION-CONSENT.md`, `docs/RC2-F-BENCHMARK-CONSENT.md`, `docs/RC2-USER-MANUAL.md`, `docs/completed/rc2-wizard.md`.
- Metodología LEONES: ESTIMATED ≠ MEASURED; DESCUBRIR ≠ ACEPTAR.
