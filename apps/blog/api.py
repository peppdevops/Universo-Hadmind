"""API que usa n8n para crear artículos de la Bitácora.

POST /api/bitacora/
Cabecera: Authorization: Bearer <N8N_API_TOKEN>
Cuerpo: multipart/form-data (con la imagen en el campo "imagen") o JSON (sin imagen).
Campos: titulo, categoria, resumen, contenido (Markdown), imagen_alt,
        prompt_imagen, fuente_nombre, fuente_url.

Respuestas:
201 creado como BORRADOR -> {"id", "titulo", "url_revision", "correo_asunto",
    "correo_html", ...}. n8n envía correo_asunto/correo_html tal cual.
400 datos inválidos -> {"errores": {"campo": ["mensaje"]}}
401 clave mala o ausente
409 esa fuente ya existe -> {"error", "id"} (n8n puede ignorarlo)

GET /api/bitacora/fuentes/ (misma cabecera)
200 -> {"fuentes": [url, ...]}: fuentes ya usadas, para que n8n no las repita.
"""

import hmac
import json

from django.conf import settings
from django.db import IntegrityError
from django.http import JsonResponse
from django.urls import reverse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_GET, require_POST

from .forms import ArticuloN8NForm
from .models import Articulo
from .services import (
    correo_revision, fuentes_usadas, normalizar_categoria, slug_unico, url_absoluta, url_revision,
)


def clave_valida(request):
    esperada = settings.N8N_API_TOKEN
    recibida = request.headers.get('Authorization', '').removeprefix('Bearer ').strip()
    # Sin clave configurada no entra nadie. compare_digest tarda lo mismo
    # acierte o no: no deja adivinar la clave midiendo tiempos.
    return bool(esperada) and hmac.compare_digest(recibida.encode(), esperada.encode())


def respuesta_duplicado(articulo):
    return JsonResponse({'error': 'Ya existe un artículo con esa fuente.', 'id': articulo.pk}, status=409)


# csrf_exempt: n8n no es un navegador y no tiene cookie CSRF. La protección
# aquí es la clave secreta de la cabecera.
@csrf_exempt
@require_POST
def crear_articulo(request):
    if not clave_valida(request):
        return JsonResponse({'error': 'Clave inválida.'}, status=401)

    if request.content_type == 'application/json':
        try:
            datos = json.loads(request.body)
        except ValueError:
            return JsonResponse({'error': 'El JSON no es válido.'}, status=400)
        if not isinstance(datos, dict):
            return JsonResponse({'error': 'Se esperaba un objeto JSON.'}, status=400)
        archivos = None
    else:
        datos, archivos = request.POST.copy(), request.FILES
    datos['categoria'] = normalizar_categoria(datos.get('categoria'))

    fuente = str(datos.get('fuente_url') or '').strip()
    existente = Articulo.objects.filter(fuente_url=fuente).first() if fuente else None
    if existente:
        return respuesta_duplicado(existente)

    form = ArticuloN8NForm(datos, archivos)
    if not form.is_valid():
        errores = {campo: [e['message'] for e in lista] for campo, lista in form.errors.get_json_data().items()}
        return JsonResponse({'errores': errores}, status=400)

    articulo = form.save(commit=False)
    articulo.origen = Articulo.Origen.N8N
    articulo.estado = Articulo.Estado.BORRADOR
    articulo.slug = slug_unico(articulo.titulo)
    try:
        articulo.save()
    except IntegrityError:
        # Dos envíos de la misma noticia al mismo tiempo: el segundo choca aquí.
        return respuesta_duplicado(Articulo.objects.get(fuente_url=fuente))

    asunto, html = correo_revision(request, articulo)
    return JsonResponse({
        'id': articulo.pk,
        'titulo': articulo.titulo,
        'estado': articulo.estado,
        'url_revision': url_absoluta(request, url_revision(articulo)),
        'url_admin': url_absoluta(request, reverse('admin:blog_articulo_change', args=[articulo.pk])),
        'imagen': url_absoluta(request, articulo.imagen.url) if articulo.imagen else '',
        'correo_asunto': asunto,
        'correo_html': html,
    }, status=201)


@require_GET
def fuentes(request):
    if not clave_valida(request):
        return JsonResponse({'error': 'Clave inválida.'}, status=401)
    return JsonResponse({'fuentes': fuentes_usadas()})
