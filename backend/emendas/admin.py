from django.contrib import admin
from .models import ParlamentarDoCiclo, PropostaDeEmenda, PropostaDeEmendaDoCiclo, Tag, Transacao, Ciclo

# Register your models here.
admin.site.register(PropostaDeEmenda)
admin.site.register(PropostaDeEmendaDoCiclo)
admin.site.register(Tag)
admin.site.register(ParlamentarDoCiclo)
admin.site.register(Transacao)
admin.site.register(Ciclo)