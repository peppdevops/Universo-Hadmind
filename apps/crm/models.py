from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Max, OuterRef, Q, Subquery
from django.db.models.functions import Lower
from django.utils import timezone

from core.utils import (
    InstagramInvalido, TelefonoInvalido, normalizar_correo, normalizar_instagram, normalizar_telefono, url_instagram,
)

# Nombre del grupo de Django para los vendedores. Lo usan el admin, el
# formulario de importación y el comando crear_grupo_vendedor.
GRUPO_VENDEDOR = 'Vendedor'


def vendedores_activos():
    """Usuarios que pueden recibir empresas asignadas."""
    return (
        get_user_model().objects
        .filter(is_active=True, groups__name=GRUPO_VENDEDOR)
        .order_by('first_name', 'username')
    )


class EtapaQuerySet(models.QuerySet):
    def abiertas(self):
        # "Abierta" = todavía se está trabajando: ni ganada (cliente) ni cerrada (final).
        return self.filter(es_cliente=False, es_final=False)


class Etapa(models.Model):
    nombre = models.CharField('nombre', max_length=60, unique=True)
    orden = models.PositiveSmallIntegerField(
        'orden', default=0, help_text='Las etapas se muestran de menor a mayor.',
    )
    es_cliente = models.BooleanField(
        'es cliente', default=False,
        help_text='Las empresas en esta etapa aparecen en "Clientes activos".',
    )
    es_final = models.BooleanField(
        'es final', default=False,
        help_text='Etapa de cierre sin venta (p. ej. "Perdido"): sale de las dos listas.',
    )

    objects = EtapaQuerySet.as_manager()

    class Meta:
        verbose_name = 'etapa'
        verbose_name_plural = 'etapas'
        ordering = ['orden', 'nombre']
        constraints = [
            # Una etapa no puede ser "cliente" y "final" a la vez: la empresa
            # no sabría en qué lista aparecer.
            models.CheckConstraint(
                condition=~(Q(es_cliente=True) & Q(es_final=True)),
                name='crm_etapa_cliente_o_final',
                violation_error_message='Una etapa no puede ser de cliente y final a la vez.',
            ),
        ]

    def __str__(self):
        return self.nombre


class ContactoQuerySet(models.QuerySet):
    """Filtros reutilizables: los usan los proxies, el admin y los tests."""

    def por_llamar(self):
        # Sin etapa también cuenta: así ninguna empresa queda "perdida" entre listas.
        return self.filter(
            Q(etapa__isnull=True) | Q(etapa__es_cliente=False, etapa__es_final=False)
        )

    def clientes_activos(self):
        return self.filter(etapa__es_cliente=True)

    def con_ultima_llamada(self):
        # Max calcula en la base de datos la fecha de la llamada más reciente
        # de cada contacto, en una sola consulta (en vez de una por fila).
        # Subquery trae además el resultado de esa llamada ("Contestó"...):
        # "de las llamadas de este contacto, ordenadas de la más nueva, el
        # resultado de la primera".
        ultima = Interaccion.objects.filter(contacto=OuterRef('pk')).order_by('-fecha')
        return self.annotate(
            ultima_llamada=Max('interacciones__fecha'),
            ultimo_resultado=Subquery(ultima.values('resultado')[:1]),
        )


