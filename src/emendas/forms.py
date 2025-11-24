from django import forms


class EmendasBulkForm(forms.Form):
    texto = forms.CharField(
        widget=forms.Textarea(attrs={"rows": 10, "cols": 80}),
        help_text="Copie do Excel e cole as emendas aqui. Uma por linha, no formato 'Título|Descrição'",
    )