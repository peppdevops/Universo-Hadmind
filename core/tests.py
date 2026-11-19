from django.test import TestCase, override_settings
from django.urls import reverse


class SitioContextTests(TestCase):
    def test_sitio_disponible_en_plantillas(self):
        response = self.client.get(reverse('landing:home'))
        sitio = response.context['sitio']
        self.assertEqual(len(sitio['servicios']), 11)
        self.assertEqual(sitio['menu'][0], {'num': '01', 'etiqueta': 'Inicio', 'href': '/'})
        self.assertEqual(sitio['menu'][1]['href'], '/#nosotros')


# --- Dashboard (Inicio del admin) ---------------------------------------------

from datetime import timedelta
from io import StringIO

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.core.management import call_command
from django.utils import timezone
from django.utils.text import slugify

from apps.crm.models import GRUPO_VENDEDOR, Contacto, Etapa, Interaccion
from core.utils import pesos, telefono_legible, url_whatsapp

User = get_user_model()


class DashboardTests(TestCase):
    """Qué ve cada uno en el Inicio, con datos de verdad en la base de prueba."""

    @classmethod
    def setUpTestData(cls):
        call_command('crear_grupo_vendedor', stdout=StringIO())
        grupo = Group.objects.get(name=GRUPO_VENDEDOR)
        cls.admin = User.objects.create_superuser('jefe', password='x', first_name='Juan')
        cls.ana = User.objects.create_user('ana', password='x', is_staff=True, first_name='Ana', last_name='Ruiz')
        cls.luis = User.objects.create_user('luis', password='x', is_staff=True, first_name='Luis')
        cls.ana.groups.add(grupo)
        cls.luis.groups.add(grupo)

        ahora = timezone.localtime()
        ayer = ahora - timedelta(days=1)
        hoy_930 = ahora.replace(hour=9, minute=30, second=0, microsecond=0)
        manana = ahora + timedelta(days=1)
        perdido = Etapa.objects.get(es_final=True)

        cls.vencida = Contacto.objects.create(empresa='Vencida de Ana', telefono='3001111111', asignado_a=cls.ana, proxima_llamada=ayer)
        cls.de_hoy = Contacto.objects.create(empresa='Hoy de Ana', telefono='6041111111', asignado_a=cls.ana, proxima_llamada=hoy_930)
        Contacto.objects.create(empresa='Mañana de Ana', telefono='3002222222', asignado_a=cls.ana, proxima_llamada=manana)
        Contacto.objects.create(empresa='Hoy de Luis', telefono='3003333333', asignado_a=cls.luis, proxima_llamada=hoy_930)
        Contacto.objects.create(empresa='Perdida', telefono='3004444444', asignado_a=cls.ana, proxima_llamada=ayer, etapa=perdido)

        Interaccion.objects.create(contacto=cls.vencida, usuario=cls.ana, resultado='contesto')
        Interaccion.objects.create(contacto=cls.vencida, usuario=cls.ana, resultado='interesado')
        Interaccion.objects.create(contacto=cls.de_hoy, usuario=cls.ana, resultado='no_contesto')

    def inicio(self, usuario, **params):
        self.client.force_login(usuario)
        respuesta = self.client.get(reverse('admin:index'), params)
        self.assertEqual(respuesta.status_code, 200)
        return respuesta

    def test_vendedor_ve_solo_su_agenda_y_nada_de_finanzas(self):
        r = self.inicio(self.ana)
        self.assertContains(r, 'Vencida de Ana')
        self.assertContains(r, 'Hoy de Ana')
        self.assertNotContains(r, 'Mañana de Ana')   # no es de hoy
        self.assertNotContains(r, 'Hoy de Luis')     # no es suya
        self.assertNotContains(r, 'Perdida')         # etapa final: ya no se llama
        self.assertNotContains(r, 'Finanzas del mes')
        self.assertNotContains(r, 'Embudo por etapas')
        self.assertNotContains(r, 'Importar CSV')
        self.assertContains(r, 'Mis llamadas')

    def test_superusuario_ve_todo_el_equipo_embudo_y_finanzas(self):
        r = self.inicio(self.admin)
        self.assertContains(r, 'Hoy de Luis')
        self.assertContains(r, 'Embudo por etapas')
        self.assertContains(r, 'Llamadas por vendedor')
        self.assertContains(r, 'Finanzas del mes')
        self.assertContains(r, 'Datos de ejemplo')
        self.assertContains(r, ', Juan')   # el saludo usa el nombre

    def test_filtro_de_vencidas(self):
        r = self.inicio(self.ana, agenda='vencidas')
        self.assertContains(r, 'Vencida de Ana')
        self.assertNotContains(r, 'Hoy de Ana')

    def test_llamadas_de_la_semana_cuentan_contestadas_e_interesados(self):
        r = self.inicio(self.admin)
        fila = r.context['llamadas']['filas'][0]
        self.assertEqual((fila['nombre'], fila['total'], fila['contestaron'], fila['interesados']), ('Ana Ruiz', 3, 2, 1))

    def test_whatsapp_solo_para_celulares(self):
        r = self.inicio(self.ana)
        filas = {f['empresa']: f for f in r.context['agenda']['filas']}
        self.assertEqual(filas['Vencida de Ana']['whatsapp'], 'https://wa.me/573001111111')
        self.assertEqual(filas['Hoy de Ana']['whatsapp'], '')   # fijo de Medellín


