from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpRequest, HttpResponse
from django.db.models import Sum, Prefetch

from emendas.decorators import group_required
from emendas.groups import GrupoDeUsuario
from emendas.models import Ciclo, ParlamentarDoCiclo, PropostaDeEmendaDoCiclo, Tag


def home_page(request: HttpRequest) -> HttpResponse:
    if not request.user.is_authenticated:
        return redirect("login")

    user = request.user
    grupos_do_user = list(user.groups.values_list("name", flat=True))

    # usuário está autenticado
    if "Gestão" in grupos_do_user:
        return redirect("gestao_home")

    if "Parlamentar" in grupos_do_user:
        return redirect("parlamentar_dashboard")

    if user.is_superuser:
        return redirect("/admin")

    return render(request, "home/default_home.html")


@group_required(GrupoDeUsuario.GESTAO)
def gestao_home(request: HttpRequest) -> HttpResponse:
    return render(request, "gestao/gestao_home.html")


@group_required(GrupoDeUsuario.PARLAMENTAR)
def parlamentar_dashboard(request: HttpRequest) -> HttpResponse:
    return render(request, "parlamentar/parlamentar_dashboard.html")


def catalogo_de_emendas(request: HttpRequest, ciclo_nome: str) -> HttpResponse:
    ciclo = get_object_or_404(Ciclo, nome=ciclo_nome)
    emendas = (
        PropostaDeEmendaDoCiclo.objects.filter(ciclo=ciclo)
        .select_related("proposta_de_emenda", "ciclo")
        .prefetch_related(
            Prefetch("proposta_de_emenda__tags", queryset=Tag.objects.all())
        )
        .annotate(total_investido=Sum("transacoes__valor_investido"))
    )

    tags = {
        tag_id: nome
        for tag_id, nome in (
            emendas.values_list(
                "proposta_de_emenda__tags__id", "proposta_de_emenda__tags__nome"
            ).distinct()
        )
    }

    user = request.user
    grupos_do_user = (
        list(user.groups.values_list("name", flat=True))
        if user.is_authenticated
        else []
    )

    return render(
        request,
        "emendas/catalogo_do_ciclo.html",
        {
            "emendas": emendas,
            "ciclo": ciclo,
            "user": user,
            "grupos_do_user": grupos_do_user,
            "tags": tags,
        },
    )


def emenda_do_ciclo(request: HttpRequest, emenda_sqid: str) -> HttpResponse:
    emenda = get_object_or_404(PropostaDeEmendaDoCiclo, sqid=emenda_sqid)
    return render(
        request,
        "emendas/emenda_do_ciclo.html",
        {"emenda": emenda},
    )


@group_required(GrupoDeUsuario.PARLAMENTAR)
def investir_em_emenda(request: HttpRequest, emenda_sqid: str) -> HttpResponse:
    emenda = get_object_or_404(PropostaDeEmendaDoCiclo, sqid=emenda_sqid)
    raise NotImplementedError


@group_required(GrupoDeUsuario.GESTAO)
def adicionar_emenda(request: HttpRequest) -> HttpResponse:
    raise NotImplementedError


@group_required(GrupoDeUsuario.GESTAO)
def adicionar_emendas(request: HttpRequest) -> HttpResponse:
    raise NotImplementedError


@group_required(GrupoDeUsuario.GESTAO)
def adicionar_parlamentar(request: HttpRequest) -> HttpResponse:
    raise NotImplementedError


@group_required(GrupoDeUsuario.GESTAO)
def adicionar_parlamentares(request: HttpRequest) -> HttpResponse:
    raise NotImplementedError


@group_required(GrupoDeUsuario.GESTAO)
def ver_parlamentar(request: HttpRequest, id: int) -> HttpResponse:
    parlamentar = get_object_or_404(ParlamentarDoCiclo, id=id)
    # se tiver ?edit...
    raise NotImplementedError


@group_required(GrupoDeUsuario.GESTAO)
def adicionar_gestor(request: HttpRequest) -> HttpResponse:
    raise NotImplementedError
