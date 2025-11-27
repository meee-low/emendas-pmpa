from django.urls import path, include

from .views import (
    adicionar_emenda_bulk,
    catalogo_de_emendas,
    home_page,
    catalogos,
    emendas,
    parlamentares,
    transacoes_do_parlamentar,
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
        "emendas/catalogos/<ciclo_nome>",
        catalogo_de_emendas,
        name="catalogo_de_emendas_do_ciclo",
    ),
    path("emendas/catalogos/", catalogos, name="catalogos"),
    path(
        "investimentos/parlamentar/<int:parlamentar_id>",
        transacoes_do_parlamentar,
        name="transacoes_do_parlamentar",
    ),
    path(
        "investimentos/",
        transacoes_do_parlamentar,
        name="meus_investimentos",
    ),
    path(
        "investimentos/user/<int:user_id>",
        transacoes_do_parlamentar,
        name="transacoes_do_user",
    ),
    path(
        "parlamentares/",
        parlamentares,
        name="lista_de_parlamentares"

    )
]
