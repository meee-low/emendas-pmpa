import typing
from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpRequest, HttpResponse
from django.db.models import Sum, Prefetch
from django.contrib.auth.models import User

from emendas.decorators import group_required
from emendas.groups import GrupoDeUsuario, get_grupos_do_usuario
from emendas.models import Ciclo, ParlamentarDoCiclo, PropostaDeEmendaDoCiclo, Tag


def home_page(request: HttpRequest) -> HttpResponse:
    user = request.user
    if not user.is_authenticated:
        return redirect("login")

    grupos_do_user = get_grupos_do_usuario(typing.cast(User, user))

    # usuário está autenticado
    if GrupoDeUsuario.GESTAO in grupos_do_user or user.is_superuser:
        return redirect("gestao_home")

    if GrupoDeUsuario.PARLAMENTAR in grupos_do_user:
        return redirect("parlamentar_dashboard")

    return render(request, "home/default_home.html")


@group_required(GrupoDeUsuario.GESTAO)
def gestao_home(request: HttpRequest) -> HttpResponse:
    return render(request, "gestao/gestao_home.html")


@group_required(GrupoDeUsuario.PARLAMENTAR)
def parlamentar_dashboard(request: HttpRequest) -> HttpResponse:
    return render(request, "parlamentar/parlamentar_dashboard.html")


def catalogos(request: HttpRequest) -> HttpResponse:
    grupos_do_user = get_grupos_do_usuario(typing.cast(User, request.user))

    ciclos = list(Ciclo.objects.all().order_by("-data_comeco", "-data_fim", "nome"))
    if GrupoDeUsuario.PARLAMENTAR in grupos_do_user:
        ciclos_do_parlamentar = ParlamentarDoCiclo.objects.filter(
            usuario=request.user
        ).values_list("ciclo_id", flat=True)
        ciclos_ativos = [c for c in ciclos if c.id in ciclos_do_parlamentar]
        outros_ciclos = [c for c in ciclos if c.id not in ciclos_do_parlamentar]
    else:
        ciclos_ativos = []
        outros_ciclos = ciclos

    return render(
        request,
        "emendas/catalogos.html",
        {
            "grupos_do_user": grupos_do_user,
            "ciclos_ativos": ciclos_ativos,
            "outros_ciclos": outros_ciclos,
        },
    )


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
