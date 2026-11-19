from django.urls import path

from . import api, views

app_name = 'blog'

urlpatterns = [
    path('api/bitacora/', api.crear_articulo, name='api_crear'),
    path('api/bitacora/fuentes/', api.fuentes, name='api_fuentes'),
    path('bitacora/', views.lista, name='lista'),
    # "revisar" va antes que el slug; no chocan porque la revisión lleva un
    # segmento más (el token), pero así queda claro cuál se evalúa primero.
    path('bitacora/revisar/<str:token>/', views.revisar, name='revisar'),
    path('bitacora/<slug:slug>/', views.detalle, name='detalle'),
]
