# Plataformas soportadas por LEONES

## Plataformas Linux de referencia

LEONES considera tres plataformas Linux como referencia explícita para ejecución local:

1. **Debian** — soporte explícito y plataforma de referencia.
2. **Ubuntu** — soporte explícito y plataforma de referencia.
3. **Red Hat Enterprise Linux (RHEL)** — soporte explícito y plataforma de referencia.

Debian, Ubuntu y RHEL tienen el mismo nivel conceptual de soporte. Debian no se considera simplemente una variante de Ubuntu.

### Qué significa «soporte explícito»

Un script LEONES debe:

- identificar la distribución mediante `/etc/os-release` cuando sea relevante;
- evitar asumir que todo Linux es Ubuntu;
- evitar asumir que existe `apt` o `dnf`;
- proporcionar instrucciones específicas cuando cambien los paquetes o comandos;
- mantener la ejecución del script independiente del gestor de paquetes siempre que sea posible;
- informar al usuario de la distribución detectada antes de recomendar acciones específicas.

### Instalación base orientativa

**Debian**

```bash
sudo apt update
sudo apt install python3 python3-venv python3-pip
```

**Ubuntu**

```bash
sudo apt update
sudo apt install python3 python3-venv python3-pip
```

**RHEL**

```bash
sudo dnf install python3 python3-pip
```

Estas órdenes son únicamente la preparación base orientativa. Cada runtime de IA puede tener requisitos adicionales y debe documentarlos por separado.

## Otras distribuciones

Fedora, Rocky Linux, AlmaLinux, Linux Mint y otras distribuciones pueden funcionar, pero no se presentan como plataformas de referencia hasta disponer de pruebas reproducibles suficientes.

## Principio LEONES

> **Linux primero; Debian, Ubuntu y RHEL como referencias explícitas.**

La compatibilidad se demuestra con pruebas reproducibles, no únicamente con una afirmación en la documentación.
