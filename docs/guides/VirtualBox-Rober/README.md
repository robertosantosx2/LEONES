# VirtualBox-Rober — Ubuntu 24.04 LTS en VirtualBox 7.0.2

**Guía paso a paso para el portátil AMD Ryzen 7 5825U · 16 GB RAM · AMD Radeon integrada · SSD 477 GB**  
**Fecha:** 11-11-2026 · **Proyecto:** LEONES

> **Aviso de compatibilidad:** VirtualBox 7.0.2 se publicó en octubre de 2022, antes de Ubuntu 24.04. Puede ejecutar el invitado, pero esta combinación no debe considerarse oficialmente validada. Se documenta 7.0.2 porque es la versión solicitada. Para una instalación nueva o si Guest Additions falla, usa una versión mantenida de VirtualBox y su Extension Pack de la misma versión exacta.

## 1. Perfil y configuración recomendada

| Elemento | Equipo anfitrión | Valor para la VM |
|---|---|---|
| CPU | Ryzen 7 5825U, 8 núcleos / 16 hilos | **4 vCPU** |
| RAM | 16 GB (15,4 GB utilizables) | **6144 MB**; 8192 MB solo con margen de memoria |
| GPU | Radeon integrada; 496 MB informados | VMSVGA, 128 MB vídeo, 3D desactivado inicialmente |
| SSD | 477 GB, 165 GB usados | VDI dinámico de **80 GB** |
| Red | — | NAT |
| Invitado | — | Ubuntu Desktop 24.04 LTS AMD64 |

Los 496 MB indicados no representan necesariamente toda la memoria gráfica disponible: la Radeon integrada utiliza memoria compartida. VirtualBox presenta una GPU virtual; no proporciona acceso directo equivalente a la Radeon física. Con 16 GB, 6 GB para Ubuntu es prudente; no asignes casi toda la RAM al invitado. El VDI dinámico crece según se utiliza.

**Seguridad:** la opción «Borrar disco e instalar Ubuntu» se aplica al disco virtual, no al SSD físico. Antes de confirmar, verifica que el instalador muestra el disco virtual de aproximadamente 80 GB.

## 2. Descargas oficiales

- Ubuntu 24.04 LTS AMD64 Desktop: https://releases.ubuntu.com/24.04/
- VirtualBox 7.0.2 (instaladores, manual, Extension Pack y Guest Additions): https://download.virtualbox.org/virtualbox/7.0.2/
- Manual 7.0.2: https://download.virtualbox.org/virtualbox/7.0.2/UserManual.pdf
- Tutorial oficial Ubuntu 24.04: https://ubuntu.com/desktop/docs/en/24.04/tutorial/install-ubuntu-desktop/

Elige la ISO **Desktop AMD64 / 64-bit PC**, no ARM ni Server. Para Windows anfitrión, el instalador es normalmente `VirtualBox-7.0.2-154219-Win.exe`. El Extension Pack es opcional y, si se instala, debe coincidir exactamente con VirtualBox 7.0.2.

En PowerShell calcula hashes (compara con los valores publicados por el proveedor):

```powershell
Get-FileHash "$env:USERPROFILE\Downloads\VirtualBox-7.0.2-154219-Win.exe" -Algorithm SHA256
Get-FileHash "$env:USERPROFILE\Downloads\ubuntu-24.04.5-desktop-amd64.iso" -Algorithm SHA256
```

El nombre de ISO puede variar según la revisión puntual (24.04.x).

## 3. Preparar Windows y comprobar AMD-V

1. Pulsa `Win + R`, escribe `winver` y comprueba Windows de 64 bits.
2. Abre Administrador de tareas → Rendimiento → CPU y comprueba que «Virtualización» está **Habilitada**.
3. El Ryzen 7 5825U admite AMD-V. Si aparece deshabilitada, reinicia y entra en UEFI/BIOS; busca **SVM Mode / AMD SVM / Secure Virtual Machine**, actívalo y guarda.
4. Comprueba el espacio libre real en el SSD. Se recomienda disponer de al menos 100 GB libres antes de crear la VM.
5. Cierra aplicaciones pesadas y realiza copia de seguridad de los archivos importantes.

