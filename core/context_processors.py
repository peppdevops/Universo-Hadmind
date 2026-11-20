from django.conf import settings
from django.urls import reverse

from . import contenido


def sitio(request):
    """Expone el contenido compartido como {{ sitio.* }} en todas las plantillas."""
    home = reverse('landing:home')
    menu = []
    for i, (id_, etiqueta, *url) in enumerate(contenido.MENU, start=1):
        if url:
            href = reverse(url[0])
        else:
            href = home if id_ == 'inicio' else f'{home}#{id_}'
        menu.append({'num': f'{i:02d}', 'etiqueta': etiqueta, 'href': href})
    return {
        'sitio': {
            'contacto': contenido.CONTACTO,
            'menu': menu,
            'servicios': contenido.SERVICIOS,
            # Para la franja que avisa al equipo que el sitio está oculto
            'en_remodelacion': settings.SITIO_EN_REMODELACION,
        },
    }


def unfold_en_cuenta(request):
    """Las pantallas de login y de verificación en 2 pasos (/cuenta/) usan la
    plantilla de login de unfold, que necesita los datos del admin (colores,
    título, estilos). Fuera de /cuenta/ no añade nada."""
    if not request.path.startswith('/cuenta/'):
        return {}
    from django.contrib import admin
    return admin.site.each_context(request)
