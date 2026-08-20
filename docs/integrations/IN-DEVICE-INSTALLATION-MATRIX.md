# Matriz de instalación en dispositivo

La matriz separa familias compatibles y deja claro qué se valida automáticamente y qué debe quedar como `unknown`.

| Perfil | Debian | Ubuntu | Rocky/RHEL | Docker | GPU | Resultado esperado |
|---|---|---|---|---|---|---|
| ODS | Sí | Sí | Sí, ruta dnf compatible | Requerido en Linux | NVIDIA/AMD/Intel Arc/CPU según plataforma | servidor IA local |
| Magnitude | Sí | Sí | Sí, si Node.js/npm funcionan | No requerido | CPU/GPU según motor y configuración | asistente coding local |

## Preflight común

1. Identificar OS y arquitectura.
2. Comprobar CPU y RAM.
3. Detectar GPU/VRAM cuando sea posible.
4. Medir almacenamiento libre.
5. Comprobar red únicamente para la fase de descarga.
6. No iniciar descargas grandes sin confirmación.
7. No registrar secretos.
8. Mostrar exactamente qué se va a instalar.

## Debian/Ubuntu

```bash
sudo apt update
sudo apt install -y curl git ca-certificates
```

Para ODS debe existir Docker Engine + Compose v2 y, si corresponde, el runtime de GPU. Para Magnitude debe existir Node.js/npm en una versión soportada por la versión de CLI instalada.

## Rocky/RHEL-compatible

```bash
sudo dnf install -y curl git ca-certificates
```

Docker/Compose y Node.js se validan como prerrequisitos independientes. LEONES no instala silenciosamente un repositorio de terceros ni sustituye el gestor de paquetes del sistema sin consentimiento.

## Validación posterior

ODS:

```bash
ods status
ods doctor
```

Y una petición local al endpoint de inferencia configurado.

Magnitude:

```bash
magnitude --help
```

Después se ejecuta una tarea controlada en un directorio de prueba y se registra el modelo/runtime que Magnitude haya seleccionado.

## Uninstall/recovery

Cada perfil debe documentar antes de instalar:

- directorio de instalación;
- archivos de configuración;
- servicios/containers creados;
- modelos descargados;
- procedimiento de parada;
- procedimiento de desinstalación;
- qué datos pueden conservarse;
- qué datos no deben eliminarse automáticamente.

No se borra un directorio del usuario sin confirmación explícita.
