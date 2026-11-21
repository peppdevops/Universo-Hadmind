"""Tests del CRM.

docker compose exec web python manage.py test apps.crm

Django crea una base de datos de prueba vacía, aplica las migraciones (así que
las etapas iniciales ya existen) y la borra al terminar: tus datos reales no
se tocan.
"""

from io import StringIO

from django.contrib.admin.sites import site
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.management import call_command
from django.test import RequestFactory, TestCase
from django.urls import reverse

from core.utils import (
    InstagramInvalido, TelefonoInvalido, normalizar_correo, normalizar_instagram, normalizar_telefono,
)

from .admin import LlamadaInline
from .models import GRUPO_VENDEDOR, ClienteActivo, Contacto, EmpresaPorLlamar, Etapa, Interaccion
from .services import importar_contactos_csv

User = get_user_model()


def csv_subido(texto, codificacion='utf-8-sig', nombre='empresas.csv'):
    """Simula un archivo subido desde el formulario."""
    return SimpleUploadedFile(nombre, texto.encode(codificacion), content_type='text/csv')


class NormalizacionTests(TestCase):
    def test_telefonos_colombianos_quedan_con_57(self):
        for entrada in ['300 123 4567', '3001234567', '573001234567', '+57 300-123-4567', '(300) 123.45.67']:
            with self.subTest(entrada=entrada):
                self.assertEqual(normalizar_telefono(entrada), '+573001234567')

    def test_telefono_extranjero_conserva_su_codigo(self):
        self.assertEqual(normalizar_telefono('+1 (305) 555-1234'), '+13055551234')

    def test_telefono_invalido(self):
        for entrada in ['123', '+57 300 123', '30012345678']:
            with self.subTest(entrada=entrada), self.assertRaises(TelefonoInvalido):
                normalizar_telefono(entrada)

    def test_vacio_y_correo(self):
        self.assertEqual(normalizar_telefono(''), '')
        self.assertEqual(normalizar_correo('  Ana@Empresa.CO '), 'ana@empresa.co')

    def test_instagram_como_lo_pegue_el_vendedor_queda_igual(self):
        for entrada in [
            '@Ferreteria.Tornillo', 'ferreteria.tornillo', ' @ferreteria.tornillo ',
            'https://www.instagram.com/ferreteria.tornillo/',
            'instagram.com/Ferreteria.Tornillo',
            'https://instagram.com/ferreteria.tornillo?igsh=MWQ1ZGUxMzBkMA==',
        ]:
            with self.subTest(entrada=entrada):
                self.assertEqual(normalizar_instagram(entrada), 'ferreteria.tornillo')
        self.assertEqual(normalizar_instagram(''), '')

    def test_instagram_invalido(self):
        # Espacios, signos raros, más de 30 letras, o el enlace a una publicación (no a un perfil).
        for entrada in ['ferreteria el tornillo', 'tienda#1', 'a' * 31, 'https://www.instagram.com/p/C1abc/']:
            with self.subTest(entrada=entrada), self.assertRaises(InstagramInvalido):
                normalizar_instagram(entrada)


class ContactoModeloTests(TestCase):
    def test_al_guardar_normaliza_y_toma_la_primera_etapa_abierta(self):
        c = Contacto.objects.create(empresa='Acme', telefono='300 123 4567', correo='Ventas@Acme.CO')
        self.assertEqual(c.telefono, '+573001234567')
        self.assertEqual(c.correo, 'ventas@acme.co')
        self.assertEqual(c.etapa.nombre, 'Por llamar')

    def test_telefono_duplicado_aunque_se_escriba_distinto(self):
        Contacto.objects.create(empresa='Acme', telefono='3001234567')
        otro = Contacto(empresa='Otra', telefono='+57 300 123 4567')
        with self.assertRaisesMessage(ValidationError, 'Ya existe un contacto con este teléfono.'):
            otro.full_clean()

    def test_correo_duplicado_con_otras_mayusculas(self):
        Contacto.objects.create(empresa='Acme', correo='ana@acme.co')
        otro = Contacto(empresa='Otra', correo='ANA@acme.co')
        with self.assertRaisesMessage(ValidationError, 'Ya existe un contacto con este correo.'):
            otro.full_clean()

    def test_vacios_no_cuentan_como_duplicados(self):
        Contacto.objects.create(empresa='A', telefono='3001111111')
        Contacto.objects.create(empresa='B', telefono='3002222222')  # los dos sin correo
        self.assertEqual(Contacto.objects.count(), 2)

    def test_exige_telefono_o_correo(self):
        with self.assertRaises(ValidationError):
            Contacto(empresa='Sin datos').full_clean()

    def test_instagram_se_guarda_como_usuario_y_arma_el_enlace(self):
        c = Contacto.objects.create(empresa='Acme', telefono='3001234567', instagram='https://instagram.com/Acme.Co/')
        self.assertEqual(c.instagram, 'acme.co')
        self.assertEqual(c.url_instagram, 'https://www.instagram.com/acme.co/')

    def test_instagram_invalido_marca_el_campo(self):
        c = Contacto(empresa='Acme', telefono='3001234567', instagram='no es un usuario')
        with self.assertRaises(ValidationError) as error:
            c.full_clean()
        self.assertIn('instagram', error.exception.message_dict)


