from django.db import models
from django.db.models import QuerySet
from django.template.defaultfilters import slugify
from django.core.exceptions import ValidationError
from django.core.validators import RegexValidator

from django_sqids import SqidsField, shuffle_alphabet

import uuid6

import typing
from typing import Self, override

if typing.TYPE_CHECKING:
    from django.db.models import ForeignKey, ManyToManyField
    from django.contrib.auth.models import User

validador_alfanumerico = RegexValidator(
    r"^[0-9a-zA-Z_-]*$",
    "Apenas caracteres alfanuméricos, _ e - são permitidos nesse campo.",
)


class Ciclo(models.Model):
    id: int
    nome = models.CharField(max_length=20, unique=True)
    data_comeco = models.DateField(verbose_name="Data do Começo")
    data_fim = models.DateField(verbose_name="Data do Fim")
    ativo = models.BooleanField()
    criado_em = models.DateTimeField(auto_now_add=True)

    def __str__(self) -> str:
        return self.nome


class PropostaDeEmenda(models.Model):
    _SLUG_LEN = 50
    sqid = SqidsField(alphabet=shuffle_alphabet(seed="PropostaDeEmenda"))
    titulo = models.CharField(max_length=200, unique=True, verbose_name="Título")
    slug = models.SlugField(
        max_length=_SLUG_LEN, unique=True, blank=True, editable=False
    )
    descricao = models.TextField(verbose_name="Descrição")
    valor = models.PositiveIntegerField()
    ativo = models.BooleanField(default=True)
    tags: "ManyToManyField[Tag, Self]" = models.ManyToManyField(
        "Tag", blank=True, related_name="emendas"
    )
    data_criacao = models.DateTimeField(
        auto_now_add=True, verbose_name="Data de Criação"
    )
    data_atualizacao = models.DateTimeField(
        auto_now=True, verbose_name="Data de Atualização"
    )

    def __str__(self):
        return self.titulo

    @override
    def save(self, *args, **kwargs):  # pyright: ignore[reportMissingParameterType, reportUnknownParameterType]
        self.slug = slugify(f"{self.sqid}-{slugify(self.titulo)}")[: self._SLUG_LEN]
        super().save(*args, **kwargs)  # pyright: ignore[reportUnknownArgumentType]

    class Meta:
        verbose_name = "Proposta de Emenda"
        verbose_name_plural = "Propostas de Emendas"


class PropostaDeEmendaDoCiclo(models.Model):
    sqid = SqidsField(alphabet=shuffle_alphabet(seed="PropostaDeEmendaDoCiclo"))
    proposta_de_emenda = models.ForeignKey(PropostaDeEmenda, on_delete=models.CASCADE)
    proposta_de_emenda_id: int
    ciclo = models.ForeignKey(Ciclo, on_delete=models.CASCADE)
    ciclo_id: int

    def total_ja_investido(self) -> int:
        if hasattr(self, "total_investido"):
            return self.total_investido or 0  # type: ignore

        total = int(
            Transacao.objects.filter(emenda=self, ciclo_id=self.ciclo_id).aggregate(
                total=models.Sum("valor_investido")
            )["total"]
            or 0
        )

        return total

    def valor_restante(self) -> int:
        return self.proposta_de_emenda.valor - self.total_ja_investido()

    def __str__(self) -> str:
        return f"Emenda {self.proposta_de_emenda_id} ({self.ciclo})"

    class Meta:
        verbose_name = "Proposta de Emenda do Ciclo"
        verbose_name_plural = "Propostas de Emendas do Ciclo"
        unique_together = ["proposta_de_emenda", "ciclo"]


