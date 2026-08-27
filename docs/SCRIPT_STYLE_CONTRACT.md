# Contrato de scripts LEONES

Los scripts de LEONES deben poder ser entendidos y utilizados por una persona con conocimientos mínimos de programación.

## Reglas obligatorias

1. **Una responsabilidad:** cada script responde a una pregunta o realiza una tarea principal.
2. **Minimalismo:** usar la solución más sencilla que conserve el comportamiento necesario. No añadir abstracciones por anticipación.
3. **Legibilidad antes que brevedad:** evitar varias instrucciones en una línea, nombres crípticos y expresiones difíciles de leer.
4. **Comentarios útiles:** explicar el propósito y, sobre todo, el motivo de las decisiones que no sean obvias. No comentar código evidente.
5. **Docstring de entrada:** todo script ejecutable debe indicar qué hace, qué recibe, qué produce y sus límites principales.
6. **Interfaz explícita:** los argumentos de línea de comandos deben tener nombres claros y una descripción comprensible.
7. **Errores accionables:** cuando algo falla, indicar qué se esperaba y qué puede hacer la persona para corregirlo.
8. **Sin trabajo oculto:** un script no debe instalar paquetes, publicar datos, modificar repositorios ni ejecutar cargas físicas salvo que su propósito lo indique expresamente.
9. **Reutilización prudente:** no duplicar una función ya existente. Si compartir código realmente simplifica el proyecto, usar un módulo pequeño y bien documentado.
10. **Prueba:** todo cambio funcional debe conservar o ampliar las pruebas existentes.

## Criterio de aceptación

Un script se considera limpio cuando una persona que no conoce el proyecto puede responder, leyendo sus primeros comentarios y la interfaz, a estas cuatro preguntas:

- ¿Para qué sirve?
- ¿Qué necesito antes de ejecutarlo?
- ¿Qué va a cambiar o producir?
- ¿Qué no hace?

La complejidad accidental debe eliminarse. La complejidad propia del problema puede permanecer, pero debe quedar explicada.

## Política de migración

Esta norma se aplica a los scripts nuevos y a todo script que se modifique. Los scripts antiguos se simplificarán de forma incremental, sin reescrituras masivas que puedan cambiar su comportamiento sin necesidad.
