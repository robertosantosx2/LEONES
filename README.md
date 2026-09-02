# LEONES

## Instalación mínima

Para un beta tester, el punto de entrada es ahora mínimo:

```bash
# 0) LLMFit es dependencia dura (LEONES no lo instala)
curl -fsSL https://llmfit.axjns.dev/install.sh | sh -s -- --local
export PATH="$HOME/.local/bin:$PATH"

# 1) LEONES
git clone https://github.com/robertosantosx2/LEONES.git
cd LEONES
./install.sh
./leones
```

**Manual corto:** [INSTALL.md](INSTALL.md)  
**Inicio rápido (web):** [web/inicio-rapido.html](web/inicio-rapido.html)  
**Manual RC2 completo:** [docs/RC2-INSTALLATION-MANUAL.md](docs/RC2-INSTALLATION-MANUAL.md)  
**Manual de usuario:** [docs/RC2-USER-MANUAL.md](docs/RC2-USER-MANUAL.md)

`install.sh` sólo comprueba Git, Python y **LLMFit**. No crea un entorno virtual ni descarga ODS, Magnitude ni modelos. `leones` es el lanzador único del wizard RC2.

Si falta LLMFit, el instalador falla de forma explícita y muestra el comando de instalación oficial.

## Estado del proyecto

| Bloque | Estado | Resultado |
|---|---|---|
| V1 / A01 | 🟢 Cerrado | Cadena real de selección → ejecución → benchmark → evidencia |
| JALÓN 1 | 🟢 Cerrado | Base CI y contratos iniciales |
| JALÓN 2 | 🟢 Cerrado | Ejecución física + evidencia reproducible con llama.cpp |
| JALÓN 3 | 🟢 Cerrado | Contrato de medición real + auditoría física |
| JALÓN 4 | 🟢 **Cerrado** | Metodología AA + contrato LEONES → ODS/Magnitude + benchmark de tareas + tiers |
| RC1 | 🟢 **Validado** | Ejecución efectiva end-to-end: selección → gate → Ollama → A01 → medición → evidencia |
| RC2-A | 🟢 **Validado** | Orquestación beta: hardware → candidatos → modelo → ODS/Magnitude → consentimiento |
| RC2-B → RC2-H | 🟡 **En validación física** | Instalación, verificación, benchmark opcional, resultado y piloto externo |

## RC2 — flujo de usuario beta

```text
INSTALAR → HARDWARE → PERFILAR → CANDIDATOS → ELEGIR MODELO
          → COMPARAR ODS/MAGNITUDE → ELEGIR STACK → PLAN
          → CONSENTIMIENTO → INSTALAR → VERIFICAR
          → ¿BENCHMARK? → SÍ: RUNNER RC1 → MEDICIÓN → EVIDENCIA
                         → NO: FIN
```

### RC2-A — validado

El wizard ASCII demuestra la capa de decisión y consentimiento. La suite local está verde: **334 tests passed**.

LLMFit aporta la inteligencia especializada de hardware/model-fit. Sus cifras de rendimiento permanecen marcadas como `estimated`; no son evidencia física.

### RC2-B y siguientes — validación física

El trabajo restante es físico: instalar/verificar el stack elegido en una máquina real, ejecutar los health checks, decidir si se autoriza el benchmark y, si procede, reutilizar el runner canónico de RC1 para generar evidencia nueva.

La detección del runtime de contenedores no presupone Docker rootless. RC2 distingue **Docker directo**, **Docker mediante sudo**, **Docker rootless** y **Podman**. En Fedora/RHEL-family, Podman puede estar presente sin que eso implique automáticamente que ODS esté listo: el runtime del host y la compatibilidad efectiva de ODS son estados separados.

Durante instalaciones largas, LEONES debe mantener actividad visible. El porcentaje mostrado debe representar fases reales del flujo de LEONES; no se debe inventar un porcentaje interno de un instalador externo que no lo proporcione.

Un fallo de conectividad o del instalador externo debe quedar como fallo explícito de instalación, conservando el error original y sin avanzar al benchmark.

LEONES **no crea otro instalador de ODS ni otro instalador de Magnitude, ni otro runner RC2**. Reutiliza los proyectos y runners canónicos.

## Documentación RC2

- [INSTALL.md](INSTALL.md) — instalación mínima para beta testers (incluye LLMFit).
- [Inicio rápido](web/inicio-rapido.html) — arranque, teclas y decisiones.
- [Manual de instalación RC2](docs/RC2-INSTALLATION-MANUAL.md) — procedimiento técnico completo.
- [Manual de usuario RC2](docs/RC2-USER-MANUAL.md) — recorrido en lenguaje de usuario.
- [Flujo contractual RC2](docs/RC2-BETA-USER-FLOW.md) — gates y estados.
- [Instalación/consentimiento](docs/RC2-I-INSTALLATION-CONSENT.md) — autorización.
- [Benchmark/hand-off](docs/RC2-J-BENCHMARK-CONSENT.md) — entrega al runner canónico.
- [Integración LLMFit](docs/integrations/LLMFIT.md) — frontera de responsabilidad y procedencia.

### Regla para beta testers

Cada máquina debe producir su propia evidencia: nuevo `execution_id`, timestamp, métrica y procedencia. Una medición histórica nunca sustituye una ejecución actual.

## Arquitectura

LLMFit es la fuente especializada de inteligencia hardware/model-fit. LEONES consume su salida JSON, conserva la procedencia y normaliza candidatos. Sus estimaciones permanecen como `estimated`; una medición física de LEONES sólo nace de una ejecución real del runner/protocolo correspondiente.

ODS se utiliza como integración de stack local y Magnitude como integración de agente/asistente. RC2 mantiene separadas recomendación, instalación y benchmark.
