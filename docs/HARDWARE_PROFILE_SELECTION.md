# Hardware real → selección LEONES

La selección canónica puede alimentarse directamente de un perfil observado
por `scripts/hardware_profile.py`.

```text
Linux/Debian
    ↓
hardware_profile.py
    ↓
CPU + RAM disponible + GPU declarada + discos + red
    ↓
select_from_hardware_profile.py
    ↓
model_selector.py
```

## Principios

- La RAM usada para selección es la **disponible en el momento de la captura**,
  no una cifra inventada a partir del marketing del equipo.
- No se infiere VRAM desde el texto de `lspci`.
- El perfil observa CPU, RAM, GPU, almacenamiento y enlaces de red, pero no los
  convierte automáticamente en rendimiento de inferencia.
- Los benchmarks de CPU, memoria y disco quedan como mediciones opt-in.
- El selector sigue siendo la única fuente de decisión.

## Validación posterior

Una vez obtenido el perfil, la siguiente fase debe ejecutar mediciones reales:

1. CPU/FLOPS o métrica equivalente reproducible.
2. ancho de banda de memoria.
3. latencia/throughput de almacenamiento.
4. VRAM realmente disponible cuando exista GPU utilizable.
5. benchmark de inferencia del modelo seleccionado.

Esas mediciones pueden actualizar evidencia del Atlas, pero nunca deben alterar
retroactivamente el contrato de selección sin una nueva ejecución del selector.
