# Integraciones LEONES: ODS y Magnitude

Estas integraciones convierten dos productos externos en **perfiles instalables y medibles** sin convertirlos en dependencias estructurales de LEONES.

- **ODS — Servidor de Stacks IA**: despliega una pila local completa alrededor de inferencia, UI, agentes, RAG, workflows, voz e imagen.
- **Magnitude — Asistente personal IA**: instala un agente de coding local con motor de inferencia propio, perfilado de hardware y recomendación de modelos.

## Regla de frontera

ODS y Magnitude siguen siendo responsables de su instalación, runtime y comportamiento interno. LEONES se ocupa de:

1. preflight;
2. consentimiento;
3. instalación reproducible;
4. captura de configuración;
5. validación independiente;
6. benchmark;
7. separación `estimated` / `measured`;
8. publicación de evidencia solo con el consentimiento correspondiente.

La instalación **no implica telemetría**. La captura de datos es explícita y opt-in.

## Documentación

- [ODS](ODS/README.md)
- [Magnitude](Magnitude/README.md)
- [Matriz de instalación por dispositivo](IN-DEVICE-INSTALLATION-MATRIX.md)
- [Contrato de datos](DATA-CONTRACT.md)
- [Plan E2E](E2E.md)

## Flujo común

```text
PREFLIGHT
   ↓
CONSENTIMIENTO
   ↓
INSTALACIÓN CONTROLADA
   ↓
HEALTH / STATUS
   ↓
CAPTURA DE CONFIGURACIÓN
   ↓
BENCHMARK LEONES
   ↓
ESTIMATED ≠ MEASURED
   ↓
EVIDENCIA ATLAS (solo con consentimiento)
```
