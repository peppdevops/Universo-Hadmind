from django.contrib import admin, messages
from django.contrib.admin.utils import flatten_fieldsets
from django.shortcuts import redirect
from django.template.response import TemplateResponse
from django.urls import reverse
from django.utils import timezone
from django.utils.html import format_html
from unfold.admin import ModelAdmin, TabularInline
from unfold.decorators import action, display

from core.utils import TelefonoInvalido, normalizar_telefono, telefono_legible

from . import formato
from .forms import ImportarCSVForm
from .models import ClienteActivo, Contacto, EmpresaPorLlamar, Etapa, Interaccion, vendedores_activos
from .services import ErrorImportacion, contar_para_hoy, importar_contactos_csv

# Lo único que un vendedor puede modificar de una empresa.
CAMPOS_EDITABLES_VENDEDOR = ('etapa', 'proxima_llamada')


def _resumir(filas, maximo=15):
    """[(3, 'motivo'), ...] -> "fila 3 (motivo), fila 7 (motivo)… y 4 más"."""
    texto = ', '.join(f'fila {numero} ({motivo})' for numero, motivo in filas[:maximo])
    if len(filas) > maximo:
        texto += f'… y {len(filas) - maximo} más'
    return texto


@admin.register(Etapa)
class EtapaAdmin(ModelAdmin):
    list_display = ['nombre', 'orden', 'es_cliente', 'es_final']
    # list_editable permite cambiar el orden directamente desde la lista.
    list_editable = ['orden']
    ordering = ['orden']


class LlamadaInline(TabularInline):
    """Las llamadas se registran dentro de cada empresa, como una tabla."""

    model = Interaccion
    extra = 1  # una fila vacía lista para anotar la llamada nueva
    fields = ['fecha', 'resultado', 'comentario', 'usuario']
    readonly_fields = ['usuario']

    # El historial no se reescribe: solo el superusuario corrige o borra
    # llamadas. Al vendedor las anteriores le aparecen como solo lectura.
    def has_change_permission(self, request, obj=None):
        return request.user.is_superuser

    def has_delete_permission(self, request, obj=None):
        return request.user.is_superuser


