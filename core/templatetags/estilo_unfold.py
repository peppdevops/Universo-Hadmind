"""Clases de unfold para las pantallas de allauth (login, verificación en
2 pasos). Los formularios de allauth usan campos normales de Django; estas
herramientas les ponen las mismas clases que unfold usa en el admin, para que
se vean igual sin inventar estilos."""

from django import template
from unfold.widgets import CHECKBOX_CLASSES, INPUT_CLASSES, TEXTAREA_CLASSES

register = template.Library()


@register.filter
def campo_unfold(campo):
    """{{ campo|campo_unfold }} → el campo con las clases de unfold."""
    tipo = getattr(campo.field.widget, 'input_type', None)
    if tipo == 'checkbox':
        clases = CHECKBOX_CLASSES
    elif campo.field.widget.__class__.__name__ == 'Textarea':
        clases = TEXTAREA_CLASSES
    else:
        clases = INPUT_CLASSES
    return campo.as_widget(attrs={'class': ' '.join(clases)})


@register.simple_tag
def clases_unfold(tipo='input'):
    """Clases para campos escritos a mano en la plantilla (sin formulario)."""
    return ' '.join({'checkbox': CHECKBOX_CLASSES, 'textarea': TEXTAREA_CLASSES}.get(tipo, INPUT_CLASSES))
