"""Inicio del admin (dashboard).

unfold llama a dashboard_callback cada vez que alguien abre el Inicio
(settings.UNFOLD['DASHBOARD_CALLBACK']). Aquí NO se calcula nada: se piden los
datos a los services de cada app y se dejan listos para las plantillas
(textos, enlaces, colores). Las plantillas solo los muestran.

Qué ve cada uno:
- Vendedor: saludo, "Hoy" (sus empresas) y sus llamadas de la semana.
- Superusuario: además el embudo, las llamadas de todo el equipo y finanzas.
"""

from datetime import timedelta

from django.urls import reverse
from django.utils import timezone

from apps.crm import formato
from apps.crm.services import agenda_hoy, embudo, inicio_de_semana, llamadas_de_la_semana
from core import dashboard_ejemplo
from core.utils import telefono_legible, url_whatsapp

DIAS_LARGOS = ['Lunes', 'Martes', 'Miércoles', 'Jueves', 'Viernes', 'Sábado', 'Domingo']
MESES_LARGOS = [
    'enero', 'febrero', 'marzo', 'abril', 'mayo', 'junio',
    'julio', 'agosto', 'septiembre', 'octubre', 'noviembre', 'diciembre',
]


def saludo(usuario):
    hora = timezone.localtime().hour
    momento = 'Buenos días' if hora < 12 else 'Buenas tardes' if hora < 19 else 'Buenas noches'
    return f'{momento}, {usuario.first_name or usuario.username}'


def fecha_larga():
    hoy = timezone.localdate()
    return f'{DIAS_LARGOS[hoy.weekday()]} {hoy.day} de {MESES_LARGOS[hoy.month - 1]} de {hoy.year}'


def texto_semana():
    """"16 al 22 de nov" (lunes a domingo de esta semana)."""
    lunes = timezone.localtime(inicio_de_semana()).date()
    domingo = lunes + timedelta(days=6)
    return f'{lunes.day} al {domingo.day} de {formato.MESES[domingo.month - 1]}'


def url_registrar_llamada(contacto):
    # Cada empresa se abre desde la lista donde vive (por llamar o clientes),
    # directamente en la tabla de llamadas (#interacciones-group).
    modelo = 'clienteactivo' if contacto.etapa and contacto.etapa.es_cliente else 'empresaporllamar'
    return reverse(f'admin:crm_{modelo}_change', args=[contacto.pk]) + '#interacciones-group'


def fila_agenda(contacto):
    tipo, _ = formato.proxima_llamada(contacto.proxima_llamada)
    local = timezone.localtime(contacto.proxima_llamada)
    vencida = tipo == 'vencida'
    if vencida:
        cuando = formato.dia_mes(local)
    else:
        cuando = formato.hora(local) if formato.tiene_hora(local) else 'Hoy'
    return {
        'vencida': vencida,
        'cuando': cuando,
        'empresa': contacto.empresa,
        'detalle': ' · '.join(filter(None, [contacto.nombre_contacto, telefono_legible(contacto.telefono)])),
        'etapa': str(contacto.etapa or 'Sin etapa'),
        'color_etapa': formato.color_etapa(contacto.etapa),
        'vendedor': formato.nombre_corto(contacto.asignado_a) or 'Sin asignar',
        'whatsapp': url_whatsapp(contacto.telefono),
        'registrar': url_registrar_llamada(contacto),
    }


def datos_agenda(usuario, filtro):
    agenda = agenda_hoy(usuario, filtro)
    pestanas = [
        ('todas', 'Todas', agenda['total']),
        ('vencidas', 'Vencidas', agenda['vencidas']),
        ('hoy', 'Para hoy', agenda['hoy']),
    ]
    return {
        **agenda,
        'descripcion': f'{agenda["hoy"]} para hoy · {agenda["vencidas"]} vencidas',
        'filas': [fila_agenda(c) for c in agenda['contactos']],
        'pestanas': [
            {'clave': clave, 'texto': texto, 'cantidad': cantidad, 'activa': clave == agenda['filtro']}
            for clave, texto, cantidad in pestanas
        ],
    }


def datos_llamadas(usuario):
    # Superusuario: todo el equipo. Vendedor: solo él.
    filas = llamadas_de_la_semana(None if usuario.is_superuser else usuario)
    resultado = []
    for f in filas:
        nombre = ' '.join(filter(None, [f['usuario__first_name'], f['usuario__last_name']])) or f['usuario__username']
        porcentaje = round(f['contestaron'] * 100 / f['total']) if f['total'] else 0
        resultado.append({
            'nombre': nombre,
            'iniciales': formato.iniciales(f['usuario__first_name'], f['usuario__last_name'], f['usuario__username']),
            'total': f['total'],
            'contestaron': f['contestaron'],
            'interesados': f['interesados'],
            'porcentaje': porcentaje,
        })
    return {'semana': texto_semana(), 'filas': resultado}


def datos_embudo():
    datos = embudo()
    for fila in datos['filas']:
        fila['color'] = formato.color_etapa(fila['etapa'])
        if fila['anterior'] is None:
            fila['nota'] = f'{fila["de_total"]} % del total'
        elif fila['de_anterior'] is None:
            fila['nota'] = f'{fila["anterior"]} está vacía'
        else:
            # Es una foto de hoy, no una conversión: por eso no dice "pasa de".
            fila['nota'] = f'{fila["de_anterior"]} % frente a {fila["anterior"]}'
    datos['total_texto'] = f'{datos["total_empresas"]} empresas en total'
    return datos


def dashboard_callback(request, context):
    usuario = request.user
    context.update({
        'title': 'Inicio',
        'saludo': saludo(usuario),
        'fecha_hoy': fecha_larga(),
        'es_superusuario': usuario.is_superuser,
        'agenda': datos_agenda(usuario, request.GET.get('agenda', 'todas')),
        'llamadas': datos_llamadas(usuario),
    })
    if usuario.is_superuser:
        context.update({
            'url_importar': reverse('admin:crm_empresaporllamar_importar'),
            'url_nueva_empresa': reverse('admin:crm_empresaporllamar_add'),
            'embudo': datos_embudo(),
            'finanzas': dashboard_ejemplo.datos(),  # EJEMPLO hasta la fase 3
        })
    return context
