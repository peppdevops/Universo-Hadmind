from django.urls import reverse

from . import contenido


def sitio(request):
    """Expone el contenido compartido como {{ sitio.* }} en todas las plantillas."""
    home = reverse('landing:home')
    menu = [
        {'num': f'{i:02d}', 'etiqueta': etiqueta, 'href': home if id_ == 'inicio' else f'{home}#{id_}'}
        for i, (id_, etiqueta) in enumerate(contenido.MENU, start=1)
    ]
    return {
        'sitio': {
            'contacto': contenido.CONTACTO,
            'menu': menu,
            'servicios': contenido.SERVICIOS,
        },
    }
