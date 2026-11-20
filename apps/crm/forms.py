from django import forms
from unfold.widgets import UnfoldAdminFileFieldWidget, UnfoldAdminSelectWidget

from .models import vendedores_activos

TAMANO_MAXIMO = 5 * 1024 * 1024  # 5 MB: de sobra para decenas de miles de filas


class VendedorChoiceField(forms.ModelChoiceField):
    # Muestra "Ana Pérez" en el desplegable en vez del nombre de usuario.
    def label_from_instance(self, usuario):
        return usuario.get_full_name() or usuario.username


class ImportarCSVForm(forms.Form):
    # Los widgets de unfold solo cambian la apariencia del campo (sus clases CSS).
    archivo = forms.FileField(
        label='Archivo CSV',
        widget=UnfoldAdminFileFieldWidget,
        help_text='Columnas: empresa, contacto, telefono, correo, ciudad, rubro. '
                  'Desde Excel: Guardar como → "CSV UTF-8" o "CSV (delimitado por comas)".',
    )
    asignar_a = VendedorChoiceField(
        queryset=None, required=False, label='Asignar todas a', empty_label='Sin asignar',
        widget=UnfoldAdminSelectWidget,
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # El queryset se pone aquí (y no arriba) para que lea los vendedores
        # cada vez que se abre el formulario, no una sola vez al arrancar Django.
        self.fields['asignar_a'].queryset = vendedores_activos()

    def clean_archivo(self):
        archivo = self.cleaned_data['archivo']
        if not archivo.name.lower().endswith('.csv'):
            raise forms.ValidationError('El archivo debe ser .csv')
        if archivo.size > TAMANO_MAXIMO:
            raise forms.ValidationError('El archivo pesa más de 5 MB.')
        return archivo