class UtilidadesFormatoTests(TestCase):
    def test_telefono_legible(self):
        self.assertEqual(telefono_legible('+573105550142'), '310 555 0142')
        self.assertEqual(telefono_legible('+14155550100'), '+14155550100')

    def test_url_whatsapp(self):
        self.assertEqual(url_whatsapp('+573105550142'), 'https://wa.me/573105550142')
        self.assertEqual(url_whatsapp('+576045550110'), '')
        self.assertEqual(url_whatsapp(''), '')

    def test_pesos(self):
        self.assertEqual(pesos(1250000), '$1.250.000')
        self.assertEqual(pesos(0), '$0')


class UsuarioAdminTests(TestCase):
    """El detalle de usuario se muestra en pestañas (unfold)."""

    def test_detalle_de_usuario_en_pestanas(self):
        jefe = User.objects.create_superuser('jefe', password='x')
        self.client.force_login(jefe)
        r = self.client.get(reverse('admin:auth_user_change', args=[jefe.pk]))
        self.assertEqual(r.status_code, 200)
        for pestana in ['Cuenta', 'Datos personales', 'Permisos', 'Fechas']:
            self.assertContains(r, f"activeFieldsetTab = '{slugify(pestana)}'")
        # Crear usuario sigue funcionando (usa su propio formulario, sin pestañas).
        self.assertEqual(self.client.get(reverse('admin:auth_user_add')).status_code, 200)


@override_settings(SITIO_EN_REMODELACION=True)
class ModoRemodelacionTests(TestCase):
    def test_visitante_ve_el_aviso_con_503(self):
        for ruta in ('/', '/bitacora/', '/cualquier-cosa/'):
            r = self.client.get(ruta)
            self.assertEqual(r.status_code, 503, ruta)
            self.assertContains(r, 'remodelación', status_code=503)
        self.assertEqual(r['Retry-After'], '86400')
        # El contacto sale de core/contenido.py
        self.assertContains(r, 'https://wa.me/', status_code=503)
        self.assertContains(r, 'hadmind@gmail.com', status_code=503)

    def test_el_equipo_ve_el_sitio_con_la_franja(self):
        self.client.force_login(User.objects.create_user('ana', password='x', is_staff=True))
        r = self.client.get('/')
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, 'solo el equipo ve el sitio')

    def test_usuario_sin_ser_del_equipo_ve_el_aviso(self):
        self.client.force_login(User.objects.create_user('cliente', password='x'))
        self.assertEqual(self.client.get('/').status_code, 503)

    def test_siguen_funcionando_admin_api_y_salud(self):
        self.assertEqual(self.client.get(reverse('admin:login')).status_code, 200)
        self.assertEqual(self.client.get(reverse('salud')).content, b'ok')
        # La API responde ella misma (401 sin clave), no el aviso
        self.assertEqual(self.client.post(reverse('blog:api_crear')).status_code, 401)
        # La revisión del correo responde ella misma (404 por enlace inválido)
        self.assertEqual(self.client.get('/bitacora/revisar/malo/').status_code, 404)

    @override_settings(SITIO_EN_REMODELACION=False)
    def test_apagado_todo_normal(self):
        r = self.client.get('/')
        self.assertEqual(r.status_code, 200)
        self.assertNotContains(r, 'solo el equipo ve el sitio')
