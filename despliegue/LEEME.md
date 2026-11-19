# Despliegue: seguridad y copias de seguridad

Guía para el VPS (`/opt/hadmind-web`). El ejemplo de Nginx está en `nginx-hadmind.conf`.

## 1. Variables de seguridad del `.env` de producción

```
DJANGO_DEBUG=0
ADMIN_URL=<dirección secreta del admin>
SITIO_EN_REMODELACION=1
SITIO_URL=https://hadmind.com.co
N8N_API_TOKEN=<clave larga>
```

- **`ADMIN_URL`**: genera una difícil de adivinar con
  `python3 -c "import secrets; print('gestion-' + secrets.token_urlsafe(8).lower())"`.
  El admin queda en `https://hadmind.com.co/<esa-dirección>/` y `/admin/` no existe.
  Guárdala junto a tus contraseñas: **no aparece en ningún enlace del sitio**.
- **`SITIO_EN_REMODELACION=1`**: los visitantes ven el aviso; tú, con sesión iniciada, ves todo.
  El día del lanzamiento cambia a `0` y reinicia con `docker compose -f docker-compose.prod.yml up -d`.

## 2. Primera entrada y cuentas del equipo

1. Crea tu superusuario:
   `docker compose -f docker-compose.prod.yml exec web python manage.py createsuperuser`
2. En el **computador**, abre `https://hadmind.com.co/<ADMIN_URL>/`. Los pasos son:
   1. Pon tu usuario y contraseña.
   2. Confirma la contraseña otra vez. Solo se pide la primera vez, para activar.
   3. Escanea el QR con **Google Authenticator** o **Microsoft Authenticator** y escribe el código de 6 dígitos.
   4. **Guarda los 10 códigos de recuperación** en papel o en un archivo fuera del celular. Si pierdes
     el celular, cada código sirve una vez en lugar de la app.
3. Crea la cuenta de cada persona en **Equipo → Usuarios**. En su primera entrada hará los mismos
   pasos 2 a 4 con su propio celular.

Desde ahí, cada entrada pide la contraseña y el **código de la app**. La sesión dura máximo
12 horas y se cierra al cerrar el navegador. Lo interno (admin, CRM, login, revisión de la
Bitácora) **no abre en celular**.

## 3. Problemas frecuentes

| Problema | Solución |
|---|---|
| "Acceso bloqueado por 1 hora" (5 contraseñas malas) | Esperar 1 hora o desbloquear: `docker compose -f docker-compose.prod.yml exec web python manage.py axes_reset` |
| Alguien olvidó la contraseña | El superusuario le asigna una nueva en Equipo → Usuarios. No hay recuperación por correo. |
| Alguien perdió el celular | Entra con uno de sus códigos de recuperación. Si no los tiene, el superusuario borra su autenticador en *Todas las aplicaciones → Authenticators* y en su próxima entrada activa la app en el celular nuevo. |
| Tú perdiste el celular y los códigos | Desde el VPS: `docker compose -f docker-compose.prod.yml exec web python manage.py shell -c "from allauth.mfa.models import Authenticator; Authenticator.objects.filter(user__username='TU_USUARIO').delete()"` |

## 4. Copias de seguridad

`backup.sh` copia la **base de datos** (CRM, Bitácora, usuarios) y las **imágenes** a
`/opt/backups/hadmind/`, y borra las de más de 14 días.

**Programarlo todos los días a las 3:00 a. m.** (`crontab -e` en el VPS, con el usuario que maneja Docker):

```
0 3 * * * /opt/hadmind-web/despliegue/backup.sh >> /var/log/hadmind-backup.log 2>&1
```

Para probarlo a mano: `/opt/hadmind-web/despliegue/backup.sh`, y luego `ls -lh /opt/backups/hadmind/`.

### Restaurar una copia

> Esto **reemplaza** los datos actuales por los de la copia. Úsalo solo si se perdió o dañó algo.

```bash
cd /opt/hadmind-web
COPIA=/opt/backups/hadmind/bd_2026-11-20_0300.dump   # la que quieras recuperar

# 1. Base de datos
docker compose -f docker-compose.prod.yml exec -T db sh -c \
  'pg_restore -U "$POSTGRES_USER" -d "$POSTGRES_DB" --clean --if-exists --no-owner' < "$COPIA"

# 2. Imágenes (si también se perdieron)
tar -xzf /opt/backups/hadmind/media_2026-11-20_0300.tar.gz -C /opt/hadmind-web

# 3. Reiniciar
docker compose -f docker-compose.prod.yml restart web
```

### Copia fuera del VPS

Si el VPS se daña, las copias que están en él también se pierden. Una vez por semana,
copia la carpeta a tu PC. Desde PowerShell en tu PC:

```
scp -r usuario@IP-DEL-VPS:/opt/backups/hadmind C:\Backups\
```

Otra opción, o como complemento: activar las copias automáticas del VPS en el panel de Hostinger.
