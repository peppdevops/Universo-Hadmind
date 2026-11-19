"""Funciones que unfold llama para decidir qué ve cada usuario en el menú lateral.

settings.UNFOLD las referencia como texto ('core.admin_permisos.es_superusuario')
porque settings se carga antes que los modelos y no puede importarlos.

Ojo: esconder un enlace del menú NO protege la página. La protección real la
dan los permisos de cada admin (has_view_permission, etc.); esto solo evita
mostrarle al vendedor enlaces que le darían error 403.
"""


def es_superusuario(request):
    return request.user.is_superuser


# Las de Ventas usan el permiso "view" de cada modelo: lo tienen el superusuario
# y el grupo Vendedor (ver el comando crear_grupo_vendedor).

def ver_empresas_por_llamar(request):
    return request.user.has_perm('crm.view_empresaporllamar')


def ver_clientes_activos(request):
    return request.user.has_perm('crm.view_clienteactivo')
