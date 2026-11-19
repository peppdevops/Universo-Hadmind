from django import forms
from django.core.files.uploadedfile import UploadedFile
from django.utils.text import slugify

from .models import Articulo
from .services import ImagenInvalida, procesar_imagen


class ImagenWebPMixin:
    """Toda imagen nueva (venga de n8n o del admin) se reduce y pasa a WebP
    al validar el formulario; si no es una imagen válida, sale como error del
    campo, igual que cualquier otro error del formulario."""

    def clean_imagen(self):
        archivo = self.cleaned_data.get('imagen')
        # Solo se procesa un archivo recién subido (no la imagen que ya tenía).
        if not isinstance(archivo, UploadedFile):
            return archivo
        nombre = slugify(self.cleaned_data.get('titulo') or '') or 'imagen'
        try:
            return procesar_imagen(archivo, nombre)
        except ImagenInvalida as error:
            raise forms.ValidationError(str(error))


class ArticuloN8NForm(ImagenWebPMixin, forms.ModelForm):
    """Lo que puede enviar n8n. Estado, origen y slug los pone Django."""

    # FileField y no ImageField: la validación de imagen la hace procesar_imagen.
    imagen = forms.FileField(required=False)

    class Meta:
        model = Articulo
        fields = [
            'titulo', 'categoria', 'resumen', 'contenido',
            'imagen', 'imagen_alt', 'prompt_imagen', 'fuente_nombre', 'fuente_url',
        ]


class ArticuloAdminForm(ImagenWebPMixin, forms.ModelForm):
    class Meta:
        model = Articulo
        fields = '__all__'


class CambiarImagenForm(forms.Form):
    imagen = forms.FileField(label='Nueva imagen')