class ContactoAdminBase(ModelAdmin):
    """Comportamiento común a las tres listas (por llamar, clientes, todos).

    Hereda de unfold.admin.ModelAdmin (y no del de Django) solo para tomar su
    apariencia: unfold.ModelAdmin es una subclase del ModelAdmin de Django, así
    que todos los permisos y métodos de abajo funcionan igual que antes.
    """

    # Columnas del diseño. Las que empiezan por "col_" son métodos de abajo que
    # deciden qué texto y qué color mostrar; el dato sigue siendo el mismo.
    list_display = [
        'col_empresa', 'nombre_contacto', 'col_telefono', 'col_etapa', 'col_vendedor',
        'col_proxima', 'col_ultima', 'col_acciones',
    ]
    list_per_page = 25
    list_filter = ['etapa', 'asignado_a', 'fuente', 'ciudad']
    # Frase de arriba de la lista: "253 empresas · 7 llamadas para hoy".
    list_before_template = 'admin/crm/_resumen_lista.html'
    # Resumen de la empresa arriba del formulario (WhatsApp, llamar, etapa...).
    change_form_before_template = 'admin/crm/_resumen_empresa.html'
    search_fields = ['empresa', 'nombre_contacto', 'telefono', 'correo']
    # select_related trae etapa y vendedor en la misma consulta (evita una
    # consulta extra por cada fila de la lista).
    list_select_related = ['etapa', 'asignado_a']
    inlines = [LlamadaInline]
    fieldsets = [
        ('Seguimiento', {'fields': ['etapa', 'asignado_a', 'proxima_llamada', 'notas']}),
        ('Datos de la empresa', {'fields': ['empresa', 'nombre_contacto', 'telefono', 'correo', 'instagram', 'ciudad', 'rubro', 'fuente']}),
        ('Registro', {'fields': ['creado', 'actualizado'], 'classes': ['collapse']}),
    ]
    readonly_fields = ['creado', 'actualizado']

    # El detalle se divide en tres pestañas. unfold solo ofrece pestañas de
    # campos DENTRO de una pestaña "General" y la tabla de llamadas como otra
    # pestaña aparte (dos niveles); esta plantilla las pone en una sola barra.
    change_form_template = 'admin/crm/contacto_change_form.html'
    # Qué bloques (fieldsets) van en cada pestaña. Seguimiento es la primera:
    # es lo que el vendedor cambia después de cada llamada.
    PESTANAS = [
        ('seguimiento', 'Seguimiento', ['Seguimiento']),
        ('llamadas', 'Llamadas', []),  # aquí va la tabla de llamadas (inline)
        ('empresa', 'Empresa', ['Datos de la empresa', 'Registro']),
    ]

    # --- Qué ve cada uno --------------------------------------------------

    def get_queryset(self, request):
        # El queryset base ya viene filtrado por el manager del proxy (por
        # llamar / clientes activos); aquí se añade la última llamada y, para
        # los vendedores, solo lo que tienen asignado.
        qs = super().get_queryset(request).con_ultima_llamada()
        if not request.user.is_superuser:
            qs = qs.filter(asignado_a=request.user)
        return qs

    def get_list_filter(self, request):
        # Al vendedor no le sirve (ni debe ver) el filtro con los demás vendedores.
        if request.user.is_superuser:
            return self.list_filter
        return [f for f in self.list_filter if f != 'asignado_a']

    def get_list_display(self, request):
        # La columna "Vendedor" sobra para el vendedor: todas son suyas.
        if request.user.is_superuser:
            return self.list_display
        return [c for c in self.list_display if c != 'col_vendedor']

    def changelist_view(self, request, extra_context=None):
        # Datos para la frase de arriba de la lista. get_queryset ya trae solo
        # lo que este usuario puede ver (todas o las suyas).
        qs = self.get_queryset(request)
        extra_context = {
            **(extra_context or {}),
            # Título como en el diseño ("Empresas") en vez del de
            # Django ("Escoja empresa a modificar").
            'title': self.opts.verbose_name_plural.capitalize(),
            'resumen_total': qs.count(),
            'resumen_hoy': contar_para_hoy(qs),
        }
        return super().changelist_view(request, extra_context)

    def change_view(self, request, object_id, form_url='', extra_context=None):
        # Datos del resumen de arriba del formulario. get_object respeta
        # get_queryset: un vendedor no obtiene empresas ajenas.
        obj = self.get_object(request, object_id)
        if obj is not None:
            tipo, texto = formato.proxima_llamada(obj.proxima_llamada)
            extra_context = {
                **(extra_context or {}),
                'resumen': {
                    'empresa': obj.empresa,
                    'detalle': ' · '.join(filter(None, [obj.nombre_contacto, obj.rubro, obj.ciudad])),
                    'etapa': obj.etapa,
                    'color_etapa': formato.color_etapa(obj.etapa),
                    'vendedor': formato.nombre_corto(obj.asignado_a),
                    'proxima_tipo': tipo,
                    'proxima_texto': texto,
                    'telefono': telefono_legible(obj.telefono),
                    'tel': obj.telefono,
                    'instagram': obj.instagram,
                    'url_instagram': obj.url_instagram,
                    # Pestaña nueva: el CRM queda abierto detrás. noopener:
                    # la página de Instagram no puede controlar esta pestaña.
                    'attrs_externo': {'target': '_blank', 'rel': 'noopener noreferrer'},
                },
            }
        return super().change_view(request, object_id, form_url, extra_context)

    def render_change_form(self, request, context, add=False, change=False, form_url='', obj=None):
        # Datos de la barra de pestañas. Si al guardar hay errores, se abre la
        # primera pestaña que los tenga: si no, el error quedaría escondido en
        # una pestaña cerrada y parecería que "no guarda".
        form = context['adminform'].form
        bloques = dict(self.get_fieldsets(request, obj))
        llamadas = sum(
            1 for f in context.get('inline_admin_formsets', [])
            for formulario in f.formset.forms if formulario.errors
        ) + sum(len(f.formset.non_form_errors()) for f in context.get('inline_admin_formsets', []))
        pestanas = []
        for clave, titulo, nombres in self.PESTANAS:
            campos = [c for n in nombres for c in bloques.get(n, {}).get('fields', [])]
            errores = llamadas if clave == 'llamadas' else sum(1 for c in campos if c in form.errors)
            cantidad = obj.interacciones.count() if clave == 'llamadas' and obj else None
            pestanas.append({'clave': clave, 'titulo': titulo, 'bloques': nombres, 'errores': errores, 'cantidad': cantidad})
        context['pestanas'] = pestanas
        context['pestana_con_error'] = next((p['clave'] for p in pestanas if p['errores']), '')
        return super().render_change_form(request, context, add, change, form_url, obj)

    # --- Columnas de la lista ----------------------------------------------
    # @display de unfold: header=True pinta dos líneas (título y subtítulo, y
    # opcionalmente iniciales en un círculo); label=... pinta una etiqueta de color.

    @display(description='Empresa', ordering='empresa', header=True)
    def col_empresa(self, obj):
        return [obj.empresa, ' · '.join(filter(None, [obj.rubro, obj.ciudad]))]

    @display(description='Teléfono', ordering='telefono')
    def col_telefono(self, obj):
        return telefono_legible(obj.telefono) or '—'

    # La clave (primer valor) elige el color; el segundo es el texto.
    @display(description='Etapa', ordering='etapa__orden', label={
        'default': 'default', 'info': 'info', 'warning': 'warning',
        'success': 'success', 'primary': 'primary', 'danger': 'danger',
    })
    def col_etapa(self, obj):
        return formato.color_etapa(obj.etapa), str(obj.etapa or 'Sin etapa')

    @display(description='Vendedor', ordering='asignado_a__first_name', header=True)
    def col_vendedor(self, obj):
        usuario = obj.asignado_a
        if usuario is None:
            return ['Sin asignar', '']
        return [
            formato.nombre_corto(usuario), '',
            formato.iniciales(usuario.first_name, usuario.last_name, usuario.username),
        ]

    @display(description='Próxima llamada', ordering='proxima_llamada', label={
        'vencida': 'danger', 'hoy': 'info', 'futura': 'default',
    })
    def col_proxima(self, obj):
        tipo, texto = formato.proxima_llamada(obj.proxima_llamada)
        return (tipo, texto) if tipo else texto

    @display(description='Última llamada', ordering='ultima_llamada', header=True)
    def col_ultima(self, obj):
        if obj.ultima_llamada is None:
            return ['—', 'Sin llamadas']
        resultado = Interaccion.Resultado(obj.ultimo_resultado).label if obj.ultimo_resultado else ''
        return [formato.dia_mes(timezone.localtime(obj.ultima_llamada)), resultado]

    @display(description='')
    def col_acciones(self, obj):
        # Botón de la fila: registrar llamada, que abre la empresa directamente
        # en la pestaña Llamadas. Sin WhatsApp: el CRM es para llamar.
        cambiar = reverse(f'admin:{self.opts.app_label}_{self.opts.model_name}_change', args=[obj.pk])
        return format_html(
            '<span class="hd-acciones"><a class="hd-boton-icono" href="{}#llamadas" title="Registrar llamada">'
            '<span class="material-symbols-outlined">edit_note</span></a></span>',
            cambiar,
        )

    def get_search_results(self, request, queryset, search_term):
        # Los teléfonos se guardan como +57..., así que si alguien busca
        # "300 123 4567" también se busca su versión normalizada.
        # Se parte del queryset recibido, que ya trae aplicados los filtros de la lista.
        filtrado = queryset
        queryset, hay_duplicados = super().get_search_results(request, queryset, search_term)
        try:
            telefono = normalizar_telefono(search_term)
        except TelefonoInvalido:
            telefono = ''
        if telefono:
            queryset |= filtrado.filter(telefono=telefono)
        return queryset, hay_duplicados

    # --- Qué puede hacer cada uno ------------------------------------------

    def get_readonly_fields(self, request, obj=None):
        if request.user.is_superuser:
            return self.readonly_fields
        # Vendedor: todo es de solo lectura excepto etapa y próxima llamada.
        todos = flatten_fieldsets(self.fieldsets)
        return [campo for campo in todos if campo not in CAMPOS_EDITABLES_VENDEDOR]

    def has_add_permission(self, request):
        return request.user.is_superuser

    def has_delete_permission(self, request, obj=None):
        return request.user.is_superuser

    def get_actions(self, request):
        # Sin acciones, el admin tampoco muestra las casillas de selección.
        if not request.user.is_superuser:
            return {}
        acciones = super().get_actions(request)
        # Una acción por vendedor activo. Se generan cada vez que se abre la
        # lista, así que un vendedor nuevo aparece sin tocar el código.
        for vendedor in vendedores_activos():
            nombre = f'asignar_a_{vendedor.pk}'
            descripcion = f'Asignar a {vendedor.get_full_name() or vendedor.username}'
            acciones[nombre] = (self._accion_asignar(vendedor), nombre, descripcion)
        acciones['quitar_asignacion'] = (
            self._accion_asignar(None), 'quitar_asignacion', 'Quitar asignación',
        )
        # Una acción por etapa: "Cambiar etapa a Contactado", etc.
        for etapa in Etapa.objects.order_by('orden', 'nombre'):
            nombre = f'etapa_{etapa.pk}'
            acciones[nombre] = (self._accion_cambiar_etapa(etapa), nombre, f'Cambiar etapa a {etapa}')
        return acciones

    @staticmethod
    def _accion_cambiar_etapa(etapa):
        def accion(modeladmin, request, queryset):
            # Igual que al asignar: se actualiza por pk por la anotación Max().
            pks = list(queryset.values_list('pk', flat=True))
            total = Contacto.objects.filter(pk__in=pks).update(etapa=etapa)
            modeladmin.message_user(request, f'{total} empresas pasaron a {etapa}.', messages.SUCCESS)
        return accion

    @staticmethod
    def _accion_asignar(vendedor):
        # Devuelve una función distinta por vendedor (una "clausura"): cada una
        # recuerda a qué vendedor asigna.
        def accion(modeladmin, request, queryset):
            # Se actualiza por pk porque el queryset de la lista lleva la
            # anotación Max(), y update() no acepta consultas agrupadas.
            pks = list(queryset.values_list('pk', flat=True))
            total = Contacto.objects.filter(pk__in=pks).update(asignado_a=vendedor)
            destino = (vendedor.get_full_name() or vendedor.username) if vendedor else 'nadie'
            modeladmin.message_user(request, f'{total} empresas asignadas a {destino}.', messages.SUCCESS)
        return accion

    def save_formset(self, request, form, formset, change):
        # commit=False devuelve los objetos sin guardarlos, para poder completar
        # "usuario" antes. Solo en las llamadas nuevas: las antiguas conservan
        # a quien las registró.
        for llamada in formset.save(commit=False):
            if llamada._state.adding:
                llamada.usuario = request.user
            llamada.save()
        for llamada in formset.deleted_objects:
            llamada.delete()
        formset.save_m2m()

    def response_change(self, request, obj):
        # Si al cambiar la etapa la empresa ya no pertenece a esta lista (p. ej.
        # pasó a "Cliente activo"), se lleva al usuario a la lista donde quedó.
        if self.get_queryset(request).filter(pk=obj.pk).exists():
            return super().response_change(request, obj)
        for modelo in (ClienteActivo, EmpresaPorLlamar, Contacto):
            opts = modelo._meta
            if (modelo.objects.filter(pk=obj.pk).exists()
                    and request.user.has_perm(f'{opts.app_label}.view_{opts.model_name}')):
                self.message_user(
                    request, f'«{obj}» se guardó y ahora está en {opts.verbose_name_plural}.', messages.SUCCESS,
                )
                return redirect(f'admin:{opts.app_label}_{opts.model_name}_changelist')
        self.message_user(request, f'«{obj}» se guardó y salió de tus listas (etapa {obj.etapa}).', messages.SUCCESS)
        return redirect(f'admin:{self.opts.app_label}_{self.opts.model_name}_changelist')


