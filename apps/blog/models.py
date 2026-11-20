"""La Bitácora: artículos del blog.

Llegan casi siempre desde n8n (api.py) como BORRADOR. Solo se ven en la web
cuando alguien los publica desde el correo de revisión o desde el admin.
"""

from django.db import models
from django.db.models import Q
from django.utils import timezone


class ArticuloQuerySet(models.QuerySet):
    def publicados(self):
        # Lo único que ve la gente. Más reciente primero.
        return self.filter(estado=Articulo.Estado.PUBLICADO).order_by('-publicado_en')


class Articulo(models.Model):
    class Categoria(models.TextChoices):
        # Las del boceto de la landing. n8n debe enviar una de estas claves.
        INTELIGENCIA_ARTIFICIAL = 'inteligencia_artificial', 'Inteligencia artificial'
        AUTOMATIZACION = 'automatizacion', 'Automatización'
        SOFTWARE = 'software', 'Software'
        STARTUPS = 'startups', 'Startups'
        PYMES = 'pymes', 'Pymes'

    class Estado(models.TextChoices):
        BORRADOR = 'borrador', 'Borrador'
        PUBLICADO = 'publicado', 'Publicado'
        DESCARTADO = 'descartado', 'Descartado'

    class Origen(models.TextChoices):
        N8N = 'n8n', 'n8n (automático)'
        MANUAL = 'manual', 'Manual'

    titulo = models.CharField('título', max_length=200)
    # La parte final de la dirección: /bitacora/<slug>/. Se crea del título.
    slug = models.SlugField('slug', max_length=220, unique=True)
    categoria = models.CharField('categoría', max_length=30, choices=Categoria.choices)
    resumen = models.TextField(
        'resumen', max_length=400,
        help_text='Una o dos frases. Se ve en la tarjeta y en Google.',
    )
    contenido = models.TextField(
        'contenido', help_text='En Markdown: ## subtítulos, **negrita**, listas con -.',
    )
    # HTML ya convertido y limpio (se guarda para no convertir en cada visita).
    contenido_html = models.TextField(editable=False, default='')

    imagen = models.ImageField('imagen', upload_to='bitacora/%Y/%m/', blank=True)
    imagen_alt = models.CharField(
        'descripción de la imagen', max_length=200, blank=True,
        help_text='Para lectores de pantalla y Google. Si está vacía se usa el título.',
    )
    # Se guarda para saber con qué se generó la imagen (y repetirla si falla).
    prompt_imagen = models.TextField('prompt de la imagen', blank=True)

    fuente_nombre = models.CharField('fuente', max_length=120, blank=True)
    fuente_url = models.URLField('enlace de la fuente', max_length=500, blank=True)

    estado = models.CharField('estado', max_length=12, choices=Estado.choices, default=Estado.BORRADOR)
    origen = models.CharField('origen', max_length=10, choices=Origen.choices, default=Origen.MANUAL)
    publicado_en = models.DateTimeField('publicado', null=True, blank=True)
    creado = models.DateTimeField('creado', auto_now_add=True)
    actualizado = models.DateTimeField('actualizado', auto_now=True)

    objects = ArticuloQuerySet.as_manager()

    class Meta:
        verbose_name = 'artículo de la bitácora'
        verbose_name_plural = 'bitácora'
        ordering = ['-creado']
        constraints = [
            # La misma noticia (misma fuente) no se guarda dos veces, aunque
            # n8n la envíe de nuevo. Los artículos manuales pueden no tener fuente.
            models.UniqueConstraint(
                fields=['fuente_url'], condition=~Q(fuente_url=''),
                name='blog_articulo_fuente_unica',
                violation_error_message='Ya existe un artículo con esa fuente.',
            ),
        ]
        indexes = [models.Index(fields=['estado', '-publicado_en'])]

    def __str__(self):
        return self.titulo

    def save(self, *args, **kwargs):
        # Import aquí: services importa este módulo (evita importación circular).
        from .services import markdown_a_html
        self.contenido_html = markdown_a_html(self.contenido)
        # La fecha de publicación se fija la primera vez que se publica.
        if self.estado == self.Estado.PUBLICADO and not self.publicado_en:
            self.publicado_en = timezone.now()
        super().save(*args, **kwargs)

    @property
    def texto_alternativo(self):
        return self.imagen_alt or self.titulo
