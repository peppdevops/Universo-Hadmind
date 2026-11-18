"""docker compose exec web python manage.py crear_grupo_vendedor

Crea (o actualiza) el grupo "Vendedor" con sus permisos. Se puede ejecutar
las veces que quieras: no duplica nada. Ejecútalo después de migrate, porque
Django crea los permisos de los modelos al terminar las migraciones.
"""

from django.apps import apps
from django.contrib.auth.models import Group, Permission
from django.contrib.contenttypes.models import ContentType
from django.core.management.base import BaseCommand, CommandError

from apps.crm.models import GRUPO_VENDEDOR

# modelo -> acciones permitidas. Se dan sobre los PROXIES (las dos listas) y no
# sobre Contacto: así el vendedor no ve la lista "Contactos" con todo.
PERMISOS = {
    'empresaporllamar': ['view', 'change'],
    'clienteactivo': ['view', 'change'],
    'interaccion': ['view', 'add'],
    'etapa': ['view'],  # para poder elegir la etapa en el desplegable
}


class Command(BaseCommand):
    help = 'Crea o actualiza el grupo "Vendedor" con los permisos del CRM.'

    def handle(self, *args, **options):
        permisos = []
        for nombre_modelo, acciones in PERMISOS.items():
            modelo = apps.get_model('crm', nombre_modelo)
            # for_concrete_model=False: los permisos de un proxy están ligados al
            # proxy, no a Contacto. Sin esto se tomarían los de Contacto.
            tipo = ContentType.objects.get_for_model(modelo, for_concrete_model=False)
            for accion in acciones:
                codigo = f'{accion}_{nombre_modelo}'
                try:
                    permisos.append(Permission.objects.get(content_type=tipo, codename=codigo))
                except Permission.DoesNotExist:
                    raise CommandError(f'No existe el permiso {codigo}. Ejecuta primero "migrate".')

        grupo, creado = Group.objects.get_or_create(name=GRUPO_VENDEDOR)
        # set() reemplaza los permisos del grupo por exactamente estos.
        grupo.permissions.set(permisos)

        estado = 'creado' if creado else 'actualizado'
        self.stdout.write(self.style.SUCCESS(f'Grupo "{GRUPO_VENDEDOR}" {estado} con {len(permisos)} permisos.'))
        self.stdout.write('Para hacer vendedor a un usuario: márcalo como "es staff" y añádelo a este grupo en el admin.')
