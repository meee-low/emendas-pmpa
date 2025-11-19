from django.db.models.signals import post_migrate
from django.contrib.auth.models import Group
from django.dispatch import receiver

from . import groups

@receiver(post_migrate)
def create_default_groups(sender, **kwargs):
    # Evita rodar em apps desnecessários
    if sender.name != "emendas":  
        return

    for group_name in list(groups.GrupoDeUsuario):
        Group.objects.get_or_create(name=group_name.value)
