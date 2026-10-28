# Migasfree: análisis de autores, proyectos y plan de promoción

**Fecha:** 28 de octubre de 2026  
**Estado:** propuesta estratégica; requiere validación técnica y editorial del equipo de Migasfree.  
**Inspiración:** [Fun with migasfree](https://fun-with-migasfree.readthedocs.io/es/master/).  
**Repositorio:** [github.com/migasfree](https://github.com/migasfree).

## 1. Resumen ejecutivo

Migasfree tiene una historia divulgativa potente: parte de una necesidad operativa real —gestionar software en una flota de equipos—, se desarrolla en un contexto público y comparte conocimiento mediante software libre. La promoción debe mostrar problemas concretos y procedimientos demostrables, no limitarse a enumerar funciones.

Se propone una campaña coordinada de cuatro líneas:

1. **Folletos:** comunicar el valor en 30 segundos y ofrecer una explicación técnica en cuatro páginas.
2. **Presentaciones y demos:** demostrar un caso reproducible, desde la preparación de un cambio hasta la comprobación del resultado.
3. **Comunicaciones:** mantener un relato coherente en la web, GitHub, comunidades, eventos y contactos institucionales.
4. **Podcast:** dar voz a autores, administradores y usuarios para contar decisiones, experiencias y aprendizajes.

La regla editorial será producir una fuente canónica de contenidos verificados y reutilizarla en todos los formatos. No se presuponen cifras de adopción, ahorros o rendimiento: cualquier dato cuantitativo deberá proceder de una fuente autorizada, con metodología y contexto.

## 2. Qué se promociona

**Mensaje principal propuesto:**

> Migasfree ayuda a gestionar y desplegar software en una flota de equipos de forma centralizada, planificada y auditable.

**Versión breve:**

> Controla qué software llega a cada equipo, cuándo llega y cómo comprobar el resultado.

Ambas formulaciones son borradores que debe validar el equipo del proyecto para ajustarlas a las capacidades de la versión vigente.

### Problemas que conectan con el público

- Mantener software coherente en muchos equipos.
- Distribuir cambios sin perder control de destinatarios y tiempos.
- Reducir tareas repetitivas y errores manuales.
- Disponer de información de inventario y cambios cuando la configuración lo permita.
- Planificar migraciones y diagnosticar incidencias.
- Preservar conocimiento técnico y evitar dependencia de procedimientos individuales.

No prometer cero incidencias, automatización total ni compatibilidad universal. Explicar requisitos, límites y costes de adopción.

## 3. Audiencias y mensajes

| Audiencia | Mensaje prioritario | Pieza y llamada a la acción |
|---|---|---|
| Dirección y responsables TIC | Control, previsibilidad, requisitos y coste total | Folleto ejecutivo; solicitar una sesión |
| Administradores de sistemas | Flujo real, configuración, diagnóstico y auditoría | Demo y guía técnica |
| Administraciones públicas | Planificación, trazabilidad y software libre | Caso de uso y charla |
| Educación y universidades | Preparación de aulas, laboratorios y equipos | Ficha sectorial y demostración |
| Integradores y servicios TIC | Arquitectura, operación y mantenimiento | Dossier técnico |
| Desarrolladores y comunidad | Cómo encontrar tareas y contribuir | Guía de contribución |
| Compras y dirección no técnica | Beneficios, riesgos, requisitos y transición | Resumen y FAQ |

No usar un único folleto para todos los públicos. Mantener consistentes las afirmaciones técnicas y cambiar ejemplos, profundidad y llamada a la acción.

## 4. Autores, historia y proyectos

### 4.1 La historia como activo

La documentación histórica *Fun with migasfree* combina el problema operativo original, la solución práctica y la publicación del conocimiento como software libre. Su valor editorial está en explicar el porqué, mostrar ejemplos, reconocer a las personas y acompañar al lector desde los primeros conceptos hasta el uso.

Debe tratarse como historia y referencia didáctica, no como guía automática de instalación actual. Comandos, versiones, dependencias, sistemas compatibles y recomendaciones de seguridad requieren verificación independiente.

### 4.2 Reconocimiento responsable de autores

Antes de producir perfiles o entrevistas:

- Revisar los agradecimientos y atribuciones de la documentación original.
- Contrastar nombres, fechas, cargos y contribuciones.
- Diferenciar autoría, mantenimiento, operación, documentación, empaquetado, traducción y comunidad.
- Invitar a participar; no asumir que una mención histórica equivale a disponibilidad o aval institucional actual.
- Solicitar consentimiento para entrevistas, citas, fotografías y grabaciones.
- Ofrecer revisión de citas y contexto antes de publicar.

**Preguntas de entrevista sugeridas:**

- ¿Qué problema concreto dio origen a Migasfree?
- ¿Qué tareas eran manuales y propensas a errores?
- ¿Qué decisión técnica resultó más importante?
- ¿Qué ha cambiado desde las primeras versiones?
- ¿Qué no debería esperar una organización del producto?
- ¿Qué necesita comprobar antes de ponerlo en producción?
- ¿Cómo puede contribuir alguien que no programa?
- ¿Qué documentación falta o resulta difícil de seguir?

### 4.3 Mapa del ecosistema

Organizar los repositorios públicos por la tarea que cumplen, verificando sus nombres y estado antes de publicar:

- Servidor y API.
- Consola o interfaz de administración.
- Cliente GNU/Linux y componentes de escritorio.
- Herramientas de instalación, operación y migración.
- Componentes relacionados con Windows o gestión de paquetes, si su estado actual lo respalda.
- SDK, API e integraciones.
- Ejemplos, plantillas y documentación.
- Proyectos históricos o archivados.

No asumir que todos los repositorios tienen la misma madurez. Cada ficha de proyecto debe indicar propósito, relación con Migasfree, estado de mantenimiento, sistemas/versiones probados, requisitos, licencia, última versión verificada, limitaciones, guía de prueba, documentación y canal de incidencias.

### 4.4 Ficha editorial de cada repositorio

- Nombre y URL oficial.
- Problema que resuelve y audiencia.
- Estado: activo, mantenimiento, experimental, histórico o archivado; validar con mantenedores.
- Sistemas y versiones comprobados.
- Requisitos y dependencias.
- Licencia y versión verificadas.
- Prueba mínima reproducible.
- Limitaciones conocidas.
- Documentación y canal de soporte.
- Contacto público autorizado.
- Mensaje promocional aprobado y fecha de revisión.

## 5. Inspiración en “Fun with migasfree”

### Conservar

- Tono humano, cercano y didáctico.
- Humor moderado, sin trivializar seguridad ni incidencias.
- Ejemplos concretos y progresivos.
- Reconocimiento al trabajo de desarrollo, operación y documentación.
- Glosario para explicar la terminología.
- Honestidad sobre el contexto histórico y la evolución del producto.
- La idea de convertir muchas experiencias individuales en conocimiento compartido.

### Actualizar

- Comprobar comandos, capturas, dependencias, arquitectura y requisitos.
- Separar guías de legado de instrucciones actuales.
- Añadir versión objetivo y fecha de verificación a las guías técnicas.
- Mantener HTML como fuente canónica y derivar PDF y otros formatos.
- Incorporar accesibilidad: contraste, texto alternativo, subtítulos y transcripciones.
- Revisar licencias y permisos antes de reutilizar texto, logotipos, diagramas, imágenes o fragmentos. La licencia exacta de cada material debe confirmarse en su aviso vigente.

**Promesa editorial propuesta:** “Te mostramos el problema, el procedimiento, el resultado y lo que hemos aprendido”.

Frases de trabajo (no eslóganes oficiales):
- “El software correcto, en los equipos adecuados y en el momento previsto.”
- “Menos tareas repetidas. Más control sobre los cambios.”
- “Software libre, experiencia real y conocimiento compartido.”

## 6. Plan de folletos

### A. Folleto ejecutivo de dos caras

Público: dirección, responsables TIC y compras.

1. Titular orientado al resultado.
2. Problema de gestionar una flota diversa.
3. Cómo ayuda Migasfree, con capacidades verificadas.
4. Diagrama: preparar → asignar → desplegar → comprobar.
5. Tres casos de uso con límites.
6. Requisitos de evaluación: infraestructura, compatibilidad, tiempo técnico y formación.
7. QR a documentación actual, demo o contacto oficial.

Criterio de éxito: el lector explica qué problema aborda y cuál sería su siguiente paso.

### B. Guía técnica de cuatro páginas

- Arquitectura vigente y fecha de verificación.
- Flujo de sincronización y despliegue.
- Proyectos, atributos, inventario y auditoría con terminología actual.
- Requisitos y compatibilidad.
- Demo reproducible.
- Limitaciones, riesgos y evaluación.
- Cómo reportar errores y contribuir.

No copiar comandos históricos sin comprobarlos ni usar métricas sin evidencia.

### C. Fichas sectoriales

Preparar variantes para administración pública, educación, equipos distribuidos e integradores. Cambiar los casos y el vocabulario; mantener intactas las afirmaciones técnicas aprobadas.

### Diseño y distribución

PDF accesible, versión HTML, QR estable, fecha y versión del material, enlaces descriptivos y tiradas impresas pequeñas tras validar primero el contenido digital.

## 7. Presentaciones y demostraciones

### Presentación ejecutiva (8–10 diapositivas)

1. Problema de gestionar una flota.
2. Qué es Migasfree en una frase.
3. Escenario representativo.
4. Preparación de un cambio.
5. Selección de equipos destinatarios.
6. Planificación y distribución.
7. Comprobación del resultado y diagnóstico.
8. Requisitos, costes y límites.
9. Historia y comunidad.
10. Próximo paso: demo, evaluación o contribución.

### Presentación técnica (20–30 minutos)

Arquitectura vigente; ciclo de vida de un paquete o cambio; selección de destinatarios; sincronización; evidencias; diagnóstico de un fallo; seguridad y credenciales; actualización y recuperación cuando proceda; preguntas y recursos.

### Demo reproducible

Preparar un entorno aislado con datos ficticios:

1. Mostrar el estado inicial y la necesidad.
2. Preparar un paquete o cambio inocuo.
3. Seleccionar el grupo destinatario.
4. Mostrar la planificación.
5. Ejecutar el proceso vigente.
6. Verificar el resultado en cliente y servidor.
7. Mostrar los registros disponibles.
8. Introducir una incidencia controlada y diagnosticarla.
9. Restaurar el entorno.

Ensayar la demo y preparar un vídeo de respaldo. Si un paso no es real, identificarlo claramente como simulación. No utilizar datos reales sin autorización.

El kit de ponentes debe incluir diapositivas editables y PDF, guiones de 5/15/30 minutos, instrucciones para reiniciar la demo, vídeo de respaldo, FAQ, capturas fechadas, diagrama vigente y formulario de feedback.

## 8. Comunicaciones

### Canales

Priorizar los canales que el equipo pueda mantener: web y documentación oficiales, GitHub, comunidades GNU/Linux y software libre, eventos técnicos, redes profesionales, blogs/boletines y contacto con organizaciones evaluadoras. No abrir canales nuevos sin capacidad para atenderlos ni enviar campañas masivas sin consentimiento.

### Calendario editorial de 12 semanas

| Semana | Tema | Formato |
|---|---|---|
| 1 | Qué problema resuelve | Página introductoria y folleto |
| 2 | Historia del proyecto | Artículo/entrevista |
| 3 | Cómo funciona un despliegue | Diagrama y artículo |
| 4 | Primera prueba guiada | Tutorial actualizado |
| 5 | Inventario y auditoría | Caso práctico |
| 6 | Arquitectura y repositorios | Mapa del ecosistema |
| 7 | Demo de principio a fin | Vídeo corto |
| 8 | Operación e incidencias | Artículo/podcast |
| 9 | Experiencia de una organización | Caso validado |
| 10 | Cómo contribuir | Guía comunitaria |
| 11 | Preguntas frecuentes y límites | FAQ |
| 12 | Sesión abierta | Webinar y resumen |

Es una propuesta flexible. Si el equipo es pequeño, publicar una pieza sólida cada dos semanas y reutilizarla es preferible a una frecuencia alta de baja calidad.

### Plantilla de comunicación

**Titular:** ¿Cómo desplegar software de forma controlada en una flota de equipos?

“Gestionar equipos no consiste solo en instalar programas: también hay que decidir qué cambia, en qué equipos, cuándo se distribuye y cómo comprobar el resultado. Migasfree es un proyecto de software libre orientado a la gestión de sistemas y al despliegue de software. Consulta la documentación, comprueba los requisitos de tu entorno y revisa una demostración reproducible.”

Enlace histórico de referencia: https://fun-with-migasfree.readthedocs.io/es/master/

Antes de publicarlo, sustituir o complementar ese enlace con la guía vigente. Cada afirmación técnica debe tener una fuente verificable. Diferenciar hechos, experiencia personal, hipótesis y objetivos; evitar superlativos y promesas de ahorro sin medición.

## 9. Podcast: “Conversaciones con Migasfree”

**Formato piloto:** seis episodios de 20–30 minutos, quincenales, en español; cada episodio con transcripción accesible.

1. ¿Por qué nació Migasfree? Origen y decisiones iniciales.
2. De un paquete a una flota: explicar el despliegue con un ejemplo.
3. La vida del administrador: planificación, incidencias y auditoría.
4. Software libre en una organización pública: aprendizajes y barreras.
5. Dentro del ecosistema: componentes y repositorios.
6. Cómo contribuir sin programar: documentación, pruebas, traducción e informes.

La propuesta no implica que personas históricas estén disponibles ni que representen oficialmente al proyecto.

### Estructura del episodio

- 0–1 min: apertura y pregunta central.
- 1–4 min: contexto.
- 4–15 min: experiencia y ejemplo.
- 15–22 min: límites y aprendizajes.
- 22–26 min: recomendaciones.
- 26–28 min: recursos y llamada a la acción.

### Producción mínima

Guion temático, consentimiento escrito, grabación inteligible, edición ligera, revisión de datos sensibles, transcripción corregida, resumen, enlaces, marcas de tiempo y conservación del máster. Usar solo música e imágenes propias o autorizadas. Seleccionar plataforma de alojamiento después de validar el piloto.

Medir escuchas completas si están disponibles, lecturas de transcripciones, clics hacia documentación, preguntas, participantes nuevos y tiempo de producción. No medir el éxito solo por descargas.

## 10. Reutilización de contenidos

Cada tema validado debe producir una unidad editorial reutilizable:

- Explicación canónica en documentación.
- Diagrama accesible.
- Ejemplo o demo reproducible.
- Resumen de 100–150 palabras.
- Diapositiva principal y fragmento para folleto.
- Pregunta para FAQ.
- Guion corto o pregunta de entrevista.
- Referencias y fecha de revisión.

Así, los materiales derivan de la misma fuente verificada y no crean versiones contradictorias.

## 11. Plan de ejecución

### Fase 0 — Validación (semanas 1–2)

Nombrar responsables editorial y técnico; verificar repositorios, licencias, requisitos y enlaces; acordar audiencias; invitar a entrevistados; definir una llamada a la acción y revisar identidad visual.

**Salida:** mensajes aprobados, mapa de repositorios y matriz de fuentes.

### Fase 1 — Kit mínimo (semanas 3–4)

Folleto ejecutivo, presentación corta, página introductoria, demo y vídeo de respaldo, FAQ de diez preguntas y plantilla de entrevista.

**Salida:** kit v1 listo para revisión externa.

### Fase 2 — Piloto (semanas 5–8)

Probar materiales con 5–8 personas de al menos dos audiencias; observar qué entienden; realizar una charla pequeña; publicar un artículo y, si hay capacidad, los dos primeros episodios; registrar dudas.

**Salida:** materiales corregidos y feedback inicial.

### Fase 3 — Difusión (semanas 9–12)

Publicar caso validado y guía de contribución, distribuir el kit en comunidades y eventos, evaluar el podcast y preparar el informe trimestral.

**Salida:** evaluación y plan de continuidad.

### Dedicación orientativa

| Rol | Carga estimada |
|---|---|
| Coordinación editorial | 2–3 h/semana |
| Revisión técnica | 2–4 h/semana |
| Diseño inicial | 8–16 h |
| Preparación de evento | 3–5 h por evento |
| Producción de audio | 4–7 h por episodio |
| Atención a comunidad | 1–3 h/semana |

Estimaciones para planificar, no compromisos aprobados.

## 12. Métricas

Establecer línea base antes del lanzamiento. Medir:

- **Comprensión:** lectores que identifican el problema resuelto; dudas restantes tras una charla.
- **Interés:** visitas a documentación, solicitudes cualificadas de demo y evaluaciones iniciadas.
- **Comunidad:** contribuciones útiles, nuevas personas participantes y preguntas respondidas.
- **Calidad:** piezas revisadas técnicamente, enlaces rotos, material obsoleto, accesibilidad y coste por pieza.

Revisar mensualmente. No premiar volumen si se deteriora la exactitud.

## 13. Riesgos y mitigación

| Riesgo | Mitigación |
|---|---|
| Documentación antigua presentada como actual | Etiquetar material histórico y fechar la revisión |
| Promesas no demostradas | Lista de afirmaciones aprobadas y fuentes |
| Dependencia de una persona | Plantillas, guiones y fuente editorial compartida |
| Sobrecarga de podcast | Piloto corto y revisión tras dos episodios |
| Materiales contradictorios | Fuente canónica reutilizable |
| Uso de nombres/imágenes sin permiso | Consentimiento y verificación de atribuciones |
| Demo fallida | Ensayo, entorno aislado y vídeo de respaldo |
| Confusión entre proyectos activos e históricos | Validación con mantenedores |
| Métricas sin contexto | Publicar método, fechas y límites |

## 14. Lista de control de publicación

- [ ] Descripción del producto validada por el equipo.
- [ ] Capacidades vinculadas a una versión identificada.
- [ ] Requisitos, comandos y capturas revisados.
- [ ] Repositorios oficiales y estado de mantenimiento verificados.
- [ ] Licencias y permisos de texto, imágenes, diagramas y audio comprobados.
- [ ] Personas citadas han revisado nombres, funciones y citas.
- [ ] Casos y cifras tienen autorización y evidencia.
- [ ] Ejemplos libres de datos personales y credenciales.
- [ ] Demo ensayada y plan de respaldo preparado.
- [ ] Fecha, versión, enlaces y llamada a la acción incluidos.
- [ ] Alternativas accesibles para PDF, vídeo y audio.
- [ ] Responsable de mantenimiento editorial asignado.

## 15. Fuentes

1. **Fun with migasfree:** https://fun-with-migasfree.readthedocs.io/es/master/ — referencia histórica y editorial.
2. **Introducción:** https://fun-with-migasfree.readthedocs.io/es/master/part01.html — relato de origen y enfoque divulgativo.
3. **Configuración del sistema:** https://fun-with-migasfree.readthedocs.io/es/master/chapter08.html — referencia histórica de conceptos de configuración y despliegue.
4. **Organización GitHub:** https://github.com/migasfree — comprobar repositorios y actividad uno por uno.
5. **Web del proyecto:** http://www.migasfree.org — verificar redirección, HTTPS y vigencia antes de imprimir enlaces.

La documentación histórica no debe tratarse como única guía de instalación moderna. Comprobar los avisos de licencia vigentes antes de reutilizar material.

## 16. Decisiones pendientes

1. Audiencia prioritaria para los próximos tres meses.
2. Versión y entorno de referencia para las demos.
3. Repositorios activos que pueden promocionarse.
4. Responsables de validar datos técnicos y aprobar comunicaciones.
5. Personas que acepten entrevistas.
6. Canal oficial para solicitudes de demo.
7. Licencias y recursos gráficos reutilizables.
8. Indicador de éxito inicial: demos, evaluaciones, contribuciones o comprensión.

## Recomendación final

Empezar con un kit mínimo verificable: folleto ejecutivo, presentación breve, demo reproducible, página introductoria actualizada y entrevista piloto. Probarlo con lectores reales antes de invertir en una temporada completa de podcast o abrir más canales.

La ventaja diferencial de Migasfree debe contarse como combinación de problema operativo reconocible, procedimientos concretos, experiencia, software libre y conocimiento compartido. De *Fun with migasfree* conviene conservar claridad, ejemplos, humor medido y reconocimiento a las personas, distinguiendo siempre la historia, las capacidades actuales y las promesas por demostrar.
