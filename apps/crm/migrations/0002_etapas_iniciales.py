"""Migración de datos: crea las etapas iniciales del embudo de ventas.

Va en una migración (y no a mano en el admin) para que existan igual en tu PC,
en los tests y en el VPS, sin pasos manuales. Luego se pueden renombrar,
reordenar o añadir más desde el admin.
"""

from django.db import migrations

# (nombre, orden, es_cliente, es_final)
ETAPAS = [
    ('Por llamar', 1, False, False),
    ('Contactado', 2, False, False),
    ('Interesado', 3, False, False),
    ('Cotizado', 4, False, False),
    ('Cliente activo', 5, True, False),
    ('Perdido', 6, False, True),
]


def crear_etapas(apps, schema_editor):
    # apps.get_model da la versión del modelo de ESTA migración, no la actual
    # de models.py: así la migración sigue funcionando aunque el modelo cambie.
    Etapa = apps.get_model('crm', 'Etapa')
    for nombre, orden, es_cliente, es_final in ETAPAS:
        Etapa.objects.get_or_create(
            nombre=nombre,
            defaults={'orden': orden, 'es_cliente': es_cliente, 'es_final': es_final},
        )


def borrar_etapas(apps, schema_editor):
    # Para poder deshacer la migración (migrate crm 0001). Falla si alguna
    # etapa tiene contactos, por el PROTECT: así no se pierden datos.
    Etapa = apps.get_model('crm', 'Etapa')
    Etapa.objects.filter(nombre__in=[nombre for nombre, *_ in ETAPAS]).delete()


class Migration(migrations.Migration):

    dependencies = [
        ('crm', '0001_initial'),
    ]

    operations = [
        migrations.RunPython(crear_etapas, borrar_etapas),
    ]