PowerShell de diagnóstico:

```powershell
Get-CimInstance Win32_Processor |
  Select-Object Name,NumberOfCores,NumberOfLogicalProcessors,VirtualizationFirmwareEnabled,SecondLevelAddressTranslationExtensions
Get-CimInstance Win32_OperatingSystem |
  Select-Object TotalVisibleMemorySize,FreePhysicalMemory
```

No desactives Hyper-V, VBS, Integridad de memoria, Secure Boot ni BitLocker a ciegas. Si VirtualBox falla con un error del hipervisor, registra primero el mensaje exacto y diagnostica la función implicada.

## 4. Instalar VirtualBox 7.0.2

1. Ejecuta el instalador como administrador.
2. Mantén las opciones predeterminadas, salvo que tengas una política de red específica.
3. Acepta los controladores de Oracle que Windows solicite instalar. La red puede desconectarse brevemente.
4. Abre VirtualBox Manager.
5. En Ayuda → Acerca de VirtualBox confirma **7.0.2**.
6. Instala Extension Pack solo si necesitas sus funciones; debe ser 7.0.2 exacto.

Comprobación PowerShell:

```powershell
$VBox = Join-Path $env:ProgramFiles 'Oracle\VirtualBox\VBoxManage.exe'
Test-Path $VBox
& $VBox --version
```

## 5. Crear la máquina virtual desde la interfaz

1. Pulsa **Nueva**.
2. Nombre: `Ubuntu 24.04 - Rober`.
3. Carpeta de máquina: por ejemplo `D:\VirtualBox VMs\Ubuntu-24.04-Rober` (o una carpeta de la unidad con espacio).
4. Selecciona la ISO Ubuntu 24.04 Desktop AMD64.
5. Tipo Linux; versión Ubuntu (64-bit).
6. Desmarca la instalación desatendida si quieres seguir el asistente manual descrito aquí.
7. RAM: **6144 MB**.
8. CPU: **4**.
9. Disco nuevo: VDI, reservado dinámicamente, **80 GB**.
10. Revisa el resumen y termina.

## 6. Ajustes previos al primer arranque

| Apartado | Valor |
|---|---|
| Sistema → Placa base | 6144 MB; chipset predeterminado; EFI desactivado inicialmente |
| Sistema → Procesador | 4 CPU; límite 100 % |
| Pantalla | VMSVGA; 128 MB; aceleración 3D desactivada |
| Almacenamiento | ISO Ubuntu conectada a unidad óptica |
| Red → Adaptador 1 | Habilitado, NAT |
| General → Avanzado | Portapapeles bidireccional (tras Guest Additions) |

No actives 3D al principio. Si aparecen pantallas negras o artefactos, mantén 3D desactivado. NAT basta para acceder a Internet; no hace falta modo puente.

## 7. Instalar Ubuntu 24.04 LTS

1. Selecciona la VM y pulsa **Iniciar**.
2. Selecciona «Try or Install Ubuntu / Probar o instalar Ubuntu».
3. Idioma: Español. Pulsa Siguiente.
4. Configura accesibilidad si procede.
5. Teclado: Español (o la distribución real del teclado). Prueba las teclas.
6. Conexión: deja NAT; conéctate si el instalador lo ofrece. La red no es imprescindible para completar la instalación.
7. Pulsa **Instalar Ubuntu**.
8. Tipo: instalación interactiva.
9. Aplicaciones: selección predeterminada para una VM más ligera; amplía después si lo necesitas.
10. Revisa las opciones de software de terceros; no necesitas instalar controladores Radeon del anfitrión.
11. En disco, selecciona «Borrar disco e instalar Ubuntu» únicamente cuando el disco mostrado sea el VDI virtual de 80 GB.
12. Zona horaria: Madrid, si corresponde.
13. Crea usuario, nombre del equipo y contraseña robusta.
14. Revisa el resumen y confirma la instalación.
15. Espera a que termine y pulsa Reiniciar ahora.

