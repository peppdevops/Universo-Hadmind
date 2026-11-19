from django.db import connection
from django.http import HttpResponse


def salud(request):
    """/salud/ para el chequeo de Docker: responde "ok" si la app y la base de
    datos funcionan. No usa la página de inicio porque con el aviso de
    remodelación esa responde 503 y Docker creería que la app está caída."""
    try:
        connection.ensure_connection()
    except Exception:
        return HttpResponse('sin base de datos', status=503, content_type='text/plain')
    return HttpResponse('ok', content_type='text/plain')
