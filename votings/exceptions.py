"""Exception handling for the public API."""

from collections.abc import Mapping

from rest_framework import status
from rest_framework.exceptions import APIException, ValidationError
from rest_framework.views import exception_handler


class Conflict(APIException):
    status_code = status.HTTP_409_CONFLICT
    default_detail = "Операция недоступна в текущем состоянии."
    default_code = "conflict"


_FALLBACK_CODES = {
    status.HTTP_400_BAD_REQUEST: "bad_request",
    status.HTTP_401_UNAUTHORIZED: "not_authenticated",
    status.HTTP_403_FORBIDDEN: "permission_denied",
    status.HTTP_404_NOT_FOUND: "not_found",
    status.HTTP_405_METHOD_NOT_ALLOWED: "method_not_allowed",
    status.HTTP_415_UNSUPPORTED_MEDIA_TYPE: "unsupported_media_type",
    status.HTTP_429_TOO_MANY_REQUESTS: "throttled",
}

_FALLBACK_DETAILS = {
    status.HTTP_400_BAD_REQUEST: "Некорректный запрос.",
    status.HTTP_404_NOT_FOUND: "Объект не найден.",
}


def api_exception_handler(exc, context):
    """Convert handled DRF exceptions to one stable response format."""
    response = exception_handler(exc, context)
    if response is None:
        return None

    if isinstance(exc, ValidationError):
        response.data = {
            "code": "validation_error",
            "detail": "Ошибка валидации.",
            "errors": response.data,
        }
        return response

    code = None
    if hasattr(exc, "get_codes"):
        codes = exc.get_codes()
        if isinstance(codes, str):
            code = codes

    detail = None
    if isinstance(response.data, Mapping):
        detail = response.data.get("detail")

    response.data = {
        "code": code or _FALLBACK_CODES.get(response.status_code, "api_error"),
        "detail": str(
            detail or _FALLBACK_DETAILS.get(response.status_code, "Ошибка API.")
        ),
    }
    return response