Si el disco mostrado no tiene el tamaño esperado, apaga la VM sin confirmar y revisa Almacenamiento en VirtualBox. No continúes ante cualquier duda sobre el dispositivo de destino.

## 8. Primer arranque y actualización

Si vuelve a arrancar el instalador, apaga la VM y quita la ISO desde Configuración → Almacenamiento → unidad óptica → Quitar disco del dispositivo virtual. Después inicia desde el VDI.

Abre Terminal con `Ctrl+Alt+T`:

```bash
sudo apt update
sudo apt full-upgrade -y
sudo apt install -y build-essential dkms linux-headers-$(uname -r)
sudo reboot
```

Completa la bienvenida y los ajustes de privacidad.

## 9. Guest Additions

Guest Additions habilita mejor integración del ratón, resolución dinámica, portapapeles y carpetas compartidas. Si mantienes VirtualBox 7.0.2, utiliza la ISO Guest Additions de la misma versión.

1. Con Ubuntu encendido: Dispositivos → Insertar imagen de CD de las Guest Additions.
2. Si no se monta automáticamente, abre el gestor de archivos y monta el CD.
3. En Terminal:

```bash
sudo apt update
sudo apt install -y build-essential dkms linux-headers-$(uname -r)
ls /media/$USER/
# Entra en el directorio VBox_GAs_* que aparezca:
cd /media/$USER/VBox_GAs_*
sudo sh ./VBoxLinuxAdditions.run
sudo reboot
```

Si la ruta difiere, usa `ls /media/$USER/`. Si falla la compilación, consulta `/var/log/vboxadd-setup.log` y `dmesg`. Por la antigüedad de 7.0.2, puede ser necesario actualizar VirtualBox y Guest Additions a una versión mantenida.

Verifica tras reiniciar:

```bash
lsmod | grep -E 'vboxguest|vboxsf|vboxvideo'
systemctl status vboxadd-service --no-pager
echo "$XDG_SESSION_TYPE"
```

Prueba cambiar el tamaño de la ventana. No des por instalada correctamente Guest Additions solo porque Ubuntu arranque.

## 10. Carpeta compartida y portapapeles

1. Apaga Ubuntu.
2. Crea en Windows `C:\Users\TU_USUARIO\VirtualBox-Compartida`.
3. En VirtualBox → Configuración VM → Carpetas compartidas → Añadir.
4. Selecciona la carpeta, nombre `intercambio`, marca Automontar y Hacer permanente.
5. Arranca Ubuntu y ejecuta:

```bash
sudo usermod -aG vboxsf "$USER"
sudo reboot
ls -la /media/sf_intercambio
```

En Dispositivos → Portapapeles compartido elige Bidireccional. Puede requerir Guest Additions funcional. Comparte solo una carpeta dedicada, no todo el perfil de Windows.

## 11. Automatización: crear VM desde PowerShell

