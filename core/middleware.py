"""Middlewares del sitio:

- SoloComputador: lo interno (admin, CRM, login, revisión de la Bitácora) no
  abre en celular; sale un aviso con un chiste.
- ModoRemodelacion: con SITIO_EN_REMODELACION=1 los visitantes solo ven el
  aviso "Estamos en remodelación"; el equipo con sesión ve el sitio completo.
- ExigirDosPasos: nadie del equipo entra al admin sin la verificación en
  2 pasos activada.
"""

import random
import re

from django.conf import settings
from django.shortcuts import redirect, render
from django.urls import reverse


def ruta_admin():
    # Por nombre y no '/admin/': la dirección real sale de ADMIN_URL (.env)
    return reverse('admin:index')


# --- Solo desde el computador ------------------------------------------------

# "Mobi" es la marca que ponen los celulares en su User-Agent (iPhone, Android
# con "Mobile", etc.). Las tablets no la ponen (el iPad dice ser un Mac), así
# que pueden entrar. Se detecta por el dispositivo y no por el tamaño de la
# ventana: achicar la ventana del computador no muestra el chiste.
ES_CELULAR = re.compile(r'Mobi|iPhone|iPod', re.IGNORECASE)

CHISTES = [
    ('Error 418', 'Soy un CRM, no una app de celular. Ábreme en un computador.'),
    ('Así no', 'Trabajar en el celular es como cocinar en el comedor: se puede, pero queda todo regado.'),
    ('Horario de oficina', 'Este CRM tiene escritorio propio y horario de oficina. Te espero en el computador ☕.'),
    ('Siéntate un ratico', 'Desde el celular se llama a los clientes, no se llenan tablas.'),
    ('Descanso merecido', 'Tu pulgar ya trabajó mucho hoy. Dale el turno al teclado.'),
]


def es_celular(request):
    return bool(ES_CELULAR.search(request.headers.get('User-Agent', '')))


class SoloComputador:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        interno = request.path.startswith((ruta_admin(), '/cuenta/', '/bitacora/revisar/'))
        if interno and es_celular(request):
            titulo, chiste = random.choice(CHISTES)
            respuesta = render(request, 'solo_computador.html', {'titulo': titulo, 'chiste': chiste})
        else:
            respuesta = self.get_response(request)
        if interno:
            # La misma dirección responde distinto según el dispositivo: que
            # ningún caché le muestre al computador la página del celular.
            respuesta['Vary'] = 'User-Agent' if 'Vary' not in respuesta else respuesta['Vary'] + ', User-Agent'
        return respuesta


# --- Modo remodelación -------------------------------------------------------

# Lo que sigue funcionando con el aviso puesto: estilos e imágenes, chequeo de
# salud de Docker, la API de n8n, la página de revisión del correo (tiene su
# propia llave: el enlace firmado) y el login (/cuenta/).
RUTAS_LIBRES = ('/static/', '/media/', '/salud/', '/api/', '/bitacora/revisar/', '/cuenta/')

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
        if request.path.startswith(RUTAS_LIBRES + (ruta_admin(),)):
            return True
        return request.user.is_authenticated and request.user.is_staff


# --- Verificación en 2 pasos obligatoria -------------------------------------

def tiene_dos_pasos(usuario):
    from allauth.mfa.models import Authenticator
    return Authenticator.objects.filter(user=usuario, type=Authenticator.Type.TOTP).exists()


class ExigirDosPasos:
    """Quien es del equipo y aún no activó la app del celular va directo a
    activarla; no puede usar el admin ni el CRM hasta hacerlo. Así también
    se cubren las sesiones abiertas antes de existir esta regla."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        usuario = request.user
        if (settings.EXIGIR_DOS_PASOS
                and usuario.is_authenticated and usuario.is_staff
                and request.path.startswith(ruta_admin())
                and not tiene_dos_pasos(usuario)):
            return redirect('mfa_activate_totp')
        return self.get_response(request)
