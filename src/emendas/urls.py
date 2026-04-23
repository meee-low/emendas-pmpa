from django.urls import path

from .views import (
    adicionar_emenda_bulk,
    adicionar_parlamentar_bulk,
    catalogo_de_emendas,
    catalogos,
    em_construcao,
    emendas,
    ciclo_view,
    home_page,
    novo_ciclo,
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
        "investimentos/ciclo/<int:ciclo_id>", em_construcao, name="transacoes_do_ciclo"
    ),
    path(
        "investimentos/user/<int:user_id>",
        transacoes_do_parlamentar,
        name="transacoes_do_user",
    ),
    path("parlamentares/", parlamentares, name="lista_de_parlamentares"),
    path(
        "parlamentares/adicionar_em_massa",
        adicionar_parlamentar_bulk,
        name="parlamentares_adicionar_em_massa",
    ),
    path("ciclo/novo", novo_ciclo, name="novo_ciclo"),
    path("ciclo/<str:ciclo_slug>", ciclo_view, name="visao_ciclo"),
    path("transacoes_do_ciclo", em_construcao, name="transacoes_do_ciclo"),
    path("", ciclo_view, name="gestao_home"),
]
