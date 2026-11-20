from django.contrib import admin, messages
from django.core.files.storage import default_storage
from django.utils.html import format_html
from unfold.admin import ModelAdmin
from unfold.decorators import action, display

from . import services
from .forms import ArticuloAdminForm
from .models import Articulo

@admin.register(Articulo)
class ArticuloAdmin(ModelAdmin):
    form = ArticuloAdminForm
    list_display = ['col_articulo', 'col_estado', 'origen', 'publicado_en', 'creado']
    list_filter = ['estado', 'categoria', 'origen']
    search_fields = ['titulo', 'resumen', 'fuente_nombre']
    # El slug se escribe solo mientras se teclea el título (al crear a mano).
    prepopulated_fields = {'slug': ['titulo']}
    readonly_fields = ['origen', 'publicado_en', 'creado', 'actualizado', 'enlace_revision']
    actions = ['accion_publicar', 'accion_borrador', 'accion_descartar']
    list_per_page = 25

    fieldsets = [
        ('Artículo', {'fields': ['titulo', 'slug', 'categoria', 'resumen', 'contenido'], 'classes': ['tab']}),
        ('Imagen', {'fields': ['imagen', 'imagen_alt', 'prompt_imagen'], 'classes': ['tab']}),
        ('Fuente y estado', {
            'fields': ['fuente_nombre', 'fuente_url', 'estado', 'origen', 'publicado_en',
                       'enlace_revision', 'creado', 'actualizado'],
            'classes': ['tab'],
        }),
    ]

    @display(description='Artículo', ordering='titulo', header=True)
    def col_articulo(self, obj):
        return [obj.titulo, obj.get_categoria_display()]

    @display(description='Estado', ordering='estado', label={
        Articulo.Estado.BORRADOR.label: 'warning',
        Articulo.Estado.PUBLICADO.label: 'success',
        Articulo.Estado.DESCARTADO.label: 'danger',
    })
    def col_estado(self, obj):
        return obj.get_estado_display()

    @display(description='Página de revisión')
    def enlace_revision(self, obj):
        # La misma página que llega en el correo (útil si el correo se perdió).
        if not obj.pk:
            return '—'
        return format_html('<a href="{}" target="_blank" rel="noopener">Abrir</a>', services.url_revision(obj))

    def save_model(self, request, obj, form, change):
        # Si se cambió o quitó la imagen, se borra el archivo anterior del disco.
        anterior = ''
        if change and 'imagen' in form.changed_data:
            anterior = Articulo.objects.filter(pk=obj.pk).values_list('imagen', flat=True).first() or ''
        super().save_model(request, obj, form, change)
        if anterior and anterior != obj.imagen.name:
            default_storage.delete(anterior)

    # --- Acciones de la lista -------------------------------------------
    # Se guardan uno por uno (no con update()) para que save() fije la fecha
    # de publicación y regenere el HTML.

    def _cambiar(self, request, queryset, funcion, texto):
        for articulo in queryset:
            funcion(articulo)
        self.message_user(request, f'{queryset.count()} artículos {texto}.', messages.SUCCESS)

    @action(description='Publicar')
    def accion_publicar(self, request, queryset):
        self._cambiar(request, queryset, services.publicar, 'publicados')

    @action(description='Volver a borrador')
    def accion_borrador(self, request, queryset):
        self._cambiar(request, queryset, services.volver_a_borrador, 'pasaron a borrador')

    @action(description='Descartar')
    def accion_descartar(self, request, queryset):
        self._cambiar(request, queryset, services.descartar, 'descartados')
