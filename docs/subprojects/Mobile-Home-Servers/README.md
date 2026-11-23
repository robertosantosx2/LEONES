# Mobile-Home-Servers — smartphones como servidores domésticos

Estado: investigación y prospección diaria.

- [Observatorio](../../../web/mobile-home-servers.html) · [Feed](../../../web/data/mobile-home-servers.json) · [Roadmap](ROADMAP.md)
- Complemento de [Mobile-LLMs-ARM](../Mobile-LLMs-ARM/README.md).

## Arquitecturas
1. Termux sin root, userland adaptado sobre Android.
2. PRoot-Distro (Debian/Ubuntu/Alpine), userland sin kernel propio.
3. Root + chroot, mayor control y superficie de riesgo.
4. Linux nativo, mainline o vendor + compatibilidad según dispositivo.
5. postmarketOS, Mobian, Droidian y Ubuntu Touch: validar soporte por variante.

## Stack Termux
```bash
pkg update && pkg upgrade -y
pkg install openssh tmux git curl wget rsync python nodejs cronie termux-services proot-distro -y
passwd
sshd # puerto habitual 8022
ip addr show wlan0
```
Debian PRoot:
```bash
proot-distro install debian
proot-distro login debian
apt update && apt install nginx python3 git curl wget tmux -y
```
Usar SSH por claves, ACLs, y acceso remoto preferiblemente mediante Tailscale/WireGuard; evitar exponer administración.

Servicios: SSH/tmux/cron/runit, rsync/SFTP, web estática, Nginx/Caddy, FastAPI/Node, MQTT/Mosquitto, Node-RED, Syncthing, backup, ntfy, sensores y edge workloads ligeros.

## Riesgos
Android puede suspender procesos, restringir batería o cambiar networking; PRoot no ofrece kernel/namespace completo. Docker no se presupone viable. Evaluar temperatura, uptime, storage, USB/red, batería y carga continua. Nunca usar baterías dañadas/hinchadas.

## Evidencia
Estados: discovered, pending_review, source_verified, tested, measured, rejected/archived. Registrar modelo/variante, SoC, RAM, sistema/kernel, bootloader, runtime, servicios, red, uptime, energía, térmica, protocolo y artefactos. No confundir datos de terceros con mediciones LEONES.

## Fuentes
https://termux.dev/ · https://wiki.termux.com/wiki/Main_Page · https://github.com/termux/proot-distro · https://andronix.app/ · https://postmarketos.org/ · https://mobian.org/ · https://droidian.org/ · https://ubuntu-touch.io/ · https://github.com/romit07/android-home-server · https://github.com/handriss/mobile-home-server · https://github.com/fbratten/android-termux-home-server · https://github.com/myselfshravan/droidvm
