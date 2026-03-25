import csv
from http import HTTPStatus
import typing
from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpRequest, HttpResponse
from django.db.models import Sum, Prefetch, F
from django.db.models.functions import Coalesce
from django.contrib.auth.models import User
from django.views.decorators.http import require_POST, require_GET


from emendas.decorators import group_required
from emendas.domain import investir
from emendas.forms import EmendasBulkForm, ParlamentaresBulkForm
from emendas.groups import GrupoDeUsuario, get_grupos_do_usuario
from emendas.models import (
    Ciclo,
    ParlamentarDoCiclo,
    PropostaDeEmenda,
    Tag,
    Transacao,
)


def home_page(request: HttpRequest) -> HttpResponse:
    user = request.user
    if not user.is_authenticated:
        return redirect("login")

    grupos_do_user = get_grupos_do_usuario(typing.cast(User, user))

    # usuário está autenticado
    if GrupoDeUsuario.GESTAO in grupos_do_user or user.is_superuser:
        return gestao_home(request)

    if GrupoDeUsuario.PARLAMENTAR in grupos_do_user:
        return redirect("parlamentar_dashboard")

    return render(request, "home/default_home.html")


@require_GET
@group_required(GrupoDeUsuario.GESTAO)
def gestao_home(request: HttpRequest) -> HttpResponse:
    ciclos = list(Ciclo.objects.order_by("-data_comeco", "-data_fim"))
    if len(ciclos) == 0:
        return render(
            request,
            "emendas/gestao/gestao_home.html",
        )
    ciclo_id_str = request.GET.get("ciclo")
    if not ciclo_id_str:
        ciclo_id = ciclos[0].id
    else:
        ciclo_id = int(ciclo_id_str)

    class EmendaComCiclos(typing.TypedDict):
        emenda: PropostaDeEmenda
        tags: list[Tag]

    emendas_queryset = (
        PropostaDeEmenda.objects.all().select_related("ciclo").filter(ciclo_id=ciclo_id)
    )

    emendas: list[EmendaComCiclos] = [
        EmendaComCiclos(
            emenda=emenda,
            tags=list(emenda.tags.all()),
        )
        for emenda in emendas_queryset
    ]

    parlamentares = ParlamentarDoCiclo.objects.filter(ciclo_id=ciclo_id).select_related(
        "usuario"
    )

    transacoes = (
        Transacao.objects.filter(ciclo_id=ciclo_id)
        .select_related(
            "parlamentar",
            "parlamentar__usuario",
            "emenda",
            "ciclo",
        )
        .order_by("-timestamp")
    )

    return render(
        request,
        "emendas/gestao/gestao_home.html",
        {
            "ciclo_selecionado_id": ciclo_id,
            "ciclos": ciclos,
            "emendas": emendas,
            "parlamentares": parlamentares,
            "transacoes": transacoes,
        },
    )


@group_required(GrupoDeUsuario.PARLAMENTAR)
def parlamentar_dashboard(request: HttpRequest) -> HttpResponse:
    return render(request, "parlamentar/parlamentar_dashboard.html")


