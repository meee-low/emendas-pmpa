from django import forms

from .models import ParlamentarDoCiclo

class EmendasBulkForm(forms.Form):
    texto = forms.CharField(
        widget=forms.Textarea(attrs={"rows": 10, "cols": 80}),
        help_text="Copie do Excel e cole as emendas aqui. Uma por linha, no formato 'Título|Descrição'",
    )

class ParlamentaresBulkForm(forms.Form):
    texto = forms.CharField(
        widget=forms.Textarea(attrs={"rows": 10, "cols": 80}),
        help_text="Copie do Excel e cole os parlamentares aqui. Um por linha, no formato 'Nome|Email|Nível(Municipal, Estadual ou Federal)|Ciclo'",
    )

class ParlamentarForm(forms.ModelForm):
    pass

    class __meta__: 
        model = ParlamentarDoCiclo
