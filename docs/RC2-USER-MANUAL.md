# LEONES RC2 — Manual de usuario beta

## Bienvenido

RC2 está pensado para que puedas usar LEONES sin conocer su arquitectura interna. Tu papel es tomar las decisiones; LEONES aporta información, prepara los planes y conserva la evidencia.

## El recorrido

```text
╔══════════════════════════════════════════════════════╗
║                 L E O N E S · R C 2                 ║
╚══════════════════════════════════════════════════════╝
                         ↓
                    TU HARDWARE
                         ↓
                    PERFILADO
                         ↓
                 MODELOS CANDIDATOS
                         ↓
                  ELIGE TU MODELO
                         ↓
          ┌──────────────┴──────────────┐
          │                             │
       ODS                         MAGNITUDE
          │                             │
          └──────────────┬──────────────┘
                         ↓
                  ELIGE TU STACK
                         ↓
                 INSTALAR / VERIFICAR
                         ↓
                 ¿QUIERES MEDIRLO?
                    ↙          ↘
                  NO            SÍ
                  ↓              ↓
                 FIN       BENCHMARK REAL
                                 ↓
                             EVIDENCIA
```

## 1. Hardware

LEONES puede observar tu equipo y, cuando un dato no pueda obtenerse automáticamente, pedirte que lo declares o corrijas.

Los datos desconocidos se mantienen como desconocidos. No necesitas inventar una cifra para continuar.

## 2. Tu modelo

LEONES te presenta modelos candidatos compatibles con el perfil disponible. La recomendación es una ayuda: **la elección final es tuya**.

Al comparar modelos, presta atención a:

- tamaño y variante;
- cuantización;
- memoria necesaria;
- runtime;
- evidencia existente;
- estimaciones frente a mediciones reales.

## 3. ODS o Magnitude

Esta es una decisión informada, no una elección entre dos nombres.

Antes de seleccionar, LEONES debe mostrar las funcionalidades disponibles de cada stack para la versión/ref concreta.

**ODS** puede aportar, según integración/ref, un stack local con inferencia y componentes de interfaz, gateway, RAG/search, voz, agentes/workflows, imágenes, privacidad y observabilidad.

**Magnitude** puede aportar, según integración/ref, agente local, modelos locales, perfilado hardware, recomendación, descarga/configuración, ejecución, skills y endpoints compatibles.

Lee también los requisitos, permisos, red, almacenamiento, componentes y limitaciones. Si una capacidad no está verificada, debe aparecer como tal.

## 4. Instalar

Después de elegir, LEONES prepara un plan de instalación.

Nada debería instalarse simplemente porque hayas elegido el stack. Primero debes ver qué se hará y autorizarlo.

Puedes cancelar.

## 5. Verificar

Una vez instalado, LEONES comprueba que el stack funciona. Si la verificación falla, no continúes al benchmark.

## 6. Medir

La pregunta es sencilla:

**¿Quieres medir esta combinación realmente en tu equipo?**

### Si respondes NO

LEONES termina sin ejecutar un benchmark.

### Si respondes SÍ

LEONES autoriza el benchmark concreto y utiliza el runner canónico de RC1. La ejecución genera evidencia nueva.

## 7. Entender el resultado

Un resultado puede incluir velocidad, éxito de tareas y otros indicadores según el benchmark.

Recuerda:

```text
ESTIMADO  ≠  MEDIDO
HISTÓRICO ≠  EJECUCIÓN ACTUAL
INSTALADO ≠  BENCHMARK AUTORIZADO
```

## 8. Evidencia

Cuando se ejecuta una medición, LEONES conserva la procedencia y un identificador de ejecución. Esto permite distinguir una prueba nueva de un resultado anterior.

## 9. Privacidad

No compartas credenciales, API keys ni información privada. La contribución de resultados al conocimiento colectivo es voluntaria.

## 10. Si algo sale mal

No borres el error. Anota la etapa, modelo, runtime, hardware y mensaje original. Un fallo de instalación o benchmark también es información útil para RC2.

Consulta el [manual de instalación de RC2](RC2-INSTALLATION-MANUAL.md) para el procedimiento técnico y el [flujo de usuario](RC2-BETA-USER-FLOW.md) para conocer el contrato completo.