def em_construcao(request: HttpRequest) -> HttpResponse:
    return render(request, "em_construcao.html")


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
        PropostaDeEmenda.objects.filter(ciclo=ciclo)
        .prefetch_related(Prefetch("tags", queryset=Tag.objects.all()))
        .annotate(total_investido=Sum("transacoes__valor_investido"))
    )

    tags = {
        tag_id: nome
        for tag_id, nome in (
            emendas.values_list("tags__id", "tags__nome")
            .distinct()
            .order_by("tags__nome")
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
        ciclo: Ciclo

    emendas_queryset = (
        PropostaDeEmenda.objects.all()
        .select_related("ciclo")
        .prefetch_related(
            Prefetch("tags", queryset=Tag.objects.all()),
        )
    )

    emendas: list[EmendaComCiclos] = [
        EmendaComCiclos(
            emenda=emenda,
            tags=list(emenda.tags.all()),
            ciclo=emenda.ciclo,
        )
        for emenda in emendas_queryset
    ]

    return render(
        request,
        "emendas/emendas.html",
        {"emendas_e_ciclos": emendas, "grupos_do_user": get_grupos_do_usuario(request.user)},
    )


def emenda_do_ciclo(request: HttpRequest, emenda_sqid: str) -> HttpResponse:
    emenda = get_object_or_404(PropostaDeEmenda, sqid=emenda_sqid)
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
@require_POST
def investir_em_emenda(request: HttpRequest, emenda_sqid: str) -> HttpResponse:
    emenda = get_object_or_404(PropostaDeEmenda, sqid=emenda_sqid)

    parlamentar = ParlamentarDoCiclo.objects.filter(
        ciclo_id=emenda.ciclo_id, usuario=request.user
    ).first()
    if parlamentar is None:
        return HttpResponse(status=HTTPStatus.FORBIDDEN)

    try:
        quantia = int(request.POST.get("quantia", 0))
        if quantia <= 0:
            return HttpResponse(status=HTTPStatus.BAD_REQUEST)
    except Exception as _e:
        return HttpResponse(status=HTTPStatus.BAD_REQUEST)
    try:
        _transacao = investir(emenda, parlamentar, quantia)
    except ValueError as _e:
        return HttpResponse(status=HTTPStatus.UNPROCESSABLE_ENTITY)
    return HttpResponse(status=HTTPStatus.CREATED)


@group_required(GrupoDeUsuario.GESTAO)
def adicionar_emenda(request: HttpRequest) -> HttpResponse:
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


@require_GET
def transacoes_do_parlamentar(
    request: HttpRequest, parlamentar_id: int | None = None, user_id: int | None = None
) -> HttpResponse:
    if parlamentar_id is None:
        if user_id is None:
            user = request.user
            if not user.is_authenticated:
                return HttpResponse(status=404)
        else:
            user = get_object_or_404(User, id=user_id)
    else:
        user = None

    qs = Transacao.objects.select_related(
        "parlamentar",
        "parlamentar__usuario",
        "emenda",
        "emenda__ciclo",
        "ciclo",
    )

    if parlamentar_id:
        qs = qs.filter(parlamentar_id=parlamentar_id)
    else:
        qs = qs.filter(parlamentar__usuario=user)

    transacoes = list(qs)

    if user:
        alvo = user
    elif transacoes:
        alvo = transacoes[0].parlamentar.usuario
    else:
        p = (
            ParlamentarDoCiclo.objects.select_related("usuario")
            .filter(id=parlamentar_id)
            .first()
        )
        if p is None:
            return HttpResponse(status=HTTPStatus.NOT_FOUND)
        alvo = p.usuario

    return render(
        request,
        "emendas/lista_de_transacoes.html",
        {"transacoes": transacoes, "alvo": alvo},
    )


def parlamentares(request: HttpRequest) -> HttpResponse:
    parlamentares = (
        ParlamentarDoCiclo.objects.select_related("usuario", "ciclo")
        .annotate(
            total_investido=Coalesce(
                Sum(
                    "transacoes__valor_investido",
                ),
                0,
            ),
            saldo_restante=F("verba_inicial")
            - Coalesce(Sum("transacoes__valor_investido"), 0),
        )
        .order_by("-ciclo__data_comeco", "usuario__username")
    )
    return render(
        request,
        "emendas/parlamentares/lista_de_parlamentares.html",
        {"parlamentares": parlamentares},
    )


@group_required(GrupoDeUsuario.GESTAO)
def adicionar_parlamentar_bulk(request: HttpRequest) -> HttpResponse:
    def processar_form(
        texto: str,
    ) -> tuple[list[tuple[ParlamentarDoCiclo, str]], list[str]]:
        try:
            linhas = bulk_processar_excel(texto)
        except Exception as e:
            return [], [f"{e}"]
        objetos: list[tuple[ParlamentarDoCiclo, str]] = []
        erros: list[str] = []
        for i, linha in enumerate(linhas, start=1):
            if len(linha) != 4:
                erros.append(
                    f"Linha {i}: Número de colunas incompatível. Encontradas {len(linha)} colunas."
                )
                continue
            username, email, esfera, ciclo = linha
            try:
                user = User(
                    username=username,
                    password="",  # TODO: senha aleatória
                    email=email,
                )
                esfera_dict = {
                    "federal": ParlamentarDoCiclo.Esfera.FEDERAL,
                    "estadual": ParlamentarDoCiclo.Esfera.ESTADUAL,
                    "municipal": ParlamentarDoCiclo.Esfera.MUNICIPAL,
                }
                parlamentar = ParlamentarDoCiclo(
                    usuario=user, esfera=esfera_dict[esfera.strip().lower()]
                )
                objetos.append((parlamentar, ciclo))
            except Exception as e:
                erros.append(f"Linha {i}: Erro ao ler os dados colados: {e}")
        return objetos, erros

    erros: list[str] = []
    if request.method == "POST":
        form = ParlamentaresBulkForm(request.POST)
        if form.is_valid():
            texto = form.cleaned_data["texto"]
            objetos, erros = processar_form(texto)
            if not erros:
                ciclos = Ciclo.objects.filter(nome__in=[c for _, c in objetos])
                mapa_ciclos = {c.nome: c for c in ciclos}
                for i, (parlamentar, nome_ciclo) in enumerate(objetos):
                    # TODO: error checking
                    try:
                        ciclo = mapa_ciclos[nome_ciclo]
                        user = parlamentar.usuario
                        user.save()
                        parlamentar = ParlamentarDoCiclo(usuario=user, ciclo=ciclo)
                        parlamentar.save()
                    except KeyError:
                        erros.append(
                            f"Linha {i}: Ciclo com o nome {nome_ciclo} não encontrado."
                        )

                if not erros:
                    return redirect("parlamentares")
        return render(
            request,
            "emendas/parlamentares/adicionar_em_massa.html",
            {"form": form, "erros": erros},
        )

    elif request.method == "GET":
        params = request.GET
        # pprint(params)
        objetos = []
        if params and "HX-Request" in request.headers:  # HTMX Update
            form = ParlamentaresBulkForm(params)
            if form.is_valid():
                texto = form.cleaned_data["texto"]
                objetos, erros = processar_form(texto)
        else:
            form = ParlamentaresBulkForm()
        return render(
            request,
            "emendas/parlamentares/adicionar_em_massa.html",
            {"form": form, "objetos": objetos, "erros": erros},
        )
    else:
        return HttpResponse(status=405)