class ParlamentarDoCiclo(models.Model):
    class Esfera(models.TextChoices):
        FEDERAL = "FEDERAL", "Federal"
        ESTADUAL = "ESTADUAL", "Estadual"
        MUNICIPAL = "MUNICIPAL", "Municipal"

    usuario: "ForeignKey[User]" = models.ForeignKey(
        "auth.User", on_delete=models.CASCADE, verbose_name="Usuário"
    )
    ciclo = models.ForeignKey(Ciclo, on_delete=models.CASCADE)
    ciclo_id: int
    esfera = models.CharField(
        max_length=20, blank=False, choices=Esfera.choices
    )
    verba_inicial = models.PositiveIntegerField()

    def __str__(self):
        return f"{self.usuario} ({self.ciclo})"

    def saldo_verba(self) -> int:
        total_investido = int(
            Transacao.objects.filter(
                parlamentar=self, ciclo_id=self.ciclo_id
            ).aggregate(models.Sum("valor_investido"))["valor_investido__sum"]
            or 0
        )
        # TODO: garantir que o saldo não esteja negativo
        saldo = self.verba_inicial - total_investido
        assert saldo >= 0
        return saldo

    class Meta:
        verbose_name = "Parlamentar do Ciclo"
        verbose_name_plural = "Parlamentares do Ciclo"
        unique_together = ["ciclo", "usuario"]


class Transacao(models.Model):
    class Tipo(models.TextChoices):
        INVESTIMENTO = "INVESTIMENTO", "Investimento"
        CANCELAMENTO = "CANCELAMENTO", "Cancelamento"

    id = models.UUIDField(primary_key=True, default=uuid6.uuid7, editable=False)
    emenda = models.ForeignKey(
        PropostaDeEmendaDoCiclo, on_delete=models.PROTECT, related_name="transacoes"
    )
    emenda_id: int
    parlamentar = models.ForeignKey(
        ParlamentarDoCiclo, on_delete=models.PROTECT, related_name="transacoes"
    )
    parlamentar_id: int
    ciclo = models.ForeignKey(
        Ciclo, on_delete=models.PROTECT, related_name="transacoes"
    )
    ciclo_id: int
    valor_investido = models.IntegerField()  # Pode ser negativo
    tipo = models.CharField(
        max_length=20, blank=False, choices=Tipo.choices, default=Tipo.INVESTIMENTO
    )
    transacao_cancelada: "ForeignKey[Self | None]" = models.ForeignKey(
        "self",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="cancelamentos",
        help_text="Se esta for uma transação de cancelamento, aponta para a transação original.",
    )
    cancelamentos: "QuerySet[Self]"
    obs = models.TextField(blank=True, verbose_name="Observação")
    timestamp = models.DateTimeField(auto_now_add=True)

    def clean(self):
        emenda_ciclo = self.emenda.ciclo_id
        parlamentar_ciclo = self.parlamentar.ciclo_id
        if emenda_ciclo != parlamentar_ciclo:
            raise ValidationError(
                "Inconsistência: Ciclo da emenda não corresponde ao ciclo do Parlamentar."
            )
        if emenda_ciclo != self.ciclo_id:
            raise ValidationError(
                "Inconsistência: Ciclo da Transação não corresponde ao ciclo do Parlamentar e da Emenda."
            )

    class Meta:
        verbose_name = "Transação"
        verbose_name_plural = "Transações"


class Tag(models.Model):
    sqid = SqidsField()
    nome = models.CharField(max_length=100, validators=[validador_alfanumerico])
    pai: "ForeignKey[Self | None]" = typing.cast(
        models.ForeignKey[Self | None],
        models.ForeignKey(
            "self",
            on_delete=models.CASCADE,
            null=True,
            blank=True,
            related_name="subtags",
        ),
    )

    def _debug_hierarquia(self) -> str:
        # WARN: Problema de N+1, use com cautela, apenas para debug. No futuro, implementar isso de um jeito melhor
        cur = self
        s = f"{cur.nome}"
        while cur.pai is not None:
            cur = cur.pai
            s = f"{cur.nome}/{s}"
        return s

    def __str__(self):
        return self.nome
