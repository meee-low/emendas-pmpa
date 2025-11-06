from django.core.management.base import BaseCommand
from faker import Faker
from decimal import Decimal
import random

from django.contrib.auth.models import User
from emendas.models import (
    Ciclo,
    Tag,
    PropostaDeEmenda,
    PropostaDeEmendaDoCiclo,
    ParlamentarDoCiclo,
    Transacao,
)


fake = Faker("pt_BR")


class Command(BaseCommand):
    help = "Seed database with fake data"

    def handle(self, *args, **options):
        self.stdout.write("Generating fake data...")

        # Tags
        tags = []
        for i in range(10):
            tag, _ = Tag.objects.get_or_create(nome=fake.unique.slug())
            tags.append(tag)

        # Ciclos
        ciclos = []
        for _ in range(3):
            start = fake.date_this_year()
            end = fake.date_between(start, "+90d")
            ciclo = Ciclo.objects.create(
                nome=fake.unique.word(),
                data_comeco=start,
                data_fim=end,
                ativo=fake.boolean(),
            )
            ciclos.append(ciclo)

        # Users
        users = []
        for _ in range(5):
            u = User.objects.create_user(
                username=fake.unique.user_name(),
                email=fake.email(),
                password="123456",
            )
            users.append(u)

        # Parlementares por ciclo
        parlamentares = []
        for user in users:
            for ciclo in ciclos:
                parlamentares.append(
                    ParlamentarDoCiclo.objects.create(
                        usuario=user,
                        ciclo=ciclo,
                        verba_inicial=random.randint(10_000, 200_000),
                    )
                )

        # Propostas
        propostas = []
        for _ in range(10):
            p = PropostaDeEmenda.objects.create(
                titulo=fake.unique.sentence(),
                descricao=fake.paragraph(),
                valor=Decimal(random.randint(1_000, 500_000)),
            )
            p.tags.set(random.sample(tags, random.randint(0, 3)))  # M2M
            propostas.append(p)

        # Propostas do Ciclo
        propostas_ciclo = []
        for proposta in propostas:
            ciclo = random.choice(ciclos)
            propostas_ciclo.append(
                PropostaDeEmendaDoCiclo.objects.create(
                    proposta_de_emenda=proposta,
                    ciclo=ciclo,
                )
            )

        # Transações
        for _ in range(30):
            pc = random.choice(propostas_ciclo)
            ciclo = pc.ciclo
            parl = random.choice(
                ParlamentarDoCiclo.objects.filter(ciclo=ciclo)
            )

            Transacao.objects.create(
                emenda=pc,
                parlamentar=parl,
                ciclo=ciclo,
                valor_investido=Decimal(random.randint(1_000, 20_000)),
                tipo=random.choice(["DEPOSITO", "SAQUE"]),
                obs=fake.sentence(),
            )

        self.stdout.write(self.style.SUCCESS("✅ Fake data successfully generated!"))