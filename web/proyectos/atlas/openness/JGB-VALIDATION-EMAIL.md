# Formulario de validación humana de Índice JGB

**Canal:** correo electrónico  
**Destino:** `manadaleones.ia@gmail.com`  
**Acceso:** restringido a personas autorizadas por LEONES.

Este documento es una **plantilla de correo**, no un formulario web.

## Asunto

```text
VALIDACIÓN JGB — <modelo> — <variante> — CLASE PROPUESTA <0-5>
```

## Cuerpo del correo

```text
FORMULARIO DE VALIDACIÓN HUMANA DE ÍNDICE JGB

Modelo: <identificador exacto>
Variante: <variante exacta>
Fuente/identidad: <URL o identificador>
Fecha de evaluación: <YYYY-MM-DD>
Solicitante: <identidad autorizada>

CLASE JGB PROPUESTA: CLASE<0-5>

DIMENSIONES

Access: <nivel 0-5>
Estado: <verified|provisional|supported|unknown|disputed>
Evidencia: <fuentes y resumen>

Model control: <nivel 0-5>
Estado: <verified|provisional|supported|unknown|disputed>
Evidencia: <fuentes y resumen>

Data control: <nivel 0-5>
Estado: <verified|provisional|supported|unknown|disputed>
Evidencia: <fuentes y resumen>

Autonomy: <nivel 0-5>
Estado: <verified|provisional|supported|unknown|disputed>
Evidencia: <fuentes y resumen>

Trust: <nivel 0-5>
Estado: <verified|provisional|supported|unknown|disputed>
Evidencia: <fuentes y resumen>

CONFIDENCE: <high|medium|low>

La clase propuesta no se activa hasta recibir una respuesta humana válida.

RESPUESTA HUMANA VÁLIDA ESPERADA

OK LEONES CLASE0
OK LEONES CLASE1
OK LEONES CLASE2
OK LEONES CLASE3
OK LEONES CLASE4
OK LEONES CLASE5
```

## Regla de activación

Solo activa una clase una respuesta que coincida **exactamente** con una de las seis expresiones anteriores.

```text
EVIDENCIA
   ↓
CLASE PROPUESTA
   ↓
FORMULARIO DE VALIDACIÓN HUMANA DE ÍNDICE JGB
   ↓
manadaleones.ia@gmail.com
   ↓
RESPUESTA EXACTA OK LEONES CLASE<N>
   ↓
CLASE ACTIVADA = N
```

La respuesta humana no sustituye la evidencia primaria. La solicitud, respuesta y clase activada deben conservarse por separado.

Si la respuesta no coincide exactamente con las seis respuestas válidas, el estado permanece `pending_human_validation`.
