from django import forms

from .models import ParlamentarDoCiclo, Ciclo


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
    class Meta:
        model = ParlamentarDoCiclo
        fields = "__all__"


class CicloForm(forms.ModelForm):
    class Meta:
        model = Ciclo
        fields = "__all__"
        widgets = {
            "data_comeco": forms.DateInput(attrs={"type": "date"}),
            "data_fim": forms.DateInput(attrs={"type": "date"}),
        }

    def __init__(self, *args, **kwargs) -> None:
        res = super().__init__(*args, **kwargs)
        self.fields["ativo"].initial = True
        return res
