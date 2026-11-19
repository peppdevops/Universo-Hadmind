"""Reglas de la Bitácora. Las vistas (api.py, views.py) y el admin solo llaman
a estas funciones; aquí está la lógica, aquí van los tests.
"""

from io import BytesIO

import markdown
import nh3
from django.conf import settings
from django.core import signing
from django.core.files.base import ContentFile
from django.template.loader import render_to_string
from django.urls import reverse
from django.utils import timezone
from django.utils.text import slugify
from PIL import Image, ImageOps

from .models import Articulo

# --- Contenido -----------------------------------------------------------

def markdown_a_html(texto):
    """Markdown -> HTML seguro.

    El texto lo escribe una IA (o alguien desde el admin) y se muestra en la
    web pública: nh3 deja solo etiquetas inofensivas (párrafos, títulos,
    listas, enlaces...) y quita <script>, eventos onclick, iframes, etc.
    """
    html = markdown.markdown(texto or '', extensions=['extra', 'sane_lists'])
    # Los enlaces externos se abren sin darle acceso a nuestra página.
    return nh3.clean(html, link_rel='noopener noreferrer nofollow')


def slug_unico(titulo, excluir_pk=None):
    """"Cinco procesos para automatizar" -> "cinco-procesos-para-automatizar".
    Si ya existe se le añade -2, -3...
    """
    base = slugify(titulo)[:200] or 'articulo'
    slug, n = base, 2
    otros = Articulo.objects.exclude(pk=excluir_pk)
    while otros.filter(slug=slug).exists():
        slug, n = f'{base}-{n}', n + 1
    return slug


def normalizar_categoria(valor):
    """La IA a veces manda "Inteligencia Artificial" en vez de la clave
    "inteligencia_artificial". Se aceptan las dos formas."""
    texto = slugify(str(valor or '')).replace('-', '_')
    for clave, nombre in Articulo.Categoria.choices:
        if texto in (clave, slugify(nombre).replace('-', '_')):
            return clave
    return valor


# --- Imagen --------------------------------------------------------------

ANCHO_MAXIMO = 1600       # suficiente para la página del artículo en pantallas grandes
CALIDAD_WEBP = 82
PESO_MAXIMO = 10 * 1024 * 1024  # 10 MB de entrada


class ImagenInvalida(ValueError):
    pass


def procesar_imagen(archivo, nombre):
    """Reduce la imagen y la convierte a WebP (pesa mucho menos que PNG/JPG,
    así la landing carga rápido en celular). Devuelve un archivo listo para
    asignar a articulo.imagen."""
    if archivo.size > PESO_MAXIMO:
        raise ImagenInvalida('La imagen pesa más de 10 MB.')
    try:
        imagen = Image.open(archivo)
        imagen.load()
    except Exception:  # Pillow lanza varios tipos de error según el archivo
        raise ImagenInvalida('El archivo no es una imagen válida.')
    if imagen.format not in ('JPEG', 'PNG', 'WEBP'):
        raise ImagenInvalida('Formato no permitido: usa JPG, PNG o WebP.')
    # Algunas fotos vienen giradas y la orientación está en los metadatos EXIF.
    imagen = ImageOps.exif_transpose(imagen)
    if imagen.mode not in ('RGB', 'RGBA'):
        imagen = imagen.convert('RGBA' if 'A' in imagen.getbands() else 'RGB')
    imagen.thumbnail((ANCHO_MAXIMO, ANCHO_MAXIMO))
    salida = BytesIO()
    imagen.save(salida, 'WEBP', quality=CALIDAD_WEBP, method=6)
    return ContentFile(salida.getvalue(), name=f'{nombre[:80]}.webp')


def poner_imagen(articulo, archivo):
    if articulo.imagen:
        articulo.imagen.delete(save=False)  # no dejar la anterior huérfana en disco
    articulo.imagen = procesar_imagen(archivo, articulo.slug)


# --- Revisión desde el correo -------------------------------------------
# El enlace del correo lleva el id del artículo FIRMADO con la SECRET_KEY:
# nadie puede inventar uno ni cambiar el id. Vence a los 7 días.

SAL_REVISION = 'blog.revision'
VIGENCIA_REVISION = 60 * 60 * 24 * 7


