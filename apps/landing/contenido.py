"""Contenido que solo usa la home. Lo compartido con otras páginas está en core/contenido.py."""

# EJEMPLO del boceto: sustituir por cifras reales antes de publicar en main
METRICAS = [
    {'valor': '70%', 'texto': 'menos tareas manuales en los procesos automatizados'},
    {'valor': '3x', 'texto': 'más rápido desde la idea hasta el sistema en producción'},
    {'valor': '24/7', 'texto': 'operación continua de flujos e integraciones'},
]

# Sección Nosotros: textos editables
NOSOTROS = {
    'titulo': 'Convertimos procesos complejos en sistemas simples',
    'parrafos': [
        'Somos un equipo de ingeniería y diseño que convierte procesos complejos en sistemas simples, inteligentes y listos para crecer.',
        'Queremos ser el aliado tecnológico de referencia en Latinoamérica para las empresas que quieren crecer con tecnología.',
    ],
    'titulo_clientes': 'Algunos de nuestros clientes',
}

# EJEMPLO: sustituir por clientes reales (con su permiso). 'logo' es la ruta dentro de static/
# (p. ej. 'landing/img/clientes/empresa.png'); sin logo se muestra el nombre. 'url' es opcional.
CLIENTES = [
    {'nombre': 'Cliente 1', 'logo': '', 'url': ''},
    {'nombre': 'Cliente 2', 'logo': '', 'url': ''},
    {'nombre': 'Cliente 3', 'logo': '', 'url': ''},
    {'nombre': 'Cliente 4', 'logo': '', 'url': ''},
    {'nombre': 'Cliente 5', 'logo': '', 'url': ''},
    {'nombre': 'Cliente 6', 'logo': '', 'url': ''},
]

# EJEMPLO del boceto: sustituir por un testimonio real (con permiso del cliente) antes de publicar en main
TESTIMONIO = {
    'cita': 'HADMIND entendió nuestro proceso antes de escribir una línea de código. Hoy el sistema trabaja solo y el equipo se dedica a lo importante.',
    'autor': 'DIRECTOR DE OPERACIONES · NOMBRE DE LA EMPRESA',
}

# Opciones de los desplegables del formulario de contacto
MOTIVOS_CONSULTA = [
    'Nuevo proyecto',
    'Automatización con IA',
    'Cotización',
    'Soporte a un proyecto existente',
    'Alianzas',
    'Otro',
]

ORIGENES = ['Google', 'Redes sociales', 'Recomendación', 'Evento', 'Otro']
