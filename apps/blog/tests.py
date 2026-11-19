"""Tests de la Bitácora: API de n8n, página de revisión del correo y admin.

Las imágenes se guardan en una carpeta temporal que se borra al terminar.
"""

import json
import shutil
import tempfile
from datetime import timedelta
from io import BytesIO
from unittest import mock

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone
from PIL import Image

from .models import Articulo
from .services import markdown_a_html, tiempo_relativo, url_revision

User = get_user_model()
CLAVE = 'clave-de-prueba'
MEDIA_TEMPORAL = tempfile.mkdtemp()


def imagen_de_prueba(ancho=2400, alto=1500, formato='PNG', nombre='foto.png'):
    salida = BytesIO()
    Image.new('RGB', (ancho, alto), '#3E83D6').save(salida, formato)
    return SimpleUploadedFile(nombre, salida.getvalue(), content_type=f'image/{formato.lower()}')


def datos_validos(**cambios):
    datos = {
        'titulo': 'Las pymes ya automatizan su atención al cliente',
        'categoria': 'automatizacion',
        'resumen': 'Cada vez más pymes usan asistentes para responder a sus clientes.',
        'contenido': '## Qué está pasando\n\nTexto del artículo.\n\n- Punto uno\n- Punto dos',
        'fuente_nombre': 'Noticias Tech',
        'fuente_url': 'https://ejemplo.com/noticia-1',
        'prompt_imagen': 'Ilustración azul de un asistente atendiendo una tienda',
    }
    datos.update(cambios)
    return datos


def crear_articulo(**cambios):
    datos = datos_validos(**cambios)
    datos.pop('prompt_imagen')
    datos.setdefault('slug', datos['titulo'].lower().replace(' ', '-')[:50])
    return Articulo.objects.create(**datos)


class ConCarpetaTemporal(TestCase):
    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(MEDIA_TEMPORAL, ignore_errors=True)


@override_settings(N8N_API_TOKEN=CLAVE, MEDIA_ROOT=MEDIA_TEMPORAL)
class ApiN8NTests(ConCarpetaTemporal):
    url = reverse('blog:api_crear')

    def enviar(self, datos, clave=CLAVE, **extra):
        cabeceras = {'HTTP_AUTHORIZATION': f'Bearer {clave}'} if clave else {}
        return self.client.post(self.url, datos, **cabeceras, **extra)

    def test_sin_clave_o_con_clave_mala_401(self):
        self.assertEqual(self.enviar(datos_validos(), clave=None).status_code, 401)
        self.assertEqual(self.enviar(datos_validos(), clave='otra').status_code, 401)
        self.assertFalse(Articulo.objects.exists())

    @override_settings(N8N_API_TOKEN='')
    def test_sin_clave_configurada_nadie_entra(self):
        # Si se olvida poner la clave en el .env, la API no queda abierta.
        self.assertEqual(self.enviar(datos_validos(), clave='').status_code, 401)

    def test_solo_acepta_post(self):
        self.assertEqual(self.client.get(self.url).status_code, 405)

    def test_crea_borrador_con_imagen_en_webp(self):
        r = self.enviar({**datos_validos(), 'imagen': imagen_de_prueba()})
        self.assertEqual(r.status_code, 201, r.content)
        articulo = Articulo.objects.get()
        self.assertEqual(articulo.estado, Articulo.Estado.BORRADOR)
        self.assertEqual(articulo.origen, Articulo.Origen.N8N)
        self.assertEqual(articulo.slug, 'las-pymes-ya-automatizan-su-atencion-al-cliente')
        # La imagen se redujo y quedó en WebP.
        self.assertTrue(articulo.imagen.name.endswith('.webp'))
        with Image.open(articulo.imagen.path) as guardada:
            self.assertEqual(guardada.format, 'WEBP')
            self.assertLessEqual(guardada.width, 1600)
        # n8n recibe el enlace para el correo de aprobación.
        self.assertIn('/bitacora/revisar/', r.json()['url_revision'])
        self.assertTrue(r.json()['url_revision'].startswith('http'))

    def test_json_sin_imagen_y_categoria_con_nombre(self):
        # La IA a veces manda el nombre ("Inteligencia Artificial") y no la clave.
        r = self.enviar(json.dumps(datos_validos(categoria='Inteligencia Artificial')),
                        content_type='application/json')
        self.assertEqual(r.status_code, 201, r.content)
        self.assertEqual(Articulo.objects.get().categoria, 'inteligencia_artificial')

    def test_misma_fuente_no_se_repite(self):
        self.assertEqual(self.enviar(datos_validos()).status_code, 201)
        r = self.enviar(datos_validos(titulo='Otro título'))
        self.assertEqual(r.status_code, 409)
        self.assertEqual(Articulo.objects.count(), 1)

    def test_titulo_repetido_tiene_otro_slug(self):
        self.enviar(datos_validos())
        self.enviar(datos_validos(fuente_url='https://ejemplo.com/noticia-2'))
        slugs = sorted(Articulo.objects.values_list('slug', flat=True))
        self.assertEqual(slugs[1], slugs[0] + '-2')

    def test_datos_invalidos_400_con_errores(self):
        r = self.enviar(datos_validos(titulo='', categoria='cocina'))
        self.assertEqual(r.status_code, 400)
        self.assertIn('titulo', r.json()['errores'])
        self.assertIn('categoria', r.json()['errores'])

    def test_archivo_que_no_es_imagen_400(self):
        falso = SimpleUploadedFile('virus.png', b'esto no es una imagen', content_type='image/png')
        r = self.enviar({**datos_validos(), 'imagen': falso})
        self.assertEqual(r.status_code, 400)
        self.assertIn('imagen', r.json()['errores'])

    def test_json_mal_formado_400(self):
        r = self.enviar('{no es json', content_type='application/json')
        self.assertEqual(r.status_code, 400)