@admin.register(EmpresaPorLlamar)
class EmpresaPorLlamarAdmin(ContactoAdminBase):
    # Botones de arriba de la lista (los "actions_list" de unfold). unfold crea
    # la URL sola: <lista>/importar/ con el nombre crm_empresaporllamar_importar.
    actions_list = ['importar']

    def has_importar_permission(self, request):
        # unfold busca has_<permiso>_permission: si devuelve False, oculta el
        # botón y responde 403 aunque se escriba la URL a mano.
        return request.user.is_superuser

    @action(description='Importar CSV', icon='upload', url_path='importar', permissions=['importar'])
    def importar(self, request):
        form = ImportarCSVForm(request.POST or None, request.FILES or None)
        if request.method == 'POST' and form.is_valid():
            try:
                resultado = importar_contactos_csv(form.cleaned_data['archivo'], form.cleaned_data['asignar_a'])
            except ErrorImportacion as error:
                form.add_error('archivo', str(error))
            else:
                self.message_user(request, f'Se importaron {len(resultado.importadas)} empresas.', messages.SUCCESS)
                if resultado.duplicadas:
                    self.message_user(
                        request, f'{len(resultado.duplicadas)} duplicadas (no se importaron): {_resumir(resultado.duplicadas)}',
                        messages.WARNING,
                    )
                if resultado.errores:
                    self.message_user(
                        request, f'{len(resultado.errores)} filas con error: {_resumir(resultado.errores)}',
                        messages.ERROR,
                    )
                return redirect('admin:crm_empresaporllamar_changelist')

        contexto = {
            # each_context añade lo que necesita la plantilla base del admin
            # (menú, nombre del sitio, usuario...).
            **self.admin_site.each_context(request),
            'opts': self.opts,
            'form': form,
            'title': 'Importar empresas desde CSV',
        }
        return TemplateResponse(request, 'admin/crm/importar_csv.html', contexto)


@admin.register(ClienteActivo)
class ClienteActivoAdmin(ContactoAdminBase):
    pass


@admin.register(Contacto)
class ContactoAdmin(ContactoAdminBase):
    """Todos los contactos (incluidos los perdidos). Solo para el superusuario."""

    def has_view_permission(self, request, obj=None):
        return request.user.is_superuser

    def has_change_permission(self, request, obj=None):
        return request.user.is_superuser

    def has_module_permission(self, request):
        return request.user.is_superuser
