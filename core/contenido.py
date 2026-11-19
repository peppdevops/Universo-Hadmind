"""Contenido fijo del sitio que se usa en varias páginas (header, footer, landing)."""

CONTACTO = {
    'correo': 'hadmind@gmail.com',
    'telefono': '+57 323 387 1149',
    'telefono_href': '+573233871149',
    'whatsapp_url': 'https://wa.me/573233871149',
    # El footer solo muestra las redes que tengan URL
    'instagram_url': 'https://www.instagram.com/hadmind.co/',
    'linkedin_url': 'https://www.linkedin.com/company/hadmind/',
    'sede': 'Itagüí, Antioquia, Colombia',
    'codigo_postal': '055410',
}

# Enlaces del menú. Los de dos valores son secciones de la landing (#id); los
# de tres llevan a otra página por su nombre de URL. La Bitácora va a su
# página y no a #bitacora porque esa sección se oculta mientras no haya
# artículos publicados. Asistente IA se añade cuando exista su app.
MENU = [
    ('inicio', 'Inicio'),
    ('nosotros', 'Nosotros'),
    ('servicios', 'Servicios'),
    ('bitacora', 'Bitácora', 'blog:lista'),
    ('contacto', 'Contacto'),
]

# Imagen opcional por servicio: añadir 'imagen': 'landing/img/servicios/archivo.webp'
# (ruta dentro de static/). Sin imagen, la tarjeta muestra su número.
SERVICIOS = [
    {
        'titulo': 'Soluciones para startups',
        'linea': 'Del MVP al producto listo para crecer.',
        'resumen': 'Acompañamos a startups desde la idea: validamos, construimos el MVP y preparamos la tecnología para escalar.',
        'imagen': 'landing/img/servicios/soluciones-para-startups.webp',
    },
    {
        'titulo': 'Bots inteligentes con IA',
        'linea': 'Asistentes que atienden, responden y venden por ti.',
        'resumen': 'Asistentes con IA que atienden clientes, responden preguntas y gestionan solicitudes las 24 horas.',
        'imagen': 'landing/img/servicios/bots-inteligentes-con-ia.webp',
    },
    {
        'titulo': 'Desarrollo de software',
        'linea': 'Software a medida para la operación de tu empresa.',
        'resumen': 'Construimos software a la medida de tu operación, desde la arquitectura hasta la puesta en producción.',
        'imagen': 'landing/img/servicios/desarrollo-de-software.webp',
    },
    {
        'titulo': 'Plataformas SaaS',
        'linea': 'Productos por suscripción listos para escalar.',
        'resumen': 'Diseñamos y desarrollamos productos SaaS multiusuario, con suscripciones, paneles y escalabilidad en la nube.',
        'imagen': 'landing/img/servicios/plataformas-saas.webp',
    },
    {
        'titulo': 'Plataformas a la medida',
        'linea': 'Sistemas diseñados alrededor de tus procesos.',
        'resumen': 'Plataformas construidas alrededor de tus procesos, sin adaptar tu negocio a una herramienta genérica.',
        'imagen': 'landing/img/servicios/plataformas-digitales-a-la-medida.webp',
    },
    {
        'titulo': 'Sistemas ERP y CRM',
        'linea': 'Gestión, ventas y clientes en un solo sistema.',
        'resumen': 'Sistemas para gestionar inventario, finanzas, ventas y clientes desde un solo lugar.',
        'imagen': 'landing/img/servicios/sistemas-erp-crm.webp',
    },
    {
        'titulo': 'Integraciones de sistemas',
        'linea': 'Tus herramientas conectadas y sincronizadas.',
        'resumen': 'Conectamos tus herramientas y bases de datos para que la información fluya sin trabajo manual.',
        'imagen': 'landing/img/servicios/integraciones-de-sistemas.webp',
    },
    {
        'titulo': 'Automatización con IA',
        'linea': 'Procesos manuales convertidos en flujos automáticos.',
        'resumen': 'Usamos IA para ejecutar tareas repetitivas: clasificar, extraer datos, responder y tomar decisiones simples.',
        'imagen': 'landing/img/servicios/automatizacion-con-ia.webp',
    },
    {
        'titulo': 'Aplicaciones y apps móviles',
        'linea': 'Apps para iOS y Android conectadas a tu negocio.',
        'resumen': 'Apps nativas e híbridas para iOS y Android, conectadas a tus sistemas y listas para publicar.',
        'imagen': 'landing/img/servicios/app-web-moviles.webp',
    },
    {
        'titulo': 'Desarrollo web',
        'linea': 'Sitios rápidos, seguros y fáciles de administrar.',
        'resumen': 'Sitios web rápidos, seguros y administrables, pensados para crecer con tu empresa.',
        'imagen': 'landing/img/servicios/desarrollo-web.webp',
    },
    {
        'titulo': 'Landing pages',
        'linea': 'Páginas enfocadas en convertir visitas en clientes.',
        'resumen': 'Páginas enfocadas en una sola acción: convertir visitas en clientes potenciales.',
        'imagen': 'landing/img/servicios/landing-pages.webp',
    },
]
