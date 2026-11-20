from django import template

from .. import services

register = template.Library()


@register.filter
def hace(fecha):
    """{{ articulo.publicado_en|hace }} → "Hace 3 días", como en el boceto."""
    return services.tiempo_relativo(fecha)
