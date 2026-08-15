# LEONES — Precios de hardware y motor de recomendación

## 1. Propósito

LEONES no utiliza el precio para decidir qué modelo de IA es mejor. El precio es una **dimensión independiente** que permite responder una pregunta práctica:

> ¿Qué combinación de CPU + RAM + GPU permite ejecutar un modelo y cuál es el coste de esa configuración?

La arquitectura mantiene separados tres dominios:

1. **Atlas de modelos**: identidad, familia, organización, licencia, apertura, JGB, benchmarks, runtime y evidencia.
2. **Perfil de hardware**: CPU, RAM, GPU/VRAM, contexto y workload.
3. **Base temporal de precios**: observaciones de mercado con fecha y fuente.

Esta separación evita que un cambio de precio modifique artificialmente la clasificación del modelo o su Índice JGB.

---

## 2. Matriz de hardware

El recomendador contempla inicialmente las categorías:

### CPU

- Intel Core i3
- Intel Core i5
- Intel Core i7
- Intel Core i9
- AMD Ryzen 3
- AMD Ryzen 5
- AMD Ryzen 7
- AMD Ryzen 9

Intel y AMD están emparejados por **categoría de gama**, no se afirma que un i5 concreto tenga el mismo rendimiento que cualquier Ryzen 5. El modelo exacto y la generación deben conservarse cuando exista evidencia.

### RAM

Se utilizan perfiles de:

- 2 GB
- 4 GB
- 8 GB
- 16 GB
- 32 GB
- 64 GB
- 128 GB

Para memoria se distingue además DDR4 de DDR5. La capacidad por sí sola no implica equivalencia técnica.

### GPU

Se mantiene un catálogo independiente de GPU NVIDIA orientadas a IA, con VRAM y precio orientativo. GPU y RAM no se suman como si fueran la misma memoria: la VRAM es un recurso distinto y puede ser el cuello de botella para inferencia local.

---

## 3. Base de precios

La base independiente es:

`data/hardware/hardware_prices.csv`

Cada observación debe conservar, como mínimo:

- identificador;
- tipo de componente;
- fabricante;
- categoría;
- modelo;
- capacidad;
- precio en EUR;
- tipo de precio;
- mercado;
- moneda;
- fuente/tienda;
- fecha de observación;
- fecha de validez, si existe;
- notas.

### Regla fundamental

**Nunca se debe convertir un precio desconocido en un precio estimado sin etiquetarlo explícitamente como estimación.**

Para comparaciones económicas fiables, el recomendador debe poder distinguir entre:

- precio observado;
- precio de referencia;
- estimación;
- precio no disponible;
- precio histórico.

---

## 4. Histórico, no sobrescritura

El precio cambia. Por ello la base está concebida como una serie de observaciones temporales.

Ejemplo conceptual:

```text
RTX X — 2026-08 — 599 €
RTX X — 2026-09 — 559 €
RTX X — 2026-10 — 519 €
```

No debe sustituirse silenciosamente el primer registro por el tercero. El histórico permite estudiar:

- depreciación;
- ofertas;
- tendencia mensual;
- coste por GB de VRAM;
- coste por rendimiento;
- puntos de entrada económicos para IA local.

---

## 5. Bot mensual

El workflow es:

`.github/workflows/monthly-hardware-prices.yml`

Nombre visible en GitHub:

**Precios hardware — actualización mensual**

Horario programado:

`04:23 UTC` el día 1 de cada mes.

También dispone de `workflow_dispatch` para una ejecución manual.

El bot utiliza:

`scripts/update_hardware_prices.py`

La función actual del bot es de **control de cobertura e integridad**: revisa que las categorías objetivo estén representadas y que exista el catálogo NVIDIA. No inventa precios ni sobrescribe datos históricos.

### Evolución prevista del bot

La capa de colección debe incorporar adaptadores de fuentes de precio autorizadas y estables. Cada adaptador tendrá que devolver:

```text
modelo
precio_eur
mercado
fuente
url
fecha_observacion
```

