from django.shortcuts import render

from . import contenido


def home(request):
    return render(request, 'landing/home.html', {
        'metricas': contenido.METRICAS,
        'nosotros': contenido.NOSOTROS,
        'clientes': contenido.CLIENTES,
        'testimonio': contenido.TESTIMONIO,
        'motivos_consulta': contenido.MOTIVOS_CONSULTA,
        'origenes': contenido.ORIGENES,
    })
