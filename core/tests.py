from django.test import TestCase
from django.urls import reverse


class SitioContextTests(TestCase):
    def test_sitio_disponible_en_plantillas(self):
        response = self.client.get(reverse('landing:home'))
        sitio = response.context['sitio']
        self.assertEqual(len(sitio['servicios']), 11)
        self.assertEqual(sitio['menu'][0], {'num': '01', 'etiqueta': 'Inicio', 'href': '/'})
        self.assertEqual(sitio['menu'][1]['href'], '/#nosotros')
