from django.core.exceptions import PermissionDenied
from django.shortcuts import redirect
from django.http import HttpRequest, HttpResponse

from typing import Callable, TypeVar, ParamSpec
from functools import wraps

P = ParamSpec("P")
R = TypeVar("R", bound=HttpResponse)


def group_required(group_name: str):
    def decorator(view_func: Callable[P, R]) -> Callable[P, R]:
        @wraps(view_func)
        def _wrapped_view(*args: P.args, **kwargs: P.kwargs) -> R:
            # Expect the first argument to be request
            request = args[0]
            assert isinstance(request, HttpRequest), (
                "First argument to a Django view must be HttpRequest"
            )

            user = request.user
            if not user.is_authenticated:
                return redirect("login")  # type: ignore

            if not (
                user.is_superuser or user.groups.filter(name=str(group_name)).exists()
            ):
                raise PermissionDenied

            return view_func(*args, **kwargs)

        return _wrapped_view

    return decorator