def token_revision(articulo):
    return signing.TimestampSigner(salt=SAL_REVISION).sign(str(articulo.pk))


def articulo_de_token(token):
    """Devuelve el artículo, o lanza signing.BadSignature (alterado) /
    signing.SignatureExpired (vencido; es subclase de BadSignature)."""
    pk = signing.TimestampSigner(salt=SAL_REVISION).unsign(token, max_age=VIGENCIA_REVISION)
    return Articulo.objects.get(pk=pk)


def url_revision(articulo):
    return reverse('blog:revisar', args=[token_revision(articulo)])


def url_absoluta(request, ruta):
    """Ruta -> dirección completa (https://...) para correos y redes sociales.

    Con SITIO_URL se usa el dominio público aunque la petición llegue por una
    dirección interna; sin ella, la de la petición (desarrollo y tests).
    """
    if settings.SITIO_URL:
        return settings.SITIO_URL + ruta
    return request.build_absolute_uri(ruta)


FUENTES_RECIENTES = 200


def fuentes_usadas():
    """Fuentes de los últimos artículos, también borradores y descartados, para
    que n8n no gaste OpenAI escribiendo una noticia que ya se usó o se rechazó."""
    return list(
        Articulo.objects.exclude(fuente_url='').order_by('-creado')
        .values_list('fuente_url', flat=True)[:FUENTES_RECIENTES]
    )


def correo_revision(request, articulo):
    """Asunto y HTML del correo de aprobación. El diseño vive aquí y no en
    n8n para que esté versionado con el resto del sitio; n8n solo lo envía."""
    revisar = url_absoluta(request, url_revision(articulo))
    html = render_to_string('blog/correo_revision.html', {
        'articulo': articulo,
        'url_revision': revisar,
        'url_imagen': url_absoluta(request, articulo.imagen.url) if articulo.imagen else '',
        'dias_vigencia': VIGENCIA_REVISION // (60 * 60 * 24),
    })
    return f'Bitácora: revisa «{articulo.titulo}»', html


# --- Cambios de estado ---------------------------------------------------

def publicar(articulo):
    articulo.estado = Articulo.Estado.PUBLICADO
    articulo.save()  # save() fija publicado_en la primera vez


def descartar(articulo):
    articulo.estado = Articulo.Estado.DESCARTADO
    articulo.save()


def volver_a_borrador(articulo):
    articulo.estado = Articulo.Estado.BORRADOR
    articulo.save()


def tiempo_relativo(fecha, ahora=None):
    """"Hace 2 horas", "Hace 3 días"... como en el boceto de la landing."""
    if not fecha:
        return ''
    segundos = int(((ahora or timezone.now()) - fecha).total_seconds())
    for unidad, singular, plural in (
        (60 * 60 * 24 * 365, 'año', 'años'), (60 * 60 * 24 * 30, 'mes', 'meses'),
        (60 * 60 * 24 * 7, 'semana', 'semanas'), (60 * 60 * 24, 'día', 'días'),
        (60 * 60, 'hora', 'horas'), (60, 'minuto', 'minutos'),
    ):
        if segundos >= unidad:
            n = segundos // unidad
            return f'Hace {n} {singular if n == 1 else plural}'
    return 'Hace un momento'


# --- Parte pública ----------------------------------------------------------

ARTICULOS_EN_INICIO = 4   # la más nueva y las 3 anteriores (boceto de la landing)
ARTICULOS_POR_PAGINA = 12  # 12 se reparte bien en 4, 3, 2 o 1 columnas


def articulos_para_inicio():
    """Los artículos de la sección "La Bitácora" del inicio."""
    return list(Articulo.objects.publicados()[:ARTICULOS_EN_INICIO])


def relacionados(articulo, cantidad=3):
    """Otros artículos para el final de la página: primero los de la misma
    categoría y, si no alcanzan, los más nuevos de cualquier categoría."""
    otros = Articulo.objects.publicados().exclude(pk=articulo.pk)
    elegidos = list(otros.filter(categoria=articulo.categoria)[:cantidad])
    if len(elegidos) < cantidad:
        ya = [a.pk for a in elegidos]
        elegidos += list(otros.exclude(pk__in=ya)[:cantidad - len(elegidos)])
    return elegidos
