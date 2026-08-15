# Descubrimiento de hardware local

LEONES no debe inferir la capacidad de una máquina únicamente a partir de CPU/GPU/RAM nominales.

El script `scripts/hardware_discovery.py` está pensado para ejecutarse **en la máquina del usuario** y generar un perfil técnico sin datos personales.

## Qué obtiene

### CPU
- arquitectura;
- modelo;
- núcleos/hilos;
- frecuencia disponible;
- flags SIMD;
- medición opcional de MFLOPS/GFLOPS mediante NumPy.

La medición FLOPS se conserva como **medición del benchmark concreto**, no como especificación universal del procesador.

### Memoria
- capacidad;
- medición de throughput de copia cuando NumPy está disponible.

El Atlas conservará por separado:
- capacidad;
- bandwidth teórico;
- bandwidth medido;
- latencia;
- método de medida.

### GPU
Se obtiene el dispositivo PCI cuando Linux lo expone. La identificación detallada de VRAM y rendimiento puede requerir herramientas específicas del fabricante/backend.

### Almacenamiento
Se obtiene el dispositivo y su transporte (por ejemplo NVMe/PCIe, SATA, USB cuando el sistema lo exponga).

La capacidad y el tipo de disco **no son suficientes**: el rendimiento depende también del protocolo, bus, enlace y conexión a la placa base. Por ello el modelo de hardware permite registrar throughput secuencial/aleatorio, latencia, interfaz, protocolo y enlace como mediciones independientes.

## Privacidad

No se debe enviar a Atlas/MANADA:
- hostname;
- número de serie;
- UUID;
- MAC/IP;
- ubicación exacta;
- credenciales/tokens;
- rutas privadas.

## Flujo

```text
máquina del usuario
      ↓
hardware_discovery.py
      ↓
perfil técnico anonimizado
      ↓
MANADA (reported)
      ↓
reproducción / revisión
      ↓
Atlas (reproducible / verified)
```

El perfil local no se considera verificado por el mero hecho de haber sido generado por el script.
