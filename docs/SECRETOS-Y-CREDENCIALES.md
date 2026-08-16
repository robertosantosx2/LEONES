# LEONES — Secretos y credenciales

## Estado

**🟢 Arquitectura funcional cerrada · configuración real pendiente**

Esta capa define cómo manejar credenciales de servicios externos sin introducir secretos en el repositorio ni en Atlas.

## Principio

```text
SECRETO
  ↓
SECRET MANAGER / GITHUB SECRETS
  ↓
WORKFLOW / SERVICIO
  ↓
ADIVINO / ALERTAS / OTROS
```

Los secretos son configuración de ejecución, nunca conocimiento del Atlas.

## Remitente de correo

Para el futuro circuito de alertas se reserva el remitente:

`mananadaleones.ia@gmail.com`

La dirección puede ser real, pero LEONES no debe almacenar su contraseña, token OAuth, app password ni claves SMTP en GitHub, código fuente, logs o documentos públicos.

## Configuración prevista

La cuenta de correo se conectará mediante el mecanismo seguro disponible en el entorno de ejecución. Como mínimo deberán existir secretos equivalentes a:

- `MAIL_FROM` — dirección remitente;
- `MAIL_PROVIDER` — proveedor/método;
- `MAIL_USERNAME` — solo si el proveedor lo requiere;
- `MAIL_PASSWORD` o `MAIL_APP_PASSWORD` — si aplica;
- `MAIL_OAUTH_CLIENT_ID` / `MAIL_OAUTH_CLIENT_SECRET` — si aplica;
- `MAIL_OAUTH_REFRESH_TOKEN` — si aplica.

Solo se almacenarán los secretos que realmente requiera el método elegido.

## Gmail

Para Gmail no se debe usar la contraseña normal de la cuenta en un script. La implementación deberá utilizar OAuth 2.0 o, cuando las condiciones de la cuenta lo permitan, una App Password con autenticación de dos factores.

La elección definitiva del método se hará durante la puesta en marcha y no forma parte del código canónico.

## GitHub Actions

Los secretos utilizados por workflows se introducirán mediante los mecanismos de Secrets/Variables de GitHub y se referenciarán en runtime. Nunca se escribirán valores reales en YAML, Markdown, `.env` versionado ni código.

Ejemplo conceptual:

```yaml
env:
  MAIL_FROM: ${{ secrets.MAIL_FROM }}
```

No se almacenan aquí valores reales.

## Desarrollo local

Para desarrollo local se utilizará un almacén de secretos fuera del repositorio o un `.env` ignorado por Git. Debe existir una plantilla sin valores:

```text
MAIL_FROM=
MAIL_PROVIDER=
MAIL_USERNAME=
MAIL_PASSWORD=
```

El `.env` real nunca se sube.

## Rotación

Las credenciales deben poder sustituirse sin cambiar código. Si una credencial se compromete, se revoca en el proveedor y se reemplaza en el almacén de secretos.

## Logs

Nunca se registran:

- contraseñas;
- tokens;
- refresh tokens;
- cookies de sesión;
- claves privadas;
- códigos de recuperación.

Los errores de autenticación se registran sin exponer el secreto.

## Principio de mínimo privilegio

El servicio de correo solo debe disponer de los permisos necesarios para enviar las notificaciones previstas. Un token de envío no debe tener acceso a Atlas, GitHub o datos que no necesite.

## Prueba de envío

La prueba de correo se hará únicamente después de configurar la credencial en el entorno seguro. El resultado de la prueba se registrará como evento de observabilidad, nunca la credencial.

El flujo previsto será:

```text
ADIVINO
  ↓
ALERTA
  ↓
MAIL
  ↓
respuesta humana: OK LEONES
  ↓
VALIDACIÓN
```

## Cierre

La arquitectura de secretos queda definida. **No se han incorporado credenciales reales al repositorio.** La cuenta `mananadaleones.ia@gmail.com` queda reservada como remitente hasta completar su configuración segura en el entorno de ejecución.
