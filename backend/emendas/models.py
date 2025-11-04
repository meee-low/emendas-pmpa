from django.db import models
from django.core.exceptions import ValidationError
from django.core.validators import RegexValidator
import typing
from typing import Self
from decimal import Decimal

if typing.TYPE_CHECKING:
    from django.db.models import ForeignKey, ManyToManyField
    from django.contrib.auth.models import User

validador_alfanumerico = RegexValidator(r'^[0-9a-zA-Z_-]*$', "Apenas caracteres alfanuméricos, _ e - são permitidos nesse campo.")

class Ciclo(models.Model):
    nome = models.CharField(max_length=20, unique=True)
    data_comeco = models.DateField()
    data_fim = models.DateField()
    ativo = models.BooleanField()
    criado_em = models.DateTimeField(auto_now_add=True)


class PropostaDeEmenda(models.Model):
    titulo = models.CharField(max_length=200, unique=True)
    descricao = models.TextField()
    valor = models.DecimalField(max_digits=12,decimal_places=2)
    ativo = models.BooleanField(default=True)
    tags: "ManyToManyField[Tag, Self]" = models.ManyToManyField(
        "Tag", blank=True, related_name="emendas"
    )
    data_criacao = models.DateTimeField(auto_now_add=True, name="Data de Criação")
    data_atualizacao = models.DateTimeField(auto_now=True, name="Data de Atualização")

    def __str__(self):
        return self.titulo

    class Meta:
        verbose_name = "Proposta de Emenda do Ciclo"
        verbose_name_plural = "Propostas de Emendas do Ciclo"


class PropostaDeEmendaDoCiclo(models.Model):
    proposta_de_emenda = models.ForeignKey(PropostaDeEmenda, on_delete=models.CASCADE)
    ciclo = models.ForeignKey(Ciclo, on_delete=models.CASCADE)
    

    def total_ja_investido(self) -> Decimal:
        total = Decimal(Transacao.objects.filter(emenda=self, ciclo_id=self.ciclo_id).aggregate(
            models.Sum("valor_investido")
        )["valor_investido__sum"] or 0)
        return total

    class Meta:
        verbose_name = "Proposta de Emenda do Ciclo"
        verbose_name_plural = "Propostas de Emendas do Ciclo"
        unique_together = ["proposta_de_emenda", "ciclo"]

class ParlamentarDoCiclo(models.Model):
    usuario: "ForeignKey[User]" = models.ForeignKey(
        "auth.User", on_delete=models.CASCADE, name="Usuário"
    )
    ciclo = models.ForeignKey(Ciclo, on_delete=models.CASCADE)
    verba_inicial = models.DecimalField(max_digits=12, decimal_places=2)

    def __str__(self):
        return f"{self.usuario} ({self.ciclo})"

    def saldo_verba(self) -> Decimal:
        total_investido = Decimal(
            Transacao.objects.filter(parlamentar=self, ciclo_id=self.ciclo_id).aggregate(
                models.Sum("valor_investido")
            )["valor_investido__sum"]
            or 0
        )
        return self.verba_inicial - total_investido

    class Meta:
        verbose_name_plural= "Parlamentares do Ciclo"


class Transacao(models.Model):
    emenda = models.ForeignKey(PropostaDeEmendaDoCiclo, on_delete=models.PROTECT)
    parlamentar = models.ForeignKey(ParlamentarDoCiclo, on_delete=models.PROTECT)
    ciclo = models.ForeignKey(Ciclo, on_delete=models.PROTECT)
    valor_investido = models.DecimalField(max_digits=12, decimal_places=2)
    tipo = models.CharField(max_length=20, blank=False)
    obs = models.TextField(blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)

    def clean(self):
        emenda_ciclo = self.emenda.ciclo_id 
        parlamentar_ciclo = self.parlamentar.ciclo_id
        if emenda_ciclo != parlamentar_ciclo:
            raise ValidationError("Inconsistência: Ciclo da emenda não corresponde ao ciclo do Parlamentar.")
        if emenda_ciclo != self.ciclo_id:
            raise ValidationError("Inconsistência: Ciclo da Transação não corresponde ao ciclo do Parlamentar e da Emenda.")
    
    class Meta:
        verbose_name = "Transação"
        verbose_name_plural = "Transações"


class Tag(models.Model):
    nome = models.CharField(max_length=100, unique=True, validators=[validador_alfanumerico])
    pai: "ForeignKey[Self | None]"= typing.cast(
        models.ForeignKey[Self|None],
        models.ForeignKey(
            "self",
            on_delete=models.CASCADE,
            null=True,
            blank=True,
            related_name="subtags",
        ),
    )

    def hierarquia(self) -> str:
        cur = self
        s = f"{cur.nome}"
        while cur.pai is not None:
            cur = cur.pai
            s = f"{cur.nome}/{s}"
        return s


    def __str__(self):
        return self.nome
