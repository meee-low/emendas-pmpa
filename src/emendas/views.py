import csv
from pprint import pprint
from types import CellType
import typing
from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpRequest, HttpResponse
from django.db.models import Sum, Prefetch
from django.contrib.auth.models import User
from django.urls import is_valid_path

from emendas.decorators import group_required
from emendas.forms import EmendasBulkForm
from emendas.groups import GrupoDeUsuario, get_grupos_do_usuario
from emendas.models import (
    Ciclo,
    ParlamentarDoCiclo,
    PropostaDeEmenda,
    PropostaDeEmendaDoCiclo,
    Tag,
)


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


def emendas(request: HttpRequest) -> HttpResponse:
    class EmendaComCiclos(typing.TypedDict):
        emenda: PropostaDeEmenda
        tags: list[Tag]
        ciclos: list[Ciclo]

    emendas_queryset = PropostaDeEmenda.objects.all().prefetch_related(
        Prefetch(
            "propostadeemendadociclo_set",
            queryset=PropostaDeEmendaDoCiclo.objects.select_related("ciclo"),
        ),
        Prefetch("tags", queryset=Tag.objects.all()),
    )

    emendas: list[EmendaComCiclos] = [
        EmendaComCiclos(
            emenda=emenda,
            tags=list(emenda.tags.all()),
            ciclos=[pc.ciclo.nome for pc in emenda.propostadeemendadociclo_set.all()],
        )
        for emenda in emendas_queryset
    ]

    return render(
        request,
        "emendas/emendas.html",
        {"emendas": emendas, "grupos_do_user": get_grupos_do_usuario(request.user)},
    )


def emenda_do_ciclo(request: HttpRequest, emenda_sqid: str) -> HttpResponse:
    emenda = get_object_or_404(PropostaDeEmendaDoCiclo, sqid=emenda_sqid)
    return render(
        request,
        "emendas/emenda_do_ciclo.html",
        {"emenda": emenda},
    )


@group_required(GrupoDeUsuario.GESTAO)
def adicionar_emenda_bulk(request: HttpRequest) -> HttpResponse:
    def processar_form(texto: str) -> tuple[list[PropostaDeEmenda], list[str]]:
        try:
            linhas = bulk_processar_excel(texto)
        except Exception as e:
            return [], [f"{e}"]
        objetos: list[PropostaDeEmenda] = []
        erros: list[str] = []
        for i, linha in enumerate(linhas, start=1):
            if len(linha) != 3:
                erros.append(
                    f"Linha {i}: Número de colunas incompatível. Encontradas {len(linha)} colunas."
                )
                continue
            titulo, descricao, valor = linha
            try:
                emenda = PropostaDeEmenda(
                    titulo=titulo, descricao=descricao, valor=int(valor), ativo=True
                )
                objetos.append(emenda)
            except Exception as e:
                erros.append(
                    f"Linha {i}: Erro ao transformar dados em Proposta de Emenda: {e}"
                )
        return objetos, erros

    erros: list[str] = []
    if request.method == "POST":
        form = EmendasBulkForm(request.POST)
        if form.is_valid():
            texto = form.cleaned_data["texto"]
            objetos, erros = processar_form(texto)
            if not erros:
                PropostaDeEmenda.objects.bulk_create(objetos)
                return redirect("emendas")
        return render(
            request, "emendas/adicionar_em_massa.html", {"form": form, "erros": erros}
        )

    elif request.method == "GET":
        params = request.GET
        # pprint(params)
        objetos = []
        if params and "HX-Request" in request.headers:  # HTMX Update
            form = EmendasBulkForm(params)
            if form.is_valid():
                texto = form.cleaned_data["texto"]
                objetos, erros = processar_form(texto)
        else:
            form = EmendasBulkForm()
        return render(
            request,
            "emendas/adicionar_em_massa.html",
            {"form": form, "objetos": objetos, "erros": erros},
        )
    else:
        return HttpResponse(status=405)


def bulk_processar_excel(texto: str) -> list[list[str]]:
    dialect = csv.Sniffer().sniff(texto, delimiters="|\t;,")
    reader = csv.reader(texto.splitlines(), dialect)

    linhas: list[list[str]] = []
    for row in reader:
        if not any(row):
            continue
        linhas.append([cell.strip() for cell in row])
    return linhas


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
