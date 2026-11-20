from django.db import connection
from django.http import HttpResponse
from django.shortcuts import redirect
from django.templatetags.static import static


def salud(request):
    """/salud/ para el chequeo de Docker: responde "ok" si la app y la base de
    datos funcionan. No usa la página de inicio porque con el aviso de
    remodelación esa responde 503 y Docker creería que la app está caída."""
    try:
        connection.ensure_connection()
    except Exception:
        return HttpResponse('sin base de datos', status=503, content_type='text/plain')
    return HttpResponse('ok', content_type='text/plain')


def favicon(request):
    """/favicon.ico: los navegadores lo piden solos, sin mirar el HTML. La
    dirección se calcula en cada visita (no al arrancar) porque en producción
    el archivo lleva un código de versión en el nombre."""
    return redirect(static('favicon/favicon.ico'), permanent=True)
