from enum import StrEnum
from django.contrib.auth.models import User


class GrupoDeUsuario(StrEnum):
    GESTAO = "Gestão"
    PARLAMENTAR = "Parlamentar"


def get_grupos_do_usuario(user: User) -> list[str]:
    if user.is_authenticated:
        return list(user.groups.values_list("name", flat=True))
    return []
