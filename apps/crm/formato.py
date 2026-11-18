"""Cómo se muestran los datos del CRM (textos y colores).

Lo usan las listas del admin y el dashboard, para que una fecha o una etapa se
vean igual en todas partes. Aquí no se consulta la base de datos.
"""

from django.utils import timezone

MESES = ['ene', 'feb', 'mar', 'abr', 'may', 'jun', 'jul', 'ago', 'sep', 'oct', 'nov', 'dic']
DIAS = ['Lun', 'Mar', 'Mié', 'Jue', 'Vie', 'Sáb', 'Dom']

# Colores de etiqueta que trae unfold (unfold/helpers/label.html).
# Las etapas son datos (se pueden crear más), así que el color de las abiertas
# se reparte por su orden; cliente y final tienen color fijo.
COLORES_ETAPA_ABIERTA = ['default', 'info', 'warning', 'success']


def hora(dt):
    """9:30 a. m. (formato colombiano)."""
    h = dt.hour % 12 or 12
    return f'{h}:{dt.minute:02d} {"a. m." if dt.hour < 12 else "p. m."}'


def dia_mes(fecha):
    """16 nov"""
    return f'{fecha.day} {MESES[fecha.month - 1]}'


def tiene_hora(dt):
    # Las fechas que venían sin hora quedaron a las 00:00: no se muestra hora.
    return not (dt.hour == 0 and dt.minute == 0)


def proxima_llamada(dt):
    """(tipo, texto) de la próxima llamada.

    tipo: 'vencida' (su día ya pasó), 'hoy' o 'futura'. El texto sigue el
    diseño: "Vencida · 16 nov", "Hoy, 9:30 a. m.", "Jue 19 nov".
    """
    if dt is None:
        return None, '—'
    local = timezone.localtime(dt)
    hoy = timezone.localdate()
    if local.date() < hoy:
        return 'vencida', f'Vencida · {dia_mes(local)}'
    if local.date() == hoy:
        return 'hoy', f'Hoy, {hora(local)}' if tiene_hora(local) else 'Hoy'
    return 'futura', f'{DIAS[local.weekday()]} {dia_mes(local)}'


def color_etapa(etapa):
    """Tipo de etiqueta de unfold para una etapa.

    Se usa el campo "orden" (1, 2, 3...) para repartir colores sin consultar
    la base por cada fila de la lista.
    """
    if etapa is None:
        return 'default'
    if etapa.es_cliente:
        return 'primary'
    if etapa.es_final:
        return 'danger'
    return COLORES_ETAPA_ABIERTA[(max(etapa.orden, 1) - 1) % len(COLORES_ETAPA_ABIERTA)]


def nombre_corto(usuario):
    """"Laura Restrepo" -> "Laura R." (o el usuario si no tiene nombre)."""
    if usuario is None:
        return ''
    if usuario.first_name:
        inicial = f' {usuario.last_name[0]}.' if usuario.last_name else ''
        return f'{usuario.first_name}{inicial}'
    return usuario.username


def iniciales(nombre, apellido='', usuario=''):
    """"Laura", "Restrepo" -> "LR"."""
    if nombre:
        return (nombre[0] + (apellido[:1] or nombre[1:2])).upper()
    return usuario[:2].upper()
