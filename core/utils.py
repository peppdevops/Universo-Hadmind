"""Utilidades compartidas entre apps (CRM, formularios de la landing, bots...)."""

import re
import unicodedata


class TelefonoInvalido(ValueError):
    """El texto no se puede convertir en un teléfono con código de país."""


def quitar_tildes(texto):
    # NFKD separa cada letra de su tilde ("é" -> "e" + "´"); al codificar a
    # ASCII ignorando errores, la tilde desaparece y queda la letra sola.
    return unicodedata.normalize('NFKD', texto).encode('ascii', 'ignore').decode('ascii')


def normalizar_telefono(valor):
    """Devuelve el teléfono en formato internacional (+57XXXXXXXXXX).

    Se guarda siempre igual para que "300 123 4567", "573001234567" y
    "+57 300-123-4567" se reconozcan como el mismo número al buscar duplicados.
    """
    valor = (valor or '').strip()
    if not valor:
        return ''

    digitos = re.sub(r'\D', '', valor)

    if valor.startswith('+'):
        # Ya trae código de país: se respeta (clientes de otros países).
        if digitos.startswith('57') and len(digitos) != 12:
            raise TelefonoInvalido(f'Teléfono de Colombia no válido: {valor}')
        if 8 <= len(digitos) <= 15:  # E.164 permite como máximo 15 dígitos
            return f'+{digitos}'
        raise TelefonoInvalido(f'Teléfono no válido: {valor}')

    # Sin "+": se asume Colombia. Celulares y fijos tienen 10 dígitos.
    if len(digitos) == 10:
        return f'+57{digitos}'
    if len(digitos) == 12 and digitos.startswith('57'):
        return f'+{digitos}'
    raise TelefonoInvalido(f'Teléfono no válido: {valor}')


def normalizar_correo(valor):
    # Los correos no distinguen mayúsculas en la práctica: "Ana@X.co" y
    # "ana@x.co" son la misma persona, así que se guardan en minúsculas.
    return (valor or '').strip().lower()


def normalizar_encabezado(valor):
    """"Teléfono " -> "telefono"; "Nombre Contacto" -> "nombre_contacto"."""
    texto = quitar_tildes((valor or '').strip().lower())
    return re.sub(r'[\s\-]+', '_', texto)


def telefono_legible(telefono):
    """"+573105550142" -> "310 555 0142" (para mostrar; en la base sigue con +57).

    Los de otros países se muestran tal cual, con su código.
    """
    if telefono.startswith('+57') and len(telefono) == 13:
        n = telefono[3:]
        return f'{n[:3]} {n[3:6]} {n[6:]}'
    return telefono


def url_whatsapp(telefono):
    """Enlace wa.me para abrir el chat, o '' si el número no puede tener WhatsApp.

    En Colombia los celulares empiezan por 3; los fijos (601, 604...) no tienen
    WhatsApp y wa.me daría error, así que no se ofrece el botón.
    """
    if not telefono:
        return ''
    if telefono.startswith('+57') and not telefono.startswith('+573'):
        return ''
    return f'https://wa.me/{telefono.lstrip("+")}'


def pesos(valor):
    """1250000 -> "$1.250.000" (pesos colombianos, sin decimales, punto de miles)."""
    return '$' + f'{valor:,}'.replace(',', '.')
