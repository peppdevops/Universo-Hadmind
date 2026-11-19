from django.urls import path

from . import api, views

app_name = 'blog'

urlpatterns = [
    path('api/bitacora/', api.crear_articulo, name='api_crear'),
    path('bitacora/revisar/<str:token>/', views.revisar, name='revisar'),
]
