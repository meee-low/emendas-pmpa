from django import template

register = template.Library()


@register.filter
def div(a: float, b: float) -> float:
    return a / b if b else 0


@register.filter
def mul(a: float, b: float) -> float:
    return a * b

@register.filter
def minus(a: float, b: float) -> float:
    return a - b