Se incluye `VirtualBox-Rober-crear-maquina.ps1`. Edita al principio `ISO_PATH` si tu nombre o ubicación de ISO cambia. El script no sobrescribe una VM existente y no inicia la instalación.

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\VirtualBox-Rober-crear-maquina.ps1
```

El script configura 6144 MB, 4 CPU, VMSVGA, 128 MB de vídeo, NAT y VDI dinámico de 80 GB. Comprueba el resumen antes de iniciar.

## 12. Automatización: postinstalación Ubuntu

Se incluye `VirtualBox-Rober-postinstalacion.sh`. Actualiza paquetes, instala herramientas y headers, y muestra datos de validación. No toca particiones ni instala drivers de la GPU anfitriona.

```bash
chmod +x VirtualBox-Rober-postinstalacion.sh
./VirtualBox-Rober-postinstalacion.sh
```

Requiere Internet y solicita contraseña sudo.

## 13. Validación final

Ejecuta y guarda la salida:

```bash
lsb_release -a
uname -a
nproc
free -h
df -h /
ip -brief address
lsmod | grep -E 'vboxguest|vboxsf|vboxvideo' || true
groups
ping -c 4 1.1.1.1
ping -c 4 ubuntu.com
```

Checklist:
- [ ] Ubuntu informa 24.04 LTS.
- [ ] La VM inicia desde VDI, no desde la ISO.
- [ ] Se ven 4 CPU virtuales y aproximadamente 6 GiB RAM.
- [ ] Red NAT y DNS funcionan.
- [ ] Guest Additions y redimensionado comprobados o incidencia registrada.
- [ ] Portapapeles y carpeta compartida probados.
- [ ] Se crea instantánea después de actualizar y validar.
- [ ] Se realiza copia externa de datos importantes.

## 14. Ajustes y mantenimiento

- Mantén 4 vCPU y 6 GB RAM al principio. Sube a 6 vCPU u 8 GB solo si el anfitrión mantiene margen.
- Mantén VMSVGA, 128 MB y 3D desactivado hasta validar estabilidad.
- Usa VDI dinámico 80 GB; amplía solo si el uso real lo exige.
- Actualiza Ubuntu con `sudo apt update && sudo apt full-upgrade`.
- Mantén VirtualBox y Extension Pack en versiones idénticas.
- Las instantáneas no sustituyen una copia externa y pueden crecer considerablemente.
- No borres manualmente archivos VDI/VBOX ni instantáneas desde el Explorador.

## 15. Solución de problemas

| Síntoma | Acción |
|---|---|
| No aparece Ubuntu 64-bit | Comprueba SVM en UEFI y Administrador de tareas; revisa conflictos del hipervisor Windows. |
| Error AMD-V/SVM | Verifica SVM, cierra otros hipervisores y reinicia. No desactives protecciones sin diagnóstico. |
| Pantalla negra/parpadeo | Desactiva 3D; conserva VMSVGA y 128 MB. |
| Resolución fija | Revisa Guest Additions, módulos y `/var/log/vboxadd-setup.log`. |
| Sin Internet | Comprueba Adaptador 1 habilitado/NAT; usa `ip a`, `ip route` y prueba DNS. |
| Carpeta compartida no aparece | Revisa Guest Additions, automontaje y grupo `vboxsf`; vuelve a iniciar sesión. |
| Reaparece el instalador | Desmonta la ISO de la unidad óptica. |
| Falta espacio | Revisa el tamaño del VDI y las instantáneas desde VirtualBox; no borres archivos manualmente. |
| Guest Additions no compila | Comprueba headers, build-essential, DKMS y log; considera actualizar VirtualBox. |

Al comunicar un fallo, conserva el error completo, versión de VirtualBox, kernel invitado y salida de:

```powershell
& "$env:ProgramFiles\Oracle\VirtualBox\VBoxManage.exe" showvminfo "Ubuntu 24.04 - Rober" --details
```

## 16. Referencias y capturas

- Ubuntu Desktop 24.04: https://ubuntu.com/desktop/docs/en/24.04/tutorial/install-ubuntu-desktop/
- ISO Ubuntu 24.04 AMD64: https://releases.ubuntu.com/24.04/
- VirtualBox 7.0.2: https://download.virtualbox.org/virtualbox/7.0.2/
- Manual VirtualBox 7.0.2: https://download.virtualbox.org/virtualbox/7.0.2/UserManual.pdf

Las capturas de las pantallas del asistente Ubuntu incluidas en la versión PDF/DOCX de esta guía se han extraído del PDF de referencia aportado por el usuario: «Guía Instalación Ubuntu 24.04 LTS en VirtualBox 7.0.26.pdf». Son orientativas; los valores de hardware deben seguir esta guía, no copiarse literalmente de las capturas.

---
**Paquete:** `VirtualBox-Rober` · **Ruta prevista en LEONES:** `docs/guides/VirtualBox-Rober/`
