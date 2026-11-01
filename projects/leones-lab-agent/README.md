# LEONES Lab Agent

Agente local en Rust para diagnóstico, inventario y experimentación reproducible dentro del ecosistema LEONES.

**Estado:** fase 1 — esqueleto CLI y diagnóstico de solo lectura.  
**Plataforma inicial:** Ubuntu Linux.  
**Licencia:** AGPL-3.0-only, conforme a la licencia raíz de LEONES.

## Principios

1. **Local-first:** el agente comienza trabajando sobre el equipo donde se ejecuta.
2. **Evidencia explícita:** inventario, estimación y medición son categorías distintas.
3. **No destructivo por defecto:** fase 1 no instala, descarga, borra, inicia ni detiene servicios.
4. **Autorización humana:** futuras operaciones con efectos laterales requerirán una política de permisos explícita.
5. **Reproducibilidad:** los informes identifican el alcance y los límites de cada captura.

## Compilar

Requiere Rust/Cargo estable. La fase 1 no tiene dependencias externas.

Desde la raíz del repositorio LEONES:

\`\`\`bash
cd projects/leones-lab-agent
cargo fmt --check
cargo test
cargo build --release
\`\`\`

Ejecutar:

\`\`\`bash
./target/release/lab-agent help
./target/release/lab-agent doctor
./target/release/lab-agent engines
./target/release/lab-agent models
./target/release/lab-agent report
\`\`\`

El comando report acepta una ruta opcional:

\`\`\`bash
./target/release/lab-agent report /tmp/leones-lab-agent-report.md
\`\`\`

## Comandos de la fase 1

| Comando | Función |
|---|---|
| doctor | SO, kernel, CPU, RAM, GPU NVIDIA y CUDA Toolkit |
| engines | Busca ejecutables conocidos en PATH |
| models | Lista repositorios de la caché Hugging Face estándar |
| report [RUTA] | Genera un informe Markdown |
| version | Muestra la versión |

## Límites conocidos

- La detección de motores se basa en ejecutables presentes en PATH; no confirma que un servidor esté activo.
- La detección de modelos solo inspecciona ~/.cache/huggingface/hub.
- La consulta de GPU usa nvidia-smi; no se inspeccionan APIs de otros fabricantes todavía.
- No se recorre el disco completo ni se inspeccionan directorios arbitrarios.
- No se ejecutan modelos ni benchmarks en esta fase.

## Próximos hitos

- Fase 1.1: inventario estructurado JSON y manifiesto de entorno.
- Fase 2: adaptadores de benchmark con límites de recursos y consentimiento explícito.
- Fase 3: proveedor LLM configurable (API OpenAI-compatible local o remota).
- Fase 4: planificador y ejecutor con permisos por herramienta.
- Fase 5: exportación de evidencia y documentación hacia LEONES.

## Desarrollo

\`\`\`bash
cargo fmt
cargo test
cargo clippy -- -D warnings
\`\`\`