class ImportacionTests(TestCase):
    def setUp(self):
        Contacto.objects.create(empresa='Ya existe', telefono='3009999999', correo='existe@x.co')

    def test_importa_saltando_duplicados_y_errores(self):
        # Formato típico de Excel en español: BOM, ";" y encabezados con tildes.
        texto = (
            'Empresa;Contacto;Teléfono;Correo;Ciudad;Rubro\n'
            'Alfa;Ana;300 111 1111;ana@alfa.co;Medellín;Retail\n'      # 2: ok
            'Beta;Luis;3009999999;;Bogotá;\n'                          # 3: tel. ya en la base
            'Gamma;;;EXISTE@x.co;;\n'                                  # 4: correo ya en la base
            'Delta;;3001111111;;;\n'                                   # 5: tel. repetido de la fila 2
            ';Sin empresa;3002222222;;;\n'                             # 6: error
            'Epsilon;;;;Cali;\n'                                       # 7: error, sin tel. ni correo
            'Zeta;;123;;;\n'                                           # 8: error, tel. no válido
            'Eta;;;eta@eta.co;;Salud\n'                                # 9: ok
            ';;;;;\n'                                                  # vacía: se ignora
        )
        resultado = importar_contactos_csv(csv_subido(texto))

        self.assertEqual(resultado.importadas, [2, 9])
        self.assertEqual([fila for fila, _ in resultado.duplicadas], [3, 4, 5])
        self.assertEqual([fila for fila, _ in resultado.errores], [6, 7, 8])

        alfa = Contacto.objects.get(empresa='Alfa')
        self.assertEqual(alfa.telefono, '+573001111111')
        self.assertEqual(alfa.ciudad, 'Medellín')
        self.assertEqual(alfa.fuente, Contacto.Fuente.IMPORTACION)
        self.assertEqual(alfa.etapa.nombre, 'Por llamar')
        self.assertEqual(Contacto.objects.count(), 3)

    def test_acepta_csv_de_excel_en_windows_1252_con_comas(self):
        texto = 'empresa,telefono,ciudad\nÑandú SAS,3005555555,Medellín\n'
        resultado = importar_contactos_csv(csv_subido(texto, codificacion='cp1252'))
        self.assertEqual(resultado.importadas, [2])
        c = Contacto.objects.get(telefono='+573005555555')
        self.assertEqual((c.empresa, c.ciudad), ('Ñandú SAS', 'Medellín'))

    def test_columna_instagram_opcional(self):
        # La de la plantilla de Excel; la fila con Instagram malo se salta y se informa.
        texto = (
            'Empresa;Telefono;Instagram\n'
            'Alfa;3001111111;@Alfa.Shop\n'      # 2: ok
            'Beta;3002222222;\n'                # 3: ok, sin Instagram
            'Gamma;3003333333;no sirve esto\n'  # 4: error
        )
        resultado = importar_contactos_csv(csv_subido(texto))
        self.assertEqual(resultado.importadas, [2, 3])
        self.assertEqual([fila for fila, _ in resultado.errores], [4])
        self.assertEqual(Contacto.objects.get(empresa='Alfa').instagram, 'alfa.shop')
        self.assertEqual(Contacto.objects.get(empresa='Beta').instagram, '')

    def test_asigna_todas_al_vendedor(self):
        vendedor = User.objects.create_user('vendedor', is_staff=True)
        importar_contactos_csv(csv_subido('empresa;telefono\nAlfa;3001111111\n'), asignar_a=vendedor)
        self.assertEqual(Contacto.objects.get(empresa='Alfa').asignado_a, vendedor)


