from django.contrib import messages
from django.core import signing
from django.core.paginator import Paginator
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.cache import never_cache

from . import services
from .forms import CambiarImagenForm
from .models import Articulo

ACCIONES = {
    'publicar': (services.publicar, 'Artículo publicado: ya se ve en la Bitácora.'),
    'descartar': (services.descartar, 'Artículo descartado: no se publicará.'),
    'borrador': (services.volver_a_borrador, 'El artículo volvió a borrador: ya no se ve en la web.'),
}


@never_cache
def revisar(request, token):
    """Página que se abre desde el correo de aprobación.

    No pide iniciar sesión: el enlace firmado es la llave (vence en 7 días).
    Ver el enlace NO cambia nada; solo los botones (POST). Así, si Gmail o un
    antivirus "visita" el enlace para revisarlo, no se publica nada solo.
    """
    try:
        articulo = services.articulo_de_token(token)
    except signing.SignatureExpired:
        return render(request, 'blog/revision_invalida.html', {'vencido': True}, status=410)
    except (signing.BadSignature, Articulo.DoesNotExist):
        return render(request, 'blog/revision_invalida.html', {'vencido': False}, status=404)

    form_imagen = CambiarImagenForm()
    if request.method == 'POST':
        accion = request.POST.get('accion')
        if accion in ACCIONES:
            funcion, mensaje = ACCIONES[accion]
            funcion(articulo)
            messages.success(request, mensaje)
            return redirect(request.path)
        if accion == 'imagen':
            form_imagen = CambiarImagenForm(request.POST, request.FILES)
            if form_imagen.is_valid():
                try:
                    services.poner_imagen(articulo, form_imagen.cleaned_data['imagen'])
                except services.ImagenInvalida as error:
                    form_imagen.add_error('imagen', str(error))
                else:
                    articulo.save()
                    messages.success(request, 'Imagen cambiada.')
                    return redirect(request.path)

    return render(request, 'blog/revisar.html', {'articulo': articulo, 'form_imagen': form_imagen})


# --- Páginas públicas -------------------------------------------------------

def lista(request):
    """/bitacora/: todos los artículos publicados, del más nuevo al más viejo."""
    pagina = Paginator(Articulo.objects.publicados(), services.ARTICULOS_POR_PAGINA).get_page(
        request.GET.get('pagina'))
    return render(request, 'blog/lista.html', {'pagina': pagina, 'articulos': pagina.object_list})


def detalle(request, slug):
    """Página de un artículo. Borradores y descartados dan 404: solo se ven en
    la página de revisión del correo o en el admin."""
    articulo = get_object_or_404(Articulo.objects.publicados(), slug=slug)
    return render(request, 'blog/detalle.html', {
        'articulo': articulo,
        'relacionados': services.relacionados(articulo),
        # WhatsApp, LinkedIn y Google necesitan direcciones completas (https://...).
        'url_absoluta': request.build_absolute_uri(),
        'imagen_absoluta': request.build_absolute_uri(articulo.imagen.url) if articulo.imagen else '',
    })
