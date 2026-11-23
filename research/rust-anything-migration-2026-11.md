# rust-anything — investigación de migración diferencial a Rust

**Fecha:** 2026-11-21. **Estado:** investigación documental incorporada; no instalado ni ejecutado en LEONES.  
**Proyecto externo:** [erkamyaman/rust-anything](https://github.com/erkamyaman/rust-anything) · **Licencia declarada:** MIT.  
**Fuentes primarias:** [README](https://github.com/erkamyaman/rust-anything) · [How it works](https://github.com/erkamyaman/rust-anything/blob/main/docs/how-it-works.md) · [Status (2026-11-20)](https://github.com/erkamyaman/rust-anything/blob/main/docs/STATUS.md) · [Decisions](https://github.com/erkamyaman/rust-anything/blob/main/DECISIONS.md).

## 1. Dictamen

rust-anything merece una línea de investigación propia como **herramienta de migración incremental a Rust guiada por perfiles y verificación diferencial del comportamiento**.

No es un traductor automático ni una promesa de acelerar cualquier programa. El proyecto propone identificar primero dónde se consume el tiempo, elegir unidades con potencial, generar un puente para mantener la API original, registrar el comportamiento del programa existente y comprobar que la implementación Rust reproduce los casos registrados. La persona o su agente de programación escribe el código Rust.

**Hipótesis LEONES:** usarlo como instrumento opcional para estudiar migraciones pequeñas y justificadas por mediciones, con contratos de comportamiento y posibilidad de despliegue gradual. No adoptar una estrategia general de reescritura.

## 2. Funcionamiento y capacidades

El flujo documentado es:

1. `profile`: ejecuta una carga de trabajo con el profiler del lenguaje original para localizar funciones calientes, llamadores y oportunidades de batching.
2. `analyze`: identifica unidades, dependencias, riesgos semánticos, orden de portado y posibles puentes.
3. `bridge`: genera el crate Rust, bindings/wrapper y stubs manteniendo la interfaz que esperan los callers.
4. `record`: ejecuta el original con casos generados, trampas semánticas y entradas propias; guarda salidas, errores y, cuando se habilita, determinados efectos.
5. `build` + `diff`: compila la implementación Rust y reproduce los casos registrados para detectar divergencias.
6. `fuzz`: genera entradas nuevas para buscar huecos de cobertura.
7. `bench`: compara tiempos incluyendo el coste del puente.
8. `shadow`: ejecuta ambas implementaciones y devuelve la salida original mientras informa de diferencias.
9. `gate`: aplica formato, Clippy, tests, auditoría de `unsafe`, cobertura de errores y comprobaciones de API/comportamiento.
10. Para aplicaciones completas, `app record/replay`, front door, wiring y `app lift` permiten sustituir progresivamente unidades hasta una aplicación Rust pura cuando se cumplen las gates.

El proyecto integra CLI, servidor MCP y skills para agentes de programación. La instalación `setup` puede modificar la configuración local de varios agentes; no debe ejecutarse de forma implícita en equipos LEONES.

## 3. Alcance y madurez declarada por upstream

El estado upstream consultado el 2026-11-20 distingue explícitamente entre **Verified** (flujo ejecutado de extremo a extremo en código real de terceros), **Tested** (cubierto en fixtures/tests, sin ejecución real equivalente) y **Whole apps** (flujo de aplicación completa, todavía sin puente de unidades en algunos lenguajes).

| Lenguaje | Estado declarado en STATUS | Observación |
|---|---|---|
| TypeScript / JavaScript | Verified | Prettier, json-server, Fuse.js, vercel/ms y x18n; incluye CLI, servidor y librerías. |
| Python | Verified | Ejecución real sobre colorsys.py de CPython 3.13. |
| Go | Verified | Ejecución real sobre package path de Go 1.24. |
| Ruby | Verified | Ejecución real sobre shellwords.rb de Ruby 3.3. |
| Java | Verified | JDK 21 tras una fachada. |
| C | Verified | Unidades de libavutil/FFmpeg y glibc mediante fachada. |
| Kotlin | Tested | Fixtures; requisitos de toolchain y dispositivo limitan CI. |
| Kotlin / Android | Tested | Se declara una prueba de dispositivo con 279/291 casos coincidentes; 12 divergencias pendientes de investigación. |
| PHP | Whole apps | Análisis y flujo de aplicación; el puente de unidades está pendiente. |
| C# | Whole apps | Análisis y flujo de aplicación; el puente de unidades está pendiente. |
| C++ | No declarado | No tratarlo como soporte de portado de unidades C++. |

Estas señales de madurez son declaraciones del propio proyecto y no validaciones independientes de LEONES. Los resultados publicados por upstream sirven como motivación y referencia, no como benchmark reproducido.

## 4. Encaje potencial en LEONES

### Casos de interés

- **Utilidades y scripts Python:** estudiar unidades CPU-bound que tengan tests y límites claros, evitando portar código cuyo coste principal sea I/O o llamadas a procesos externos.
- **Herramientas TypeScript/JavaScript:** evaluar módulos de parsing, transformación, búsqueda o procesamiento de datos cuando el perfil real muestre una ruta caliente.
- **Componentes Go, Java o Ruby:** posible evaluación futura si LEONES incorpora o mantiene módulos de esos lenguajes.
- **Puentes y contratos:** explorar si el registro/replay diferencial puede reforzar la disciplina de compatibilidad al sustituir una implementación sin cambiar a sus consumidores.
- **Agentes de coding:** analizar su servidor MCP/skill como herramienta asistida, manteniendo las decisiones, permisos y gates bajo HDAE.

### Relación con proyectos existentes

- **LEONES Lab Agent:** ya es un proyecto Rust; rust-anything no es necesario para reescribirlo. Su valor aquí sería metodológico o para componentes auxiliares en otros lenguajes, no una dependencia de ejecución.
- **TensorFold Web:** candidato exploratorio sólo para módulos Python concretos si un perfil demuestra que merece la pena. No portar el servidor/UI por preferencia tecnológica.
- **Atlas, Router y observatorio web:** podrían evaluarse utilidades de datos o parsing si hay rutas críticas medibles y contratos de salida estables.
- **NEPENTHES / Tandem.cpp:** no es candidato directo para portar unidades C++; el soporte documentado para C no debe extrapolarse a C++. Mantener C++ y su toolchain específicos.
- **ODS / REDIL:** no sustituye sus funciones de despliegue, federación, serving ni observabilidad.

La oportunidad de mayor valor no es «todo en Rust», sino **mover el bucle caliente completo** cuando el perfil lo justifique. Una llamada FFI por elemento puede ser más lenta que el JIT; el batching mantiene los datos y el bucle dentro de Rust, pero debe medirse en el workload real.

## 5. Límites de la equivalencia y riesgos

La aceptación de `diff` significa que Rust coincide con los casos registrados, no que se haya demostrado equivalencia universal.

1. **Cobertura de entradas:** los casos generados, tests originales, datos reales y fuzzing determinan qué comportamiento se comprueba. Las entradas no registradas siguen siendo riesgo.
2. **Efectos secundarios:** `record` puede ejecutar código original muchas veces; las operaciones sobre archivos, bases de datos, HTTP o SMTP pueden repetirse. Algunos efectos se registran mediante opciones específicas, pero colas, señales y rutas de red fuera de la instrumentación pueden quedar sin comparar.
3. **No determinismo:** reloj, aleatoriedad, concurrencia y orden de colecciones necesitan tratamiento explícito. Los comodines introducidos para diferencias entre ejecuciones deben revisarse, no aceptarse a ciegas.
4. **Semántica entre lenguajes:** UTF-16/UTF-8, regex, números, overflow, orden de mapas, excepciones, reflexión y asincronía pueden producir divergencias difíciles.
5. **Métricas no cubiertas por equivalencia:** el replay no acredita por sí mismo rendimiento bajo carga, consumo de memoria, concurrencia ni comportamiento en otra plataforma.
6. **Actualización del original:** el proyecto guarda huellas de los ficheros registrados y advierte de grabaciones obsoletas; la campaña debe regenerar y revisar los casos cuando cambie la fuente.
7. **Ejecución de código:** los comandos ejecutan el programa original y la versión portada. Deben usarse copias de laboratorio, datos sintéticos/test, bases de datos desechables y entornos sin credenciales de producción.

## 6. Plan de evaluación por gates

### R0 — revisión documental (remoto)

- Fijar un commit/release concreto de upstream.
- Revisar licencia MIT, dependencias, matriz de lenguajes, decisiones de diseño y avisos de seguridad.
- Confirmar la semántica real de record/replay, efectos, shadow, fuzz y gates.

**Aceptación:** ficha de versión, matriz de capacidades y límites; sin instalación.

### R1 — selección de candidato (remoto)

- Inventariar módulos Python/TypeScript existentes que tengan tests y límites de API.
- Elegir sólo candidatos con perfil representativo o hipótesis medible.
- Excluir C++ como objetivo de portado directo y descartar código dominado por I/O, FFI o llamadas externas.

**Aceptación:** candidato con baseline, alcance pequeño, API y criterios de descarte.

### R2 — prueba aislada (entorno de laboratorio)

- Ejecutar en copia desechable, sin secretos ni servicios de producción.
- Registrar tests existentes y entradas reales anonimizadas, más casos de borde.
- Revisar cada wildcard, salida no determinista y efecto secundario.
- Comparar resultados y errores antes de considerar rendimiento.

**Aceptación:** replay completo de los casos aprobados, gate satisfactoria y limitaciones explícitas.

### R3 — benchmark controlado (MSI/CI según candidato)

- Comparar original y Rust con inputs, semántica, número de hilos y entorno equivalentes.
- Medir latencia, throughput, CPU, RSS, memoria, coste del puente y variabilidad.
- Incluir batching cuando proceda; medir también el modo por llamada.
- En el MSI, no requiere GPU: priorizar CPU, RAM y disco; registrar el entorno Ubuntu y la versión de toolchain.

**Aceptación:** mejora MEASURED que supere el coste de mantenimiento y del puente, sin regresiones de comportamiento.

### R4 — integración gradual

- Mantener la API original y usar shadow/fallback si el proyecto lo permite.
- Incorporar pruebas de contrato y detección de grabaciones obsoletas en CI.
- Documentar rollback y la propiedad de cada unidad portada.

**Aceptación:** PR revisado, CI verde, rollback probado y aceptación humana explícita.

## 7. Decisión provisional

- **Investigar:** sí; herramienta relevante para migraciones incrementales y verificación diferencial.
- **Instalar en MSI o agentes:** no autorizado por esta ficha.
- **Integrar como dependencia de LEONES:** no; mantener como herramienta externa opcional.
- **Portar componentes:** sólo después de perfilar y elegir un candidato pequeño con tests y entradas representativas.
- **Portar Tandem.cpp/NEPENTHES C++:** no mediante las capacidades de unidad actualmente declaradas.
- **Declarar mejoras de rendimiento:** sólo con benchmarks propios y protocolo equivalente.

## 8. Fuentes

- [Repositorio rust-anything](https://github.com/erkamyaman/rust-anything)
- [How it works](https://github.com/erkamyaman/rust-anything/blob/main/docs/how-it-works.md)
- [Status, actualizado 2026-11-20](https://github.com/erkamyaman/rust-anything/blob/main/docs/STATUS.md)
- [Decisions](https://github.com/erkamyaman/rust-anything/blob/main/DECISIONS.md)
- [MIT License](https://github.com/erkamyaman/rust-anything/blob/main/LICENSE)

**Límite de evidencia:** evaluación documental de fuentes upstream. No se ha instalado rust-anything, no se ha ejecutado sobre repositorios LEONES y no existe aún resultado MEASURED propio.
