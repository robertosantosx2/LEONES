#requires -Version 5.1
# VirtualBox-Rober-crear-maquina.ps1
# Crea la VM; no inicia instalación ni modifica discos físicos.
$ErrorActionPreference = "Stop"
$VM_NAME = "Ubuntu 24.04 - Rober"
$VM_BASE = Join-Path $env:USERPROFILE "VirtualBox VMs"
$VM_DIR = Join-Path $VM_BASE $VM_NAME
$ISO_PATH = Join-Path $env:USERPROFILE "Downloads\ubuntu-24.04.5-desktop-amd64.iso"
$RAM_MB = 6144
$CPUS = 4
$DISK_GB = 80
$VBox = Join-Path $env:ProgramFiles "Oracle\VirtualBox\VBoxManage.exe"
if (-not (Test-Path $VBox)) { throw "No se encuentra VBoxManage: $VBox" }
if (-not (Test-Path $ISO_PATH)) { throw "No se encuentra la ISO: $ISO_PATH. Edita ISO_PATH." }
New-Item -ItemType Directory -Force -Path $VM_BASE | Out-Null
$existing = & $VBox list vms
if ($existing -match [regex]::Escape($VM_NAME)) { throw "Ya existe '$VM_NAME'; no se sobrescribe." }
Write-Host "[1/5] Creando VM..." -ForegroundColor Cyan
& $VBox createvm --name $VM_NAME --ostype Ubuntu_64 --basefolder $VM_BASE --register
Write-Host "[2/5] Configurando recursos..." -ForegroundColor Cyan
& $VBox modifyvm $VM_NAME --memory $RAM_MB --cpus $CPUS --cpuexecutioncap 100 --vram 128 --graphicscontroller vmsvga --accelerate3d off --nic1 nat --boot1 dvd --boot2 disk --boot3 none --boot4 none
Write-Host "[3/5] Creando VDI dinámico..." -ForegroundColor Cyan
$diskDir = Join-Path $VM_DIR "Disks"
New-Item -ItemType Directory -Force -Path $diskDir | Out-Null
$diskPath = Join-Path $diskDir "Ubuntu-24.04-Rober.vdi"
& $VBox createmedium disk --filename $diskPath --size ([int]($DISK_GB * 1024)) --format VDI --variant Standard
Write-Host "[4/5] Conectando almacenamiento e ISO..." -ForegroundColor Cyan
& $VBox storagectl $VM_NAME --name "SATA" --add sata --controller IntelAhci --portcount 2
& $VBox storageattach $VM_NAME --storagectl "SATA" --port 0 --device 0 --type hdd --medium $diskPath
& $VBox storagectl $VM_NAME --name "IDE" --add ide
& $VBox storageattach $VM_NAME --storagectl "IDE" --port 0 --device 0 --type dvddrive --medium $ISO_PATH
Write-Host "[5/5] Resumen:" -ForegroundColor Cyan
& $VBox showvminfo $VM_NAME --details
Write-Host "VM creada. Revisa el resumen antes de iniciar." -ForegroundColor Green
