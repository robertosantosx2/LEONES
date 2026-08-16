# LEONES — Scripts locales para probar LLMs

Este directorio contiene exclusivamente herramientas destinadas al **usuario final** que quiere probar su propio LLM en su equipo.

## Objetivo

La web de LEONES no ejecuta la infraestructura del proyecto ni exige descargar el repositorio completo.

El flujo previsto es:

```text
web LEONES
    ↓
seleccionar prueba
    ↓
descargar script local
    ↓
instalar dependencias
    ↓
ejecutar en el equipo del usuario
    ↓
obtener resultados
    ↓
comparar / interpretar
```

## Qué debe contener cada prueba

Cada nueva prueba debe incluir, como mínimo:

```text
<prueba>/
├── README.md
├── script o módulo principal
├── requirements.txt (si procede)
├── examples/ (si procede)
└── fixtures/ (si procede y son ligeros)
```

## Contrato de una prueba

El `README.md` de cada prueba debe indicar:

1. **Propósito:** qué mide o demuestra.
2. **Modelo:** qué modelos admite y qué formato espera.
3. **Hardware:** CPU, RAM, GPU/VRAM y almacenamiento recomendados.
4. **Software:** sistema operativo, Python/runtime y dependencias.
5. **Instalación:** pasos reproducibles.
6. **Ejecución:** comando exacto.
7. **Entrada:** datos o parámetros necesarios.
8. **Salida:** formato y ubicación de resultados.
9. **Interpretación:** cómo leer los resultados.
10. **Privacidad:** qué información sale del equipo, si sale alguna.
11. **Limitaciones:** qué no mide la prueba.
12. **Licencia:** licencia del código y de cualquier recurso incluido.

## Reglas

- No importar módulos desde `atlas/`, `agents/` ni otros componentes internos de infraestructura.
- No requerir GitHub Actions.
- No requerir secretos de LEONES.
- No incluir credenciales.
- No descargar modelos automáticamente sin indicarlo claramente.
- No enviar prompts, resultados ni telemetría fuera del equipo sin explicarlo y solicitar la configuración correspondiente.
- No asumir hardware concreto: detectar o documentar los requisitos.
- Preferir dependencias mínimas y reproducibles.
- Mantener scripts legibles y formateados.
- Los ejemplos deben poder ejecutarse de forma independiente.

## Qué no pertenece aquí

No deben colocarse en `scripts/local/`:

- scrapers de LEONES;
- pipelines de Atlas;
- jobs de prospección;
- procesos de ingestión;
- workflows;
- mantenimiento de bases de datos internas;
- automatizaciones del proyecto;
- herramientas que necesiten credenciales internas;
- código que sólo tenga sentido dentro de la infraestructura.

## Principio de portabilidad

Una persona debe poder descargar una prueba, leer su `README.md`, instalar sus dependencias y ejecutarla en un equipo compatible **sin clonar ni desplegar la infraestructura completa de LEONES**.

Si esto no es posible, la herramienta no debe clasificarse como script local de usuario: debe permanecer en infraestructura hasta que pueda convertirse en un paquete autónomo.
