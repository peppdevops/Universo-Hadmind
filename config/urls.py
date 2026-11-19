from allauth.account.decorators import secure_admin_login
from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path
from django.views.generic import RedirectView

from core.views import favicon, salud

# El login propio del admin (solo usuario y contraseña) se cambia por el de
# allauth, que pide además el código del celular. Sin esto, /admin/login/
# sería una puerta trasera sin verificación en 2 pasos.
admin.site.login = secure_admin_login(admin.site.login)

urlpatterns = [
    # La dirección del admin sale del .env (ADMIN_URL): en el VPS es secreta.
    path(settings.ADMIN_URL, admin.site.urls),
    # Login con verificación en 2 pasos (allauth). El registro (/cuenta/signup/)
    # está cerrado por core.cuenta.AdaptadorCuenta.
    # Sin recuperación de contraseña por correo (va antes de allauth para
    # taparla): la contraseña la cambia el superusuario en Equipo → Usuarios.
    path('cuenta/password/reset/', RedirectView.as_view(pattern_name='account_login')),
    path('cuenta/', include('allauth.urls')),
    path('salud/', salud, name='salud'),
    # Los navegadores piden /favicon.ico solos, sin mirar el HTML
    path('favicon.ico', favicon),
    path('', include('apps.blog.urls')),
    path('', include('apps.landing.urls')),
]

# En desarrollo Django sirve las imágenes subidas. static() no hace nada con
# DEBUG apagado: en el VPS las sirve Nginx (más rápido y sin pasar por Django).
urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
