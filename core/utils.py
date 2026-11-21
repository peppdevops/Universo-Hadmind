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


class InstagramInvalido(ValueError):
    """El texto no es un usuario ni un enlace de perfil de Instagram."""


# Usuario de Instagram: letras, números, punto y guion bajo; máximo 30.
USUARIO_INSTAGRAM = re.compile(r'^[a-z0-9._]{1,30}$')
# Rutas de instagram.com que no son perfiles (publicaciones, reels, historias...).
RUTAS_NO_PERFIL = {'p', 'reel', 'reels', 'stories', 'explore', 'tv', 'accounts', 'direct'}


def normalizar_instagram(valor):
    """Devuelve solo el usuario, en minúsculas y sin @.

    Se acepta como lo copie el vendedor: "@Ferreteria.Tornillo",
    "ferreteria.tornillo" o "https://www.instagram.com/ferreteria.tornillo/?hl=es".
    Se guarda solo el usuario (y no el enlace) para que dos formas del mismo
    perfil queden iguales; el enlace se arma al mostrarlo (url_instagram).
    """
    texto = (valor or '').strip()
    if not texto:
        return ''
    enlace = re.match(r'^(?:https?://)?(?:www\.|m\.)?instagram\.com/([^/?#]*)', texto, re.IGNORECASE)
    usuario = (enlace.group(1) if enlace else texto).lstrip('@').lower()
    if usuario in RUTAS_NO_PERFIL or not USUARIO_INSTAGRAM.match(usuario):
        raise InstagramInvalido(
            f'«{valor}» no es un usuario de Instagram. Escribe el usuario (@empresa) o el enlace del perfil.'
        )
    return usuario


def url_instagram(usuario):
    return f'https://www.instagram.com/{usuario}/' if usuario else ''


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


def pesos(valor):
    """1250000 -> "$1.250.000" (pesos colombianos, sin decimales, punto de miles)."""
    return '$' + f'{valor:,}'.replace(',', '.')
