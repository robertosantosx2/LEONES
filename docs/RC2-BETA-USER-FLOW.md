# RC2 — LEONES Beta User Flow

**Estado:** 🟢 RC2-A cerrado · RC2-B preparado para validación física  
**Fecha:** 31 de agosto de 2026  
**Predecesor:** RC1 — ejecución efectiva validada  

## 1. Objetivo

RC2 convierte la cadena técnica validada en RC1 en un recorrido que un beta tester externo pueda completar sin conocer la arquitectura interna de LEONES.

RC2 no crea un sistema paralelo de selección, perfilado, benchmark ni ejecución: orquesta los contratos y componentes ya fijados.

## 2. Estado actual

RC2-A queda **cerrado y validado** como capa de orquestación.

Criterios comprobados:

- wizard ejecutable como entrada documentada;
- hardware real consumido desde LLMFit;
- candidatos procedentes de LLMFit conservados como `estimated`;
- elección explícita de modelo;
- elección explícita de ODS o Magnitude;
- consentimiento de instalación separado;
- flujo no interactivo determinista;
- sesión RC2 con estado trazable;
- suite completa: **334 tests passed**;
- árbol de trabajo limpio tras la validación local.

La salida de LLMFit no se considera evidencia de ejecución. La evidencia real sólo nace del runner/protocolo canónico.

## 3. Experiencia canónica

```text
INSTALAR LEONES
      ↓
PREFLIGHT
      ↓
HARDWARE OBSERVADO / DECLARADO
      ↓
PERFILADO ODS / MAGNITUDE
      ↓
CANDIDATOS DE MODELO
      ↓
ELECCIÓN DEL USUARIO
      ↓
COMPARADOR ODS / MAGNITUDE
      ↓
ELECCIÓN DE STACK
      ↓
PLAN
      ↓
CONSENTIMIENTO
      ↓
INSTALAR / PREPARAR
      ↓
VERIFICAR
      ↓
¿BENCHMARK REAL?
   ┌───┴────┐
  NO       SÍ
   ↓        ↓
 FIN     RUNNER CANÓNICO RC1
            ↓
       MEDICIÓN
            ↓
         EVIDENCIA
            ↓
        RESULTADO
            ↓
   COMPARTIR (OPT-IN)
```

## 4. Principios de producto

### 4.1 LEONES recomienda; el usuario decide

La selección puede ordenar candidatos, pero no sustituye la decisión del usuario.

### 4.2 No ocultar ODS y Magnitude

Antes de elegir el stack deben mostrarse sus funcionalidades relevantes, versión/ref, requisitos, componentes, permisos, red, almacenamiento, privacidad y limitaciones conocidas.

### 4.3 No inventar capacidades

Lo no comprobado debe permanecer como desconocido. Las capacidades dependen de la versión/ref y de la plataforma.

### 4.4 Consentimiento antes de instalar

Las descargas y cambios del sistema requieren consentimiento explícito y separado del consentimiento de benchmark.

### 4.5 Medición separada de estimación

`observed`, `configured`, `estimated`, `reported` y `measured` conservan significados distintos. RC2 nunca convierte una predicción en medición LEONES.

### 4.6 Privacidad por defecto

No se deben enviar prompts, archivos, conversaciones, código, secretos ni API keys. Compartir evidencia será siempre opt-in.

## 5. Contratos que RC2 reutiliza

RC2 debe consumir, no duplicar:

- selección de modelo/runtime;
- gate de autorización;
- decisión LEONES → ODS/Magnitude;
- contratos de integración ODS y Magnitude;
- protocolo de medición real;
- runner canónico;
- evidencia reproducible;
- benchmark de tareas completadas.

**Prohibición explícita:** LEONES no crea otro instalador de ODS ni otro instalador de Magnitude, ni crea un runner RC2 paralelo.

## 6. Fases

### RC2-A — Orquestación · 🟢 CERRADO

Entrada CLI y wizard funcionando, con decisiones separadas y sin efectos laterales ocultos.

Validación local final: **334/334 tests OK**.

### RC2-B — Hardware y perfilado · 🟡 SIGUIENTE GATE

La integración con LLMFit ya consume el payload real del sistema y normaliza hardware/candidatos. El siguiente trabajo no es diseñar otra capa: es validar el recorrido físico sobre una instalación externa/real y documentar cualquier discrepancia.

### RC2-C/D — Selección y comparador

La selección humana y el contrato funcional ODS/Magnitude quedan condicionados a la información realmente disponible en la versión/ref utilizada. No se promocionarán estimaciones a evidencia.

### RC2-E — Instalación controlada

Preparar/invocar la interfaz soportada por el stack elegido, con consentimiento, health check y rollback/uninstall. La instalación real es el próximo efecto lateral autorizado del piloto.

### RC2-F — Benchmark opcional

Si el beta tester acepta, conectar con el runner canónico RC1 y el protocolo de medición real. No crear un runner RC2 paralelo.

### RC2-G — Resultado y contribución

Mostrar resultado y ofrecer compartición opt-in.

### RC2-H — Piloto beta

Repetir el flujo con máquinas externas y registrar problemas de instalación, selección, runtime, benchmark y evidencia.

## 7. Definition of Done de RC2

RC2 sólo se considera validado cuando un beta tester externo puede completar el flujo completo sin intervención del desarrollador:

- [ ] instalar LEONES;
- [ ] detectar/declarar hardware;
- [ ] obtener perfil;
- [ ] recibir candidatos;
- [ ] seleccionar modelo;
- [ ] ver funcionalidades de ODS y Magnitude antes de elegir;
- [ ] elegir ODS o Magnitude;
- [ ] instalar/preparar con consentimiento;
- [ ] pasar health checks;
- [ ] elegir benchmark Sí/No;
- [ ] si elige Sí, producir medición real con el runner canónico;
- [ ] conservar evidencia reproducible;
- [ ] mostrar resultado comprensible;
- [ ] no filtrar datos privados;
- [ ] poder repetir o desinstalar;
- [ ] documentar limitaciones reales.

## 8. Relación con RC1

RC1 validó:

```text
selección → gate → runtime real → A01 → medición → evidencia
```

RC2 añade la experiencia:

```text
usuario → hardware → perfilado → candidatos → elección
        → ODS/Magnitude → instalación → benchmark opcional
        → ejecución real → evidencia → resultado
```

**RC1 demuestra que la máquina funciona. RC2-A demuestra que la decisión puede recorrerse de forma controlada. RC2-B en adelante debe demostrar que ese recorrido funciona físicamente para un usuario externo.**