class Contacto(models.Model):
    class Fuente(models.TextChoices):
        # (valor guardado en la base, texto visible)
        IMPORTACION = 'importacion', 'Importación'
        COTIZACION = 'cotizacion', 'Cotización web'
        BOT = 'bot', 'Bot'
        MANUAL = 'manual', 'Manual'

    empresa = models.CharField('empresa', max_length=200)
    nombre_contacto = models.CharField('contacto', max_length=150, blank=True)
    telefono = models.CharField(
        'teléfono', max_length=20, blank=True,
        help_text='Se guarda como +57XXXXXXXXXX. Para otros países, escríbelo con +código.',
    )
    correo = models.EmailField('correo', blank=True)
    ciudad = models.CharField('ciudad', max_length=100, blank=True)
    rubro = models.CharField('rubro', max_length=100, blank=True)
    # Se guarda solo el usuario, sin @ (máximo 30 caracteres, ver
    # normalizar_instagram); el enlace se arma al mostrarlo. max_length es
    # mayor porque el formulario mide lo que se PEGA antes de limpiarlo, y un
    # enlace copiado de la app ("...?igsh=...") pasa fácil de 30.
    instagram = models.CharField(
        'Instagram', max_length=200, blank=True,
        help_text='El usuario (@empresa) o el enlace del perfil; se guarda solo el usuario.',
    )
    fuente = models.CharField('fuente', max_length=20, choices=Fuente.choices, default=Fuente.MANUAL)
    # PROTECT: no se puede borrar una etapa mientras haya contactos en ella.
    # null=True: si no hay etapa, save() asigna la primera abierta.
    etapa = models.ForeignKey(
        Etapa, on_delete=models.PROTECT, null=True, blank=True,
        related_name='contactos', verbose_name='etapa',
    )
    # SET_NULL: si se borra un vendedor, sus empresas quedan sin asignar (no se borran).
    asignado_a = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='contactos_asignados', verbose_name='asignado a',
    )
    # Fecha Y hora: el dashboard ordena el día por hora ("9:30 a. m.").
    proxima_llamada = models.DateTimeField('próxima llamada', null=True, blank=True)
    notas = models.TextField('notas internas', blank=True)
    creado = models.DateTimeField('creado', auto_now_add=True)
    actualizado = models.DateTimeField('actualizado', auto_now=True)

    objects = ContactoQuerySet.as_manager()

    class Meta:
        verbose_name = 'contacto'
        verbose_name_plural = 'contactos'
        # Primero las que hay que llamar antes; las que no tienen fecha, al final.
        ordering = [models.F('proxima_llamada').asc(nulls_last=True), 'empresa']
        constraints = [
            # Duplicado = mismo teléfono O mismo correo. La condición excluye los
            # vacíos: muchas empresas pueden no tener correo y no son duplicadas.
            models.UniqueConstraint(
                fields=['telefono'],
                condition=~Q(telefono=''),
                name='crm_contacto_telefono_unico',
                violation_error_message='Ya existe un contacto con este teléfono.',
            ),
            # Lower(): la base compara en minúsculas aunque alguien guarde
            # "Ana@X.co" saltándose save() (por ejemplo con update()).
            models.UniqueConstraint(
                Lower('correo'),
                condition=~Q(correo=''),
                name='crm_contacto_correo_unico',
                violation_error_message='Ya existe un contacto con este correo.',
            ),
        ]
        indexes = [models.Index(fields=['proxima_llamada'])]

    def __str__(self):
        return self.empresa

    @property
    def url_instagram(self):
        return url_instagram(self.instagram)

    def normalizar(self):
        self.telefono = normalizar_telefono(self.telefono)
        self.correo = normalizar_correo(self.correo)
        self.instagram = normalizar_instagram(self.instagram)

    def clean(self):
        # El admin llama a clean() ANTES de comprobar las restricciones de
        # duplicados; por eso se normaliza aquí y no solo en save().
        try:
            self.normalizar()
        except TelefonoInvalido as error:
            raise ValidationError({'telefono': str(error)})
        except InstagramInvalido as error:
            raise ValidationError({'instagram': str(error)})
        if not self.telefono and not self.correo:
            raise ValidationError('Indica al menos un teléfono o un correo.')

    def save(self, *args, **kwargs):
        # También en save(): cubre los contactos creados desde código (bot,
        # formulario web) que no pasan por clean().
        self.normalizar()
        if self.etapa_id is None:
            self.etapa = Etapa.objects.abiertas().first()
        super().save(*args, **kwargs)


# --- Las dos listas del admin ------------------------------------------------
# Un modelo proxy usa la MISMA tabla que Contacto, pero Django lo trata como un
# modelo aparte: tiene su propio admin, su propio menú y sus propios permisos.
# Su manager filtra qué contactos pertenecen a cada lista.

class EmpresaPorLlamarManager(models.Manager.from_queryset(ContactoQuerySet)):
    def get_queryset(self):
        return super().get_queryset().por_llamar()


class ClienteActivoManager(models.Manager.from_queryset(ContactoQuerySet)):
    def get_queryset(self):
        return super().get_queryset().clientes_activos()


class EmpresaPorLlamar(Contacto):
    objects = EmpresaPorLlamarManager()

    class Meta:
        proxy = True
        # Solo cambia el nombre visible. El nombre interno (EmpresaPorLlamar)
        # se mantiene: renombrarlo cambiaría los permisos del grupo Vendedor.
        verbose_name = 'empresa'
        verbose_name_plural = 'empresas'


class ClienteActivo(Contacto):
    objects = ClienteActivoManager()

    class Meta:
        proxy = True
        verbose_name = 'cliente activo'
        verbose_name_plural = 'clientes activos'


class Interaccion(models.Model):
    class Resultado(models.TextChoices):
        CONTESTO = 'contesto', 'Contestó'
        NO_CONTESTO = 'no_contesto', 'No contestó'
        VOLVER_A_LLAMAR = 'volver_a_llamar', 'Pidió volver a llamar'
        INTERESADO = 'interesado', 'Interesado'
        NO_INTERESADO = 'no_interesado', 'No interesado'
        NUMERO_EQUIVOCADO = 'numero_equivocado', 'Número equivocado'

    contacto = models.ForeignKey(
        Contacto, on_delete=models.CASCADE, related_name='interacciones', verbose_name='contacto',
    )
    # editable=False: no aparece en los formularios; el admin lo llena con
    # quien registra la llamada, así nadie puede firmar a nombre de otro.
    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
        editable=False, related_name='interacciones', verbose_name='registrada por',
    )
    fecha = models.DateTimeField('fecha', default=timezone.now)
    resultado = models.CharField('resultado', max_length=20, choices=Resultado.choices)
    comentario = models.TextField('comentario', blank=True)

    # Resultados en los que alguien sí atendió el teléfono. Los usa el
    # dashboard para "contestaron". "Número equivocado" no cuenta: atendió
    # alguien, pero no la empresa.
    CONTESTARON = [
        Resultado.CONTESTO, Resultado.VOLVER_A_LLAMAR, Resultado.INTERESADO, Resultado.NO_INTERESADO,
    ]

    class Meta:
        verbose_name = 'llamada'
        verbose_name_plural = 'llamadas'
        ordering = ['-fecha']

    def __str__(self):
        return f'{self.contacto} · {self.get_resultado_display()}'