Si una fuente no responde, cambia su estructura, bloquea el acceso o no proporciona una coincidencia inequívoca, el bot debe marcar el dato como no actualizado y conservar el último dato válido.

**Un fallo de una fuente nunca debe convertirse en un precio falso.**

---

## 6. Fuentes y trazabilidad

Los precios observados en el desarrollo se consideran datos de mercado, no propiedades técnicas del componente. Las fuentes se guardan junto a la observación.

Para el mercado español se priorizarán fuentes comerciales con precios visibles y fecha de consulta. Cuando sea posible se utilizarán también APIs o feeds estructurados, porque son más robustos que raspar HTML.

Los precios publicados en este proyecto son orientativos y pueden variar por:

- fabricante de la tarjeta;
- ensamblador;
- tienda;
- disponibilidad;
- promociones;
- IVA;
- condición nueva/reacondicionada;
- momento de consulta.

---

## 7. Precio y recomendador

El precio **no sustituye al Índice JGB**.

El flujo conceptual es:

```text
                 MODELO
                   │
       ┌───────────┼───────────┐
       ▼           ▼           ▼
      JGB       Evidencia    Benchmarks
       │           │           │
       └───────────┼───────────┘
                   ▼
              COMPATIBILIDAD
                   │
        ┌──────────┴──────────┐
        ▼                     ▼
     CPU/RAM               GPU/VRAM
        │                     │
        └──────────┬──────────┘
                   ▼
             CONFIGURACIÓN
                   │
                   ▼
                PRECIO
                   │
                   ▼
          RECOMENDACIÓN EXPLICABLE
```

Una recomendación puede ser técnicamente válida pero cara. Otra puede ser menos potente pero ofrecer una relación coste/rendimiento mucho mejor. Ambas dimensiones deben conservarse.

---

## 8. Métricas económicas previstas

Una vez exista evidencia suficiente de precio y rendimiento, el motor podrá calcular:

- coste total de configuración;
- €/GB de VRAM;
- €/GB de RAM;
- €/token/s;
- coste por unidad de benchmark;
- coste por capacidad de modelo desplegable;
- coste/rendimiento por workload;
- ahorro frente a una configuración alternativa;
- evolución mensual del coste.

Estas métricas solo deben aparecer cuando las variables necesarias estén verificadas.

---

## 9. Relación con JGB

El Índice JGB es una dimensión de apertura/libertad y **no debe degradarse a una puntuación económica**.

Una configuración barata con un modelo de JGB alto no se convierte automáticamente en una recomendación superior. El recomendador debe explicar por separado:

1. **libertad/apertura** — JGB;
2. **capacidad técnica** — benchmarks y evidencia;
3. **desplegabilidad** — hardware, memoria, VRAM, runtime y cuantización;
4. **coste** — precio temporal de hardware;
5. **adecuación al workload**.

---

## 10. Ejecución verificada del recomendador

La ejecución comprobada del pipeline diario del Atlas terminó correctamente con todos sus pasos:

```text
Descargar repositorio              OK
Preparar Python                    OK
Ingerir descubrimientos NDJSON     OK
Normalizar feed                    OK
Generar recomendaciones            OK
Publicar resultados                OK
```

El pipeline genera recomendaciones por perfiles de hardware y publica los resultados cuando existen cambios.

El precio no se incorpora todavía como criterio de puntuación automática hasta que la observación de precios tenga cobertura y trazabilidad suficientes. Esta decisión evita que datos incompletos de mercado contaminen el ranking.

---

## 11. Principio de calidad

El sistema debe preferir:

> **"No lo sé todavía"**

frente a:

> **"Tengo que rellenar el campo para poder recomendar."**

Esto se aplica tanto a precio como a memoria, VRAM, runtime, cuantización, rendimiento, benchmarks y JGB.

El recomendador de LEONES pretende ser un sistema de decisión explicable y reproducible, no una tabla de números aparentando una precisión que las fuentes no permiten.