class CrmAdminTests(TestCase):
    """Permisos y comportamiento del admin con un superusuario y dos vendedores."""

    @classmethod
    def setUpTestData(cls):
        # StringIO recoge lo que imprime el comando para que no ensucie la salida de los tests.
        call_command('crear_grupo_vendedor', stdout=StringIO())
        grupo = Group.objects.get(name=GRUPO_VENDEDOR)
        cls.admin = User.objects.create_superuser('jefe', password='x')
        cls.vendedor = User.objects.create_user('ana', password='x', is_staff=True, first_name='Ana')
        cls.otro = User.objects.create_user('luis', password='x', is_staff=True, first_name='Luis')
        cls.vendedor.groups.add(grupo)
        cls.otro.groups.add(grupo)
        cls.mia = Contacto.objects.create(empresa='Empresa de Ana', telefono='3001111111', asignado_a=cls.vendedor)
        cls.ajena = Contacto.objects.create(empresa='Empresa de Luis', telefono='3002222222', asignado_a=cls.otro)

    def url(self, nombre, *args):
        return reverse(f'admin:crm_empresaporllamar_{nombre}', args=args)

    def datos_cambio(self, etapa, **extra):
        """POST mínimo del formulario de cambio, con el formset de llamadas vacío."""
        datos = {
            'etapa': etapa.pk,
            'proxima_llamada': '',
            'interacciones-TOTAL_FORMS': '0',
            'interacciones-INITIAL_FORMS': '0',
            'interacciones-MIN_NUM_FORMS': '0',
            'interacciones-MAX_NUM_FORMS': '1000',
        }
        datos.update(extra)
        return datos

    def test_vendedor_solo_ve_sus_empresas(self):
        self.client.force_login(self.vendedor)
        respuesta = self.client.get(self.url('changelist'))
        self.assertContains(respuesta, 'Empresa de Ana')
        self.assertNotContains(respuesta, 'Empresa de Luis')
        # Ni siquiera escribiendo la URL de la empresa ajena (el admin redirige).
        self.assertEqual(self.client.get(self.url('change', self.ajena.pk)).status_code, 302)

    def test_vendedor_no_ve_la_lista_de_todos_los_contactos(self):
        self.client.force_login(self.vendedor)
        self.assertEqual(self.client.get(reverse('admin:crm_contacto_changelist')).status_code, 403)

    def test_vendedor_no_puede_editar_datos_de_la_empresa(self):
        self.client.force_login(self.vendedor)
        contactado = Etapa.objects.get(nombre='Contactado')
        datos = self.datos_cambio(contactado, empresa='Nombre cambiado', telefono='3007777777')
        respuesta = self.client.post(self.url('change', self.mia.pk), datos)
        self.assertEqual(respuesta.status_code, 302)
        self.mia.refresh_from_db()
        self.assertEqual(self.mia.empresa, 'Empresa de Ana')       # ignorado: es solo lectura
        self.assertEqual(self.mia.telefono, '+573001111111')
        self.assertEqual(self.mia.etapa, contactado)               # la etapa sí se puede cambiar

    def test_vendedor_no_puede_crear_importar_ni_usar_acciones(self):
        self.client.force_login(self.vendedor)
        self.assertEqual(self.client.get(self.url('add')).status_code, 403)
        self.assertEqual(self.client.get(self.url('importar')).status_code, 403)
        request = RequestFactory().get('/')
        request.user = self.vendedor
        self.assertEqual(site._registry[EmpresaPorLlamar].get_actions(request), {})

    def test_vendedor_puede_agregar_llamadas_pero_no_editarlas(self):
        self.client.force_login(self.vendedor)
        datos = self.datos_cambio(
            self.mia.etapa,
            **{
                'interacciones-TOTAL_FORMS': '1',
                'interacciones-0-contacto': self.mia.pk,
                'interacciones-0-fecha_0': '2026-11-18',
                'interacciones-0-fecha_1': '10:30:00',
                'interacciones-0-resultado': Interaccion.Resultado.INTERESADO,
                'interacciones-0-comentario': 'Pide cotización',
            },
        )
        self.assertEqual(self.client.post(self.url('change', self.mia.pk), datos).status_code, 302)
        llamada = Interaccion.objects.get(contacto=self.mia)
        self.assertEqual(llamada.usuario, self.vendedor)  # se llena sola con quien la registra

        request = RequestFactory().get('/')
        request.user = self.vendedor
        inline = LlamadaInline(EmpresaPorLlamar, site)
        self.assertFalse(inline.has_change_permission(request, self.mia))
        self.assertFalse(inline.has_delete_permission(request, self.mia))

    def test_al_pasar_a_cliente_activo_cambia_de_lista(self):
        self.client.force_login(self.vendedor)
        cliente = Etapa.objects.get(nombre='Cliente activo')
        respuesta = self.client.post(self.url('change', self.mia.pk), self.datos_cambio(cliente))
        # Se le lleva a la lista donde quedó la empresa.
        self.assertRedirects(respuesta, reverse('admin:crm_clienteactivo_changelist'))
        self.assertFalse(EmpresaPorLlamar.objects.filter(pk=self.mia.pk).exists())
        self.assertTrue(ClienteActivo.objects.filter(pk=self.mia.pk).exists())
        self.assertContains(self.client.get(reverse('admin:crm_clienteactivo_changelist')), 'Empresa de Ana')

    def test_superusuario_asigna_con_las_acciones(self):
        self.client.force_login(self.admin)
        respuesta = self.client.post(self.url('changelist'), {
            'action': f'asignar_a_{self.otro.pk}',
            '_selected_action': [self.mia.pk],
        })
        self.assertEqual(respuesta.status_code, 302)
        self.mia.refresh_from_db()
        self.assertEqual(self.mia.asignado_a, self.otro)

    def test_superusuario_importa_desde_el_admin(self):
        self.client.force_login(self.admin)
        respuesta = self.client.post(self.url('importar'), {
            'archivo': csv_subido('empresa;telefono\nNueva;3003333333\nRepetida;3001111111\n'),
            'asignar_a': self.vendedor.pk,
        }, follow=True)
        self.assertContains(respuesta, 'Se importaron 1 empresas.')
        self.assertContains(respuesta, '1 duplicadas')
        self.assertEqual(Contacto.objects.get(empresa='Nueva').asignado_a, self.vendedor)

    def test_busqueda_por_telefono_sin_formato(self):
        self.client.force_login(self.admin)
        respuesta = self.client.get(self.url('changelist'), {'q': '300 111 1111'})
        self.assertContains(respuesta, 'Empresa de Ana')
        self.assertNotContains(respuesta, 'Empresa de Luis')


