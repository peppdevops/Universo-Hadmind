from django.test import TestCase
from django.urls import reverse


class HomeTests(TestCase):
    def test_home_responde(self):
        response = self.client.get(reverse('landing:home'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'landing/home.html')

    def test_home_incluye_header_y_menu(self):
        response = self.client.get(reverse('landing:home'))
        self.assertTemplateUsed(response, 'partials/_header.html')
        self.assertTemplateUsed(response, 'partials/_menu.html')
        self.assertContains(response, 'href="/#servicios"')

    def test_home_muestra_metricas_con_valor_final(self):
        response = self.client.get(reverse('landing:home'))
        self.assertContains(response, 'data-metrica-valor="70%">70%</div>', html=False)

    def test_home_incluye_todas_las_secciones(self):
        response = self.client.get(reverse('landing:home'))
        for seccion in ('inicio', 'nosotros', 'servicios', 'contacto', 'ubicaciones'):
            self.assertContains(response, f'id="{seccion}"')

    def test_formulario_de_contacto_tiene_campos_obligatorios(self):
        response = self.client.get(reverse('landing:home'))
        for campo in ('motivo', 'nombre', 'apellido', 'correo', 'telefono', 'empresa', 'ubicacion', 'consulta', 'origen'):
            self.assertContains(response, f'name="{campo}"')
        self.assertContains(response, 'data-whatsapp="https://wa.me/')

    def test_home_incluye_footer(self):
        response = self.client.get(reverse('landing:home'))
        self.assertTemplateUsed(response, 'partials/_footer.html')
        self.assertContains(response, 'Landing pages')
        self.assertContains(response, 'href="https://wa.me/')
