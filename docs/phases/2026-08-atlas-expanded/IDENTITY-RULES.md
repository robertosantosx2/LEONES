# H06 — P0 Identidad canónica

## Objetivo

Medir la identidad de los registros actuales antes de fusionar o ampliar el catálogo.

## Regla de precedencia

```text
1. model_id
2. repository/source canonical path
3. organization + model_name
```

La coincidencia por nombre es secundaria y nunca autoriza una fusión automática.

## Variantes legítimas

Dos registros con la misma identidad base pueden representar artefactos/configuraciones distintas si difieren en cuantización, hardware objetivo u otra característica técnica explícita. Se agrupan para revisión, pero no se destruyen ni fusionan automáticamente.

```text
MODELO
 ├── variante base
 ├── cuantización
 ├── artefacto
 └── configuración hardware
```

## Estados del auditor

- `unique`: una única fila para la identidad.
- `duplicate-candidate`: varias filas aparentemente equivalentes; revisión obligatoria.
- `same-model-multiple-artifacts-or-configs`: misma identidad con configuraciones/artifactos distintos; conservar separados hasta definir entidad de variante/artefacto.
- `possible-collision`: coincidencia débil por clave secundaria; riesgo alto.

## Regla de seguridad

El auditor **no hace merges**. Produce candidatos y exige revisión. La deduplicación destructiva queda fuera de P0.

## Salida

`scripts/atlas_identity_audit.py` genera `data/prospection/atlas_identity_audit.csv`, proporcionando clave de identidad, fila, identidad visible, configuración y acción recomendada.

## Criterio de aceptación P0

P0 se podrá cerrar cuando:

1. el auditor se ejecute sobre el feed real;
2. se conozca el número de identidades únicas y grupos duplicados;
3. todos los grupos no únicos tengan clasificación/riesgo;
4. no exista merge automático sin evidencia suficiente;
5. los resultados queden documentados antes de continuar con P1.
