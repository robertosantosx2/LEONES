# Instalación in-device — ODS + Magnitude

## Debian / Ubuntu

### Servidor de Stacks IA — ODS

```bash
curl -fsSL https://install.osmantic.com/ods.sh | bash
```

### Asistente personal IA — Magnitude

```bash
npm install -g @magnitudedev/cli
```

Después:

```bash
magnitude
```

## Red Hat / RHEL / Rocky

### ODS

Validar primero Docker/Compose y la aceleración disponible. Después:

```bash
curl -fsSL https://install.osmantic.com/ods.sh | bash
```

### Magnitude

Instalar Node.js/npm compatible con la distribución y después:

```bash
npm install -g @magnitudedev/cli
magnitude
```

## Reglas LEONES

- ODS corresponde al perfil **Servidor de Stacks IA**.
- Magnitude corresponde al perfil **Asistente personal IA**.
- La instalación no implica telemetría.
- La telemetría requiere consentimiento.
- Nunca recoger prompts, documentos, conversaciones, secretos, tokens o API keys.
- Los valores estimados y medidos deben permanecer separados.
