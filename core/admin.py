"""Usuarios y grupos de Django con la apariencia de unfold.

Django registra User y Group con su admin propio (sin estilo unfold). Aquí se
quitan y se vuelven a registrar con las clases de unfold. Es solo apariencia:
el comportamiento es el UserAdmin estándar. La gestión de vendedores (fase 2)
se construirá sobre esto.
"""

from django.contrib import admin
from django.contrib.auth.admin import GroupAdmin as BaseGroupAdmin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.models import Group, User
from unfold.admin import ModelAdmin
from unfold.forms import AdminPasswordChangeForm, UserChangeForm, UserCreationForm

admin.site.unregister(User)
admin.site.unregister(Group)


@admin.register(User)
class UsuarioAdmin(BaseUserAdmin, ModelAdmin):
    # Formularios de unfold: los mismos campos que los de Django, con su estilo.
    form = UserChangeForm
    add_form = UserCreationForm
    change_password_form = AdminPasswordChangeForm

    # Los mismos bloques que el UserAdmin de Django, pero como pestañas
    # ('classes': ['tab'] es la forma de unfold de hacerlas). Aquí sí sirven
    # las pestañas de unfold tal cual: usuarios no tiene tablas (inlines)
    # que obliguen a un segundo nivel, como pasa en el detalle de empresa.
    # Solo afecta a editar; el formulario de "nuevo usuario" no cambia.
    fieldsets = (
        ('Cuenta', {'fields': ('username', 'password'), 'classes': ['tab']}),
        ('Datos personales', {'fields': ('first_name', 'last_name', 'email'), 'classes': ['tab']}),
        ('Permisos', {
            'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions'),
            'classes': ['tab'],
        }),
        ('Fechas', {'fields': ('last_login', 'date_joined'), 'classes': ['tab']}),
    )


@admin.register(Group)
class GrupoAdmin(BaseGroupAdmin, ModelAdmin):
    pass
