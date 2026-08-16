# ADIVINO — descubrimiento con validación humana

ADIVINO es el nombre oficial del mecanismo de descubrimiento de nuevas fuentes para LEONES.

## Qué descubre

Puede proponer sitios web, repositorios, datasets, benchmarks, runtimes, software, skills, agentes, documentación y otras fuentes útiles para aprender o medir.

## Principio de seguridad

ADIVINO **descubre, pero no decide**. Cada descubrimiento queda en `pending_human` hasta que el responsable lo aprueba expresamente.

La aprobación operativa es exactamente:

```text
OK LEONES
```

Cualquier otro texto mantiene el candidato pendiente.

## Flujo

```text
ADIVINO
  ↓
CANDIDATO
  ↓
NORMALIZACIÓN + DEDUPLICACIÓN
  ↓
PENDING_HUMAN
  ↓
correo al responsable
  ↓
respuesta: OK LEONES
  ↓
APPROVED
  ↓
adaptador / extracción / medición
  ↓
evidencia + quality gates
  ↓
Atlas / Manada / recomendador
```

## Correo

El workflow de notificación debe utilizar un secreto configurable, por ejemplo `ADIVINO_EMAIL_TO`. No se guarda ninguna dirección personal en el repositorio.

El correo debe contener como mínimo:

- nombre de la fuente;
- URL canónica;
- tipo;
- por qué ADIVINO la propone;
- fecha del descubrimiento;
- identificador estable;
- instrucciones claras: responder exactamente `OK LEONES` para aprobar.

## Respuesta

El procesador de correo debe buscar respuestas del responsable y aceptar únicamente el texto normalizado `OK LEONES`. La aprobación se registra con fecha, mensaje origen y candidato aprobado.

Nunca se debe interpretar un correo reenviado, una firma, una frase parecida o una aprobación de otra persona como autorización automática.

## No publicación directa

Incluso después de `OK LEONES`, ADIVINO solo autoriza la fuente para el siguiente pipeline. Los datos obtenidos siguen teniendo que atravesar identidad, licencia, evidencia, calidad y los gates específicos del Atlas.

## CI

Cualquier workflow de ADIVINO que escriba en `main` debe usar la regla global de no concurrencia:

```yaml
concurrency:
  group: leones-main-writers
  cancel-in-progress: false
```

## Privacidad

Las direcciones de correo se mantienen en secretos/configuración del entorno y nunca en código, fixtures, logs o commits.
