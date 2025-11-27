from datetime import datetime, timedelta
from multiprocessing import Value
from emendas.models import ParlamentarDoCiclo, PropostaDeEmendaDoCiclo, Transacao
from django.contrib.auth.models import User
from django.db.models import Sum
from enum import StrEnum, auto


def investir(
    emenda: PropostaDeEmendaDoCiclo, parlamentar: ParlamentarDoCiclo, quantia: int
) -> Transacao:
    if emenda.ciclo_id != parlamentar.ciclo_id:
        raise ValueError("Parlamentar não pertence a esse ciclo de emendas")

    if quantia < 0:
        raise ValueError("Não é possível investir uma quantia negativa.")

    if quantia > parlamentar.saldo_verba():
        raise ValueError("Saldo insuficiente")

    if quantia > emenda.valor_restante():
        raise ValueError("Investimento excede o valor máximo da emenda.")

    # TODO: checar se obedece o minimo de investimento naquele ciclo

    return Transacao.objects.create(
        emenda=emenda,
        parlamentar=parlamentar,
        ciclo=emenda.ciclo_id,
        valor_investido=quantia,
        tipo="INVESTIMENTO",
    )


class MotivosDeCancelamento(StrEnum):
    MANUAL_PELO_USUARIO = auto()
    MANUAL_PELA_GESTAO = auto()
    AUTOMATICO = auto()


def cancelar_transacao(
    transacao: Transacao, motivo: MotivosDeCancelamento, mensagem: str | None = None
) -> Transacao:
    if datetime.now() - transacao.timestamp > timedelta(days=7):
        raise ValueError(
            "Essa transação é antiga demais para ser cancelada normalmente. "
            "Por favor, contate o administrador do site."
        )

    if transacao.cancelamentos.exists():
        raise ValueError("Esta transação já foi cancelada anteriormente.")

    if (
        transacao.transacao_cancelada is not None
        or transacao.tipo == Transacao.Tipo.CANCELAMENTO[0]
    ):
        raise ValueError(
            "Esta transação já é um cancelamento e cancelamentos não podem ser cancelados."
        )

    investido_na_emenda_por_essa_pessoa = (
        Transacao.objects.filter(
            parlamentar=transacao.parlamentar,
            emenda=transacao.emenda,
            ciclo=transacao.ciclo,
        ).aggregate(total=Sum("valor_investido"))["total"]
        or 0
    )

    if investido_na_emenda_por_essa_pessoa < transacao.valor_investido:
        raise ValueError(
            "Não é possível cancelar: essa pessoa não possui fundos suficientes investidos nessa Emenda nesse Ciclo"
        )

    obs = f"Cancela transação {transacao.pk}: {motivo}'"
    if mensagem:
        obs += f" ({mensagem})"

    cancelamento = Transacao.objects.create(
        emenda=transacao.emenda,
        parlamentar=transacao.parlamentar,
        ciclo=transacao.emenda.ciclo_id,
        valor_investido=-transacao.valor_investido,
        tipo=Transacao.Tipo.CANCELAMENTO,
        transacao_cancelada=transacao,
        obs=obs,
    )
    return cancelamento
