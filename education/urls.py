from django.urls import path
from . import views

app_name = 'education'

urlpatterns = [
    path('',                           views.index,             name='index'),
    path('municipios/',                views.municipio_list,    name='municipio_list'),
    path('municipios/<str:co>/',       views.municipio_detail,  name='municipio_detail'),
    path('mapa/',                      views.mapa,              name='mapa'),
    path('analise/',                   views.analise,           name='analise'),
    path('modelos/',                   views.modelos,           name='modelos'),
    path('modelos/<str:nome>/',        views.modelo_detail,     name='modelo_detail'),
    path('clusters/',                  views.clusters,          name='clusters'),

    # API JSON
    path('api/municipios/',            views.api_municipios,    name='api_municipios'),
    path('api/municipio/<str:co>/',    views.api_municipio,     name='api_municipio'),
    path('api/mapa/',                  views.api_mapa,          name='api_mapa'),
    path('api/malha/',                 views.api_malha_municipios, name='api_malha'),
    path('api/modelos/',               views.api_modelos,       name='api_modelos'),
    path('api/clusters/',              views.api_clusters,      name='api_clusters'),
]
