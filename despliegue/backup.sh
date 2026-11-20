#!/usr/bin/env bash
# Copia de seguridad de HADMIND: base de datos (CRM, Bitácora, usuarios) e
# imágenes de la Bitácora. Guarda las de los últimos 14 días.
#
# En el VPS (cron, todos los días a las 3:00 a. m.):
#   0 3 * * * /opt/hadmind-web/despliegue/backup.sh >> /var/log/hadmind-backup.log 2>&1
# A mano:  /opt/hadmind-web/despliegue/backup.sh
# Restaurar: ver despliegue/LEEME.md
set -euo pipefail

PROYECTO="${PROYECTO:-/opt/hadmind-web}"
DESTINO="${DESTINO:-/opt/backups/hadmind}"
COMPOSE="${COMPOSE:-docker compose -f docker-compose.prod.yml}"
GUARDAR_DIAS="${GUARDAR_DIAS:-14}"
FECHA="$(date +%Y-%m-%d_%H%M)"

# Las copias tienen datos de clientes: solo el dueño de la carpeta las lee.
umask 077
mkdir -p "$DESTINO"
cd "$PROYECTO"

# 1) Base de datos. Formato "custom" de PostgreSQL (-Fc): ya va comprimido y se
#    restaura con pg_restore. Primero a un .tmp: si falla a mitad, no queda una
#    copia rota con nombre de buena.
$COMPOSE exec -T db sh -c 'pg_dump -U "$POSTGRES_USER" -d "$POSTGRES_DB" -Fc' > "$DESTINO/bd_$FECHA.dump.tmp"
if [ ! -s "$DESTINO/bd_$FECHA.dump.tmp" ]; then
    echo "$(date '+%F %T') ERROR: la copia de la base de datos salió vacía" >&2
    rm -f "$DESTINO/bd_$FECHA.dump.tmp"
    exit 1
fi
mv "$DESTINO/bd_$FECHA.dump.tmp" "$DESTINO/bd_$FECHA.dump"

# 2) Imágenes de la Bitácora (carpeta media/)
if [ -d media ]; then
    tar -czf "$DESTINO/media_$FECHA.tar.gz" media
fi

# 3) Borrar las copias de más de GUARDAR_DIAS días
find "$DESTINO" -maxdepth 1 \( -name 'bd_*.dump' -o -name 'media_*.tar.gz' \) -mtime +"$GUARDAR_DIAS" -delete

echo "$(date '+%F %T') OK: $(du -h "$DESTINO/bd_$FECHA.dump" | cut -f1) bd_$FECHA.dump"
