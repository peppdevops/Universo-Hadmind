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
        },
    }
