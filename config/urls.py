from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('apps.blog.urls')),
    path('', include('apps.landing.urls')),
]

# En desarrollo Django sirve las imágenes subidas. static() no hace nada con
# DEBUG apagado: en el VPS las sirve Nginx (más rápido y sin pasar por Django).
urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
