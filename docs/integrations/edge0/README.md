# Edge0 ↔ ODS ↔ LEONES
**Perfil:** framework open-source de inferencia MoE streaming con offload SSD y predicción de routing.
**Estado LEONES:** 🟢 candidato P1 · ⏳ validación independiente pendiente.

## 1. Resumen
Edge0 explora inferencia MoE con memoria limitada mediante streaming de expertos desde SSD, predicción previa de rutas y Recover-LoRA. La idea central es desacoplar el backend de inferencia de la política de recuperación de expertos.

## 2. Arquitectura
`prompt/token → prerouter → predicción de expertos → SSD/cache → compute backend`.
Esta separación es interesante para ODS porque encaja con un Runtime Registry basado en capacidades.

## 3. Valor para ODS
ODS podría registrar Edge0 como runtime `moe-streaming`, seleccionándolo cuando el modelo supere VRAM/RAM y el almacenamiento tenga suficiente rendimiento. El servicio debería mantener una API estable aunque cambie el backend interno.

## 4. Backend y portabilidad
La implementación pública actual está especialmente orientada a MLX/Apple Silicon; CUDA aparece como dirección de extensión. Por tanto, en el equipo ODS NVIDIA no debe asumirse compatibilidad operativa sin una prueba específica.

## 5. Riesgos
- Estado de madurez.
- Dependencia de abstracciones/backend concreto.
- Beneficio del prerouter depende de localidad real del routing.
- SSD pasa a formar parte de la ruta crítica.

## 6. LEONES
Registrar backend, dispositivo, modelo, número de expertos, tasa de aciertos de predicción, cache hit, bytes SSD, TTFT/prefill/decode y calidad. Separar claramente resultados de paper/README de medidas locales.

## 7. Integración
Primera fase como servicio experimental fuera del camino por defecto. Si aparece backend CUDA estable, añadir manifest:
`moe=true, ssd=true, prediction=true, api=?`.
La API debe verificarse, no inferirse.

## 8. Veredicto
| Área | Evaluación |
|---|---|
| MoE streaming | 🟢 |
| SSD offload | 🟢 |
| Predictor | 🟢 Interesante |
| NVIDIA actual | 🟡 Pendiente |
| Apple | 🟢 |
| Madurez ODS | 🟡 Experimental |
| LEONES | 🟢 |

**Clasificación:** P1 — estudiar arquitectura y vigilar backend CUDA.
**Fuente:** https://github.com/Edge0-AI/Edge0