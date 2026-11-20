from django.shortcuts import render

from apps.blog.services import articulos_para_inicio

from . import contenido


def home(request):
    return render(request, 'landing/home.html', {
        'metricas': contenido.METRICAS,
        'nosotros': contenido.NOSOTROS,
        'clientes': contenido.CLIENTES,
        'testimonio': contenido.TESTIMONIO,
        'motivos_consulta': contenido.MOTIVOS_CONSULTA,
        'origenes': contenido.ORIGENES,
        # Vacío si no hay nada publicado: la sección no se muestra.
        'articulos_bitacora': articulos_para_inicio(),
    })
