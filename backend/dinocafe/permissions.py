"""Permisos reutilizables de la capa de negocio de DinoCafé."""
from rest_framework.permissions import BasePermission


class EsAdministrador(BasePermission):
    message = "Solo el administrador puede realizar esta operación."

    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated and request.user.rol == "administrador")


class EsCajero(BasePermission):
    message = "Solo el cajero puede registrar pedidos y pagos."

    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated and request.user.rol == "cajero")


class EsCajeroOAdministrador(BasePermission):
    message = "Solo caja o administración puede realizar esta operación."

    def has_permission(self, request, view):
        return bool(
            request.user
            and request.user.is_authenticated
            and request.user.rol in {"administrador", "cajero"}
        )