class ContenidoTests(TestCase):
    def test_markdown_se_convierte_y_se_limpia(self):
        html = markdown_a_html(
            '## Título\n\n**negrita** <script>alert(1)</script>\n\n'
            '[malo](javascript:alert(1)) [bueno](https://ejemplo.com)'
        )
        self.assertIn('<h2>Título</h2>', html)
        self.assertIn('<strong>negrita</strong>', html)
        self.assertNotIn('<script', html)
        self.assertNotIn('javascript:', html)
        self.assertIn('rel="noopener noreferrer nofollow"', html)

    def test_publicados_solo_trae_los_publicados(self):
        crear_articulo(estado=Articulo.Estado.PUBLICADO)
        crear_articulo(fuente_url='https://ejemplo.com/2', slug='b')
        crear_articulo(fuente_url='https://ejemplo.com/3', slug='c', estado=Articulo.Estado.DESCARTADO)
        self.assertEqual(Articulo.objects.publicados().count(), 1)

    def test_tiempo_relativo(self):
        ahora = timezone.now()
        self.assertEqual(tiempo_relativo(ahora - timedelta(hours=2), ahora), 'Hace 2 horas')
        self.assertEqual(tiempo_relativo(ahora - timedelta(days=1), ahora), 'Hace 1 día')
        self.assertEqual(tiempo_relativo(ahora - timedelta(days=8), ahora), 'Hace 1 semana')


@override_settings(MEDIA_ROOT=MEDIA_TEMPORAL)
class RevisionTests(ConCarpetaTemporal):
    def setUp(self):
        self.articulo = crear_articulo()
        self.url = url_revision(self.articulo)

    def test_abrir_el_enlace_no_publica(self):
        # Gmail o un antivirus pueden "visitar" el enlace: eso no cambia nada.
        r = self.client.get(self.url)
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, self.articulo.titulo)
        self.assertContains(r, 'noindex')
        self.articulo.refresh_from_db()
        self.assertEqual(self.articulo.estado, Articulo.Estado.BORRADOR)

    def test_publicar_desde_el_correo(self):
        r = self.client.post(self.url, {'accion': 'publicar'}, follow=True)
        self.assertContains(r, 'Artículo publicado')
        self.articulo.refresh_from_db()
        self.assertEqual(self.articulo.estado, Articulo.Estado.PUBLICADO)
        self.assertIsNotNone(self.articulo.publicado_en)

    def test_descartar_desde_el_correo(self):
        self.client.post(self.url, {'accion': 'descartar'})
        self.articulo.refresh_from_db()
        self.assertEqual(self.articulo.estado, Articulo.Estado.DESCARTADO)

    def test_enlace_alterado_404(self):
        alterado = self.url.rstrip('/')[:-3] + 'abc/'
        self.assertEqual(self.client.get(alterado).status_code, 404)
        # Otro id con la firma de este artículo tampoco sirve.
        otro = crear_articulo(fuente_url='https://ejemplo.com/otro', slug='otro')
        falso = self.url.replace(f'/{self.articulo.pk}:', f'/{otro.pk}:')
        self.assertEqual(self.client.get(falso).status_code, 404)

    def test_enlace_vencido_410(self):
        with mock.patch('apps.blog.services.VIGENCIA_REVISION', -1):
            r = self.client.get(self.url)
        self.assertEqual(r.status_code, 410)
        self.assertContains(r, 'venció', status_code=410)

    def test_cambiar_imagen(self):
        r = self.client.post(self.url, {'accion': 'imagen', 'imagen': imagen_de_prueba(800, 500)})
        self.assertEqual(r.status_code, 302)
        self.articulo.refresh_from_db()
        self.assertTrue(self.articulo.imagen.name.endswith('.webp'))


