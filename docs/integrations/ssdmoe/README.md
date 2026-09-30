# SSD MoE ↔ ODS ↔ LEONES
**Perfil:** inferencia MoE streaming desde SSD, con lector C nativo y endpoints OpenAI-compatible.
**Estado LEONES:** 🟢 candidato P1/P2 · ⏳ validación pendiente.

## 1. Resumen
SSD MoE investiga una ruta directa desde almacenamiento hacia el runtime de expertos. Documenta Qwen3.5-35B-A3B y Nemotron-H 30B-A3B, evitando cargar el checkpoint completo en RAM.

## 2. Arquitectura
Incluye index builder y lector de expertos nativo, trabajando sobre shards safetensors originales. Esto reduce la necesidad de mantener una segunda copia convertida y puede simplificar la cadena de modelos.

## 3. ODS
El principal atractivo es un backend especializado con endpoints OpenAI-compatible. La integración debería aislar el almacenamiento del modelo en un volumen dedicado y declarar explícitamente que el storage es parte de la capacidad del runtime.

## 4. Hardware
Las pruebas públicas están principalmente en Apple Silicon. Para NVIDIA/Ubuntu la compatibilidad debe verificarse. La separación entre lector y compute puede facilitar una futura adaptación.

## 5. Riesgos
Madurez, cobertura de plataformas y dependencia de rendimiento SSD. La misma ruta que permite modelos grandes puede hacer que una máquina con NVMe lento resulte inutilizable.

## 6. LEONES
Medir lectura por token, cache hit, ancho de banda, RAM, contexto, TTFT/prefill/decode y calidad. Comparar con una implementación convencional cuando sea posible.

## 7. Veredicto
| Área | Evaluación |
|---|---|
| SSD streaming | 🟢 Muy alto |
| OpenAI API | 🟢 |
| MoE modernos | 🟢 |
| NVIDIA | 🟡 |
| Apple | 🟢 |
| Producción ODS | 🟡 |
| Investigación | 🟢 |

**Clasificación:** P1/P2 — candidato de investigación con potencial de backend.
**Fuente:** https://github.com/RasoulNik/ssdmoe