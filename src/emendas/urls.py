from django.urls import path, include

from .views import catalogo_de_emendas, home_page, catalogos

urlpatterns = [
    path("", home_page, name="home"),
    path(
        "emendas/catalogo/<ciclo_nome>",
        catalogo_de_emendas,
        name="catalogo_de_emendas_do_ciclo",
    ),
    path("emendas/catalogo/", catalogos, name="catalogos"),
]
