from django.urls import path, include

from .views import (
    adicionar_emenda_bulk,
    catalogo_de_emendas,
    home_page,
    catalogos,
    emendas,
)

urlpatterns = [
    path("", home_page, name="home"),
    path("emendas/", emendas, name="emendas"),
    path(
        "emendas/adicionar_em_massa",
        adicionar_emenda_bulk,
        name="emendas_adicionar_em_massa",
    ),
    path(
        "emendas/catalogo/<ciclo_nome>",
        catalogo_de_emendas,
        name="catalogo_de_emendas_do_ciclo",
    ),
    path("emendas/catalogo/", catalogos, name="catalogos"),
]
