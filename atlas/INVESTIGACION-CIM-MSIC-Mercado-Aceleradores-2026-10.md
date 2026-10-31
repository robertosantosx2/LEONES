# Investigación: Mercado de Compute-in-Memory (CIM) y Chips de Señal Mixta (MSIC)

**Fecha:** Octubre 2026  
**Enfoque:** Opciones comerciales de chips/tarjetas físicas listas para instalar como aceleradores de hardware de IA.

## Resumen del mercado

El mercado de comercialización de tecnología Compute-in-Memory (CIM) y chips de señal mixta (MSICs) está dividido en dos grandes bloques:

1. **Gigantes tecnológicos** que integran CIM/PIM en sus líneas de memoria tradicionales (Samsung, SK hynix, Micron).
2. **Startups disruptivas** que venden silicio especializado para acelerar la Inteligencia Artificial (d-Matrix, EnCharge AI, Syntiant, Axelera AI).

## Empresas y productos con disponibilidad comercial (Octubre 2026)

### 1. Startups Especializadas (Edge AI y Centros de Datos)

#### Axelera AI (Países Bajos) – **Más fácil de comprar hoy**
- **Producto:** Metis AIPU (Digital In-Memory Compute)
- **Formato:** M.2 2280 y PCIe HHHL (1 o 4 chips); Compute Board SBC; sistemas completos.
- **Disponibilidad:** Tienda oficial + distribuidores (Mouser). Stock y envío rápido.
- **Prestaciones:** Hasta 214 TOPS INT8 por chip (~15 TOPS/W); 4-15 W típicos; hasta ~3200 FPS ResNet-50.
- **Modelos de IA:** Visión computacional (YOLOv5/v7/v8, SSD-MobileNet, EfficientNet, detección de objetos, clasificación, pose). Soporta hasta ~8B parámetros LLM por chip (limitado).
- **Precios aproximados (ex-VAT):**
  - M.2: ~$250-300
  - PCIe 1-chip 4 GB: ~$380
  - PCIe 1-chip 16 GB: ~$610-700
  - 4-chip / sistemas: desde ~$1.800+
- **Enlace:** https://store.axelera.ai

#### Syntiant – Edge ultra-bajo consumo
- **Producto:** Neural Decision Processors (NDP115, NDP120, NDP200, NDP250)
- **Formato:** Chips embebidos (WLBGA/QFN) + kits de evaluación.
- **Disponibilidad:** Producción masiva. Kits en DigiKey, Avnet, Farnell.
- **Prestaciones:** Microvatios a pocos mW; 100x eficiencia vs MCU tradicionales.
- **Modelos de IA:** Audio/voz (keyword spotting, ASR, noise reduction), sensores, visión básica.
- **Precios:**
  - Chip NDP115 (volumen): ~$3-4
  - NDP120 (volumen): ~$6-9
  - Kits evaluación: ~$37 (TinyML) a ~€60-170 (RASynBoard)

#### d-Matrix – Data-center inference de baja latencia
- **Producto:** Corsair (Digital In-Memory Compute / DIMC, SRAM-based)
- **Formato:** PCIe Gen5 FHFL; racks de referencia (SquadRack).
- **Disponibilidad:** Full production desde junio 2026. Envíos de volumen a clientes prioritarios (hyperscalers, neoclouds, frontier labs). **No retail público.**
- **Prestaciones:** ~2.400 TFLOPS 8-bit / 9.600 TFLOPS 4-bit por tarjeta; 2 GB SRAM on-chip (~150 TB/s) + hasta 256 GB LPDDR; 600 W TDP. Claims de 10x interactivo en decode vs GPU-only.
- **Modelos de IA:** Inferencia de LLMs (Llama 3 8B/70B y similares); foco en fase de decode/token generation. Complementa GPUs.
- **Precio:** No público. Contact sales. Estimaciones de decenas de miles de dólares por tarjeta/sistema.

#### EnCharge AI – Analog CIM de alta eficiencia
- **Producto:** EN100 (Analog In-Memory Compute basado en capacitores)
- **Formato:** M.2 (laptops) y PCIe (workstations, 4 NPUs).
- **Disponibilidad:** Early Access Program (rondas para developers/OEMs). **No venta retail abierta.**
- **Prestaciones:** >200 TOPS a 8,25 W (M.2); ~1 PetaOPS PCIe (~40 W); claims hasta 20x mejor perf/W.
- **Modelos de IA:** Inferencia on-device multimodal, agentes, visión + transformers; modelos de frontera en edge/client.

### 2. Gigantes de Semiconductores (Integración en DRAM/Flash)

- **Samsung Electronics:** HBM-PIM y LPDDR5X-PIM. Disponible a través de partners de sistemas (AMD Instinct, etc.). Mejora ~2x rendimiento y reduce energía >70% en workloads AI.
- **SK hynix:** AiM / AiMX (basado en GDDR6). Demostrado con GPUs para LLMs (attention/KV-cache). Disponible vía integradores de servidores.
- **Micron Technology:** Módulos y memorias de próxima generación con computación interna. Orientado a partners.

### 3. Proveedores de IP (no chip físico)
- Crossbar Inc. y Weebit Nano: Licencian ReRAM para matrices analógicas CIM.
- Synthara: IP de señal mixta para integrar CIM en microcontroladores RISC-V.

## Qué se puede comprar hoy día (31 Oct 2026)

| Prioridad | Producto | Formato | Acceso | Uso principal |
|-----------|----------|---------|--------|---------------|
| **Más fácil** | Axelera Metis | M.2 / PCIe | Tienda online + distribuidores | Visión edge, multi-cámara, industrial |
| **Barato / edge** | Syntiant NDP | Chip + kits | DigiKey, Avnet, Farnell | Audio, sensores, always-on |
| **Enterprise** | d-Matrix Corsair | PCIe / racks | Contact sales (clientes prioritarios) | LLM inference data-center baja latencia |
| **Early access** | EnCharge EN100 | M.2 / PCIe | Programa Early Access | Máxima eficiencia on-device |

## Conclusiones y recomendaciones

- **Para hardware físico listo e instalable ya:** Axelera Metis es la opción más práctica y transparente.
- **Para ultra-bajo consumo edge:** Syntiant.
- **Para data-center de alto rendimiento en LLMs:** d-Matrix (requiere calificación comercial).
- El software (SDK, cuantización, toolchains) es crítico; no todos los modelos corren “out-of-the-box” sin optimización.
- Analog CIM (EnCharge) ofrece eficiencia extrema pero requiere más cuidado con precisión que las soluciones digitales.

## Fuentes principales
- Sitios oficiales de d-Matrix, EnCharge AI, Syntiant, Axelera AI.
- Anuncios de producción y disponibilidad 2025-2026.
- Distribuidores (Mouser, DigiKey, Avnet, Farnell).
- Cobertura técnica (Hot Chips, ISSCC, análisis independientes).

---

*Documento generado como investigación para el proyecto LEONES (Libre Open Agent Stack). Actualizado a 31 de octubre de 2026.*