class MenuAdminTests(TestCase):
    """Menú lateral de unfold: cada uno ve solo lo que le corresponde."""

    @classmethod
    def setUpTestData(cls):
        call_command('crear_grupo_vendedor', stdout=StringIO())
        cls.admin = User.objects.create_superuser('jefe', password='x')
        cls.vendedor = User.objects.create_user('ana', password='x', is_staff=True)
        cls.vendedor.groups.add(Group.objects.get(name=GRUPO_VENDEDOR))

    def test_vendedor_ve_ventas_pero_no_equipo(self):
        self.client.force_login(self.vendedor)
        respuesta = self.client.get(reverse('admin:crm_empresaporllamar_changelist'))
        self.assertContains(respuesta, reverse('admin:crm_clienteactivo_changelist'))
        self.assertNotContains(respuesta, reverse('admin:auth_user_changelist'))
        # Y el botón de importar no aparece.
        self.assertNotContains(respuesta, reverse('admin:crm_empresaporllamar_importar'))

    def test_vendedor_no_entra_a_usuarios_escribiendo_la_url(self):
        self.client.force_login(self.vendedor)
        self.assertEqual(self.client.get(reverse('admin:auth_user_changelist')).status_code, 403)

    def test_superusuario_ve_equipo_y_boton_importar(self):
        self.client.force_login(self.admin)
        respuesta = self.client.get(reverse('admin:crm_empresaporllamar_changelist'))
        self.assertContains(respuesta, reverse('admin:auth_user_changelist'))
        self.assertContains(respuesta, reverse('admin:crm_empresaporllamar_importar'))

    # El enlace "Todas las aplicaciones" se reconoce por el código que lo abre.
    MARCA_TODAS = 'openAllApplications = !openAllApplications'

    def test_todas_las_aplicaciones_solo_para_superusuario(self):
        self.client.force_login(self.vendedor)
        self.assertNotContains(self.client.get(reverse('admin:crm_empresaporllamar_changelist')), self.MARCA_TODAS)
        self.client.force_login(self.admin)
        self.assertContains(self.client.get(reverse('admin:crm_empresaporllamar_changelist')), self.MARCA_TODAS)


