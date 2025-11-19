from django import template

register = template.Library()


@register.filter()
def num_br(valor: float, casas_decimais: int = 2) -> str:
    """
    Formata número com separadores brasileiros:
    - . separador de milhar
    - , separador decimal
    - decimal_places: número de casas depois da vírgula
    """
    try:
        valor = float(valor)
    except (TypeError, ValueError):
        return str(valor)

    # formata com número fixo de casas decimais usando o padrão EN
    formatted = f"{valor:,.{casas_decimais}f}"

    # troca separadores EN -> BR
    formatted = formatted.replace(",", "TEMP")  # milhares , → TEMP
    formatted = formatted.replace(".", ",")  # decimais . → ,
    formatted = formatted.replace("TEMP", ".")  # TEMP → .

    return formatted


@register.filter()
def to_float_point(valor: float, casas_decimais: int = 2) -> str:
    try:
        valor = float(valor)
    except (TypeError, ValueError):
        return str(valor)

    return f"{valor:,.{casas_decimais}f}"