class AdminBitacoraTests(TestCase):
    def test_superusuario_ve_la_bitacora_en_el_menu(self):
        self.client.force_login(User.objects.create_superuser('jefe', password='x'))
        r = self.client.get(reverse('admin:blog_articulo_changelist'))
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, 'Bitácora')

    def test_staff_sin_permisos_no_entra(self):
        self.client.force_login(User.objects.create_user('ana', password='x', is_staff=True))
        self.assertEqual(self.client.get(reverse('admin:blog_articulo_changelist')).status_code, 403)

    def test_accion_publicar_fija_la_fecha(self):
        self.client.force_login(User.objects.create_superuser('jefe', password='x'))
        articulo = crear_articulo()
        self.client.post(reverse('admin:blog_articulo_changelist'), {
            'action': 'accion_publicar', '_selected_action': [articulo.pk],
        })
        articulo.refresh_from_db()
        self.assertEqual(articulo.estado, Articulo.Estado.PUBLICADO)
        self.assertIsNotNone(articulo.publicado_en)


def publicado(dias_atras=0, **cambios):
    """Artículo publicado hace `dias_atras` días."""
    n = Articulo.objects.count() + 1
    cambios.setdefault('fuente_url', f'https://ejemplo.com/pub-{n}')
    cambios.setdefault('slug', f'articulo-{n}')
    cambios.setdefault('titulo', f'Artículo {n}')
    articulo = crear_articulo(estado=Articulo.Estado.PUBLICADO, **cambios)
    # publicado_en lo fija save(); se mueve a mano para ordenar por fecha
    Articulo.objects.filter(pk=articulo.pk).update(publicado_en=timezone.now() - timedelta(days=dias_atras))
    articulo.refresh_from_db()
    return articulo


class InicioBitacoraTests(TestCase):
    def test_sin_publicados_no_sale_la_seccion(self):
        crear_articulo()  # borrador
        r = self.client.get(reverse('landing:home'))
        self.assertNotContains(r, 'id="bitacora"')
        self.assertNotContains(r, 'bitacora.js')

    def test_muestra_la_mas_nueva_y_tres_anteriores(self):
        for dias in (5, 1, 9, 3, 20):
            publicado(dias, titulo=f'Hace {dias} días')
        crear_articulo(titulo='Borrador oculto', fuente_url='https://ejemplo.com/b', slug='b')
        r = self.client.get(reverse('landing:home'))
        self.assertContains(r, 'id="bitacora"')
        titulos = [a.titulo for a in r.context['articulos_bitacora']]
        self.assertEqual(titulos, ['Hace 1 días', 'Hace 3 días', 'Hace 5 días', 'Hace 9 días'])
        self.assertNotContains(r, 'Borrador oculto')

    def test_la_ventana_trae_el_texto_completo(self):
        publicado(contenido='## Detalle\n\nEl resto de la noticia.')
        r = self.client.get(reverse('landing:home'))
        self.assertContains(r, 'data-bitacora-contenido')
        self.assertContains(r, '<h2>Detalle</h2>', html=False)
        self.assertContains(r, 'Leer en su página')

    def test_menu_tiene_bitacora(self):
        r = self.client.get(reverse('landing:home'))
        self.assertContains(r, f'href="{reverse("blog:lista")}"')
        self.assertContains(r, 'Bitácora')


class PaginasPublicasTests(TestCase):
    def test_lista_vacia_responde(self):
        r = self.client.get(reverse('blog:lista'))
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, 'Pronto publicaremos')

    def test_lista_pagina_de_12_en_12(self):
        for dias in range(14):
            publicado(dias)
        r = self.client.get(reverse('blog:lista'))
        self.assertEqual(len(r.context['articulos']), 12)
        self.assertContains(r, '?pagina=2')
        r = self.client.get(reverse('blog:lista') + '?pagina=2')
        self.assertEqual(len(r.context['articulos']), 2)
        # Una página que no existe muestra la última, no un error
        self.assertEqual(self.client.get(reverse('blog:lista') + '?pagina=99').status_code, 200)

    def test_detalle_publicado(self):
        articulo = publicado()
        r = self.client.get(reverse('blog:detalle', args=[articulo.slug]))
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, articulo.titulo)
        self.assertContains(r, 'property="og:title"')
        self.assertContains(r, 'rel="canonical" href="http://testserver/bitacora/')

    def test_borrador_y_descartado_dan_404(self):
        borrador = crear_articulo(slug="borrador")
        descartado = crear_articulo(fuente_url='https://ejemplo.com/d', slug='d',
                                    estado=Articulo.Estado.DESCARTADO)
        for articulo in (borrador, descartado):
            self.assertEqual(self.client.get(reverse('blog:detalle', args=[articulo.slug])).status_code, 404)

    def test_relacionados_prefieren_la_misma_categoria(self):
        articulo = publicado(categoria='software')
        misma = publicado(5, categoria='software')
        otras = [publicado(dias, categoria='pymes') for dias in (1, 2, 3)]
        r = self.client.get(reverse('blog:detalle', args=[articulo.slug]))
        relacionados = r.context['relacionados']
        self.assertEqual(relacionados[0], misma)
        self.assertEqual(relacionados[1:], otras[:2])
        self.assertNotIn(articulo, relacionados)