class ListasYDetalleTests(TestCase):
    """Bloque B: columnas del diseño, acción "Cambiar etapa" y resumen del detalle."""

    @classmethod
    def setUpTestData(cls):
        from datetime import timedelta
        from django.utils import timezone

        call_command('crear_grupo_vendedor', stdout=StringIO())
        cls.admin = User.objects.create_superuser('jefe', password='x')
        cls.ana = User.objects.create_user('ana', password='x', is_staff=True, first_name='Ana', last_name='Ruiz')
        cls.ana.groups.add(Group.objects.get(name=GRUPO_VENDEDOR))
        cls.empresa = Contacto.objects.create(
            empresa='Auto Direct', telefono='3105550142', rubro='Lavadero', ciudad='Sabaneta',
            asignado_a=cls.ana, proxima_llamada=timezone.now() - timedelta(days=2),
        )
        Interaccion.objects.create(contacto=cls.empresa, usuario=cls.ana, resultado='no_contesto')

    def lista(self, usuario):
        self.client.force_login(usuario)
        return self.client.get(reverse('admin:crm_empresaporllamar_changelist'))

    def test_lista_muestra_columnas_del_diseno(self):
        r = self.lista(self.admin)
        self.assertContains(r, '310 555 0142')         # teléfono legible
        self.assertContains(r, 'Lavadero · Sabaneta')   # subtítulo de la empresa
        self.assertContains(r, 'Vencida ·')             # próxima llamada vencida
        self.assertContains(r, 'No contestó')           # resultado de la última llamada
        self.assertContains(r, 'Ana R.')                # vendedor
        self.assertNotContains(r, 'wa.me')                # el CRM no tiene WhatsApp
        self.assertContains(r, '1 empresa · 0 llamadas para hoy')

    def test_vendedor_no_ve_columna_vendedor(self):
        r = self.lista(self.ana)
        self.assertContains(r, 'Auto Direct')
        self.assertNotContains(r, 'Ana R.')

    def test_accion_cambiar_etapa(self):
        self.client.force_login(self.admin)
        contactado = Etapa.objects.get(nombre='Contactado')
        self.client.post(reverse('admin:crm_empresaporllamar_changelist'), {
            'action': f'etapa_{contactado.pk}', '_selected_action': [self.empresa.pk],
        })
        self.empresa.refresh_from_db()
        self.assertEqual(self.empresa.etapa, contactado)

    def test_detalle_muestra_resumen_sin_whatsapp(self):
        self.client.force_login(self.ana)
        r = self.client.get(reverse('admin:crm_empresaporllamar_change', args=[self.empresa.pk]))
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, 'hd-resumen')
        self.assertContains(r, 'tel:+573105550142')
        self.assertNotContains(r, 'wa.me')
        # Sin Instagram guardado, no hay botón.
        self.assertNotContains(r, 'instagram.com')

    def test_boton_instagram_abre_el_perfil_en_pestana_nueva(self):
        Contacto.objects.filter(pk=self.empresa.pk).update(instagram='autodirect.co')
        self.client.force_login(self.ana)
        r = self.client.get(reverse('admin:crm_empresaporllamar_change', args=[self.empresa.pk]))
        self.assertContains(r, 'href="https://www.instagram.com/autodirect.co/"')
        self.assertContains(r, 'target="_blank"')
        self.assertContains(r, 'rel="noopener noreferrer"')

    def test_menu_dice_empresas(self):
        r = self.lista(self.admin)
        self.assertEqual(r.context['title'], 'Empresas')
        self.assertNotContains(r, 'por llamar')

    def test_detalle_en_tres_pestanas(self):
        self.client.force_login(self.admin)
        r = self.client.get(reverse('admin:crm_empresaporllamar_change', args=[self.empresa.pk]))
        claves = [p['clave'] for p in r.context['pestanas']]
        self.assertEqual(claves, ['seguimiento', 'llamadas', 'empresa'])
        self.assertEqual(r.context['pestanas'][1]['cantidad'], 1)   # una llamada registrada
        self.assertEqual(r.context['pestana_con_error'], '')
        # Las llamadas van dentro de su pestaña, y la fila de la lista abre esa pestaña.
        self.assertContains(r, 'id="interacciones-group"', count=1)
        self.assertContains(self.lista(self.admin), '#llamadas')

    def test_error_abre_la_pestana_que_lo_tiene(self):
        # Teléfono inválido: el error está en la pestaña Empresa, que debe
        # abrirse sola; si no, quedaría escondido y parecería que no guarda.
        self.client.force_login(self.admin)
        url = reverse('admin:crm_empresaporllamar_change', args=[self.empresa.pk])
        datos = {
            'empresa': 'Auto Direct', 'telefono': '123', 'correo': '', 'etapa': self.empresa.etapa_id,
            'interacciones-TOTAL_FORMS': '0', 'interacciones-INITIAL_FORMS': '0',
        }
        r = self.client.post(url, datos)
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.context['pestana_con_error'], 'empresa')
