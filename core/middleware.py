"""Modo remodelación: mientras SITIO_EN_REMODELACION=1, los visitantes solo ven
el aviso "Estamos en remodelación". El equipo (con sesión en el admin) ve el
sitio completo para revisarlo en el servidor real sin que nadie más lo vea.
"""

from django.conf import settings
from django.shortcuts import render
from django.urls import reverse

# Lo que sigue funcionando con el aviso puesto:
# estilos e imágenes, chequeo de salud de Docker, la API de n8n y la página de
# revisión del correo (que tiene su propia llave: el enlace firmado).
RUTAS_LIBRES = ('/static/', '/media/', '/salud/', '/api/', '/bitacora/revisar/')

# 1 día: le dice a Google "es temporal, vuelve mañana"
REINTENTAR_EN = 60 * 60 * 24


class ModoRemodelacion:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if settings.SITIO_EN_REMODELACION and not self.puede_pasar(request):
            # 503 = "no disponible por ahora": Google no reemplaza el sitio por
            # el aviso en sus resultados, entiende que es temporal.
            respuesta = render(request, 'remodelacion.html', status=503)
            respuesta['Retry-After'] = str(REINTENTAR_EN)
            return respuesta
        return self.get_response(request)

    @staticmethod
    def puede_pasar(request):
        # El admin (y su login) por su prefijo real, que cambiará al hacerlo secreto
        if request.path.startswith(RUTAS_LIBRES + (reverse('admin:index'),)):
            return True
        return request.user.is_authenticated and request.user.is_staff
