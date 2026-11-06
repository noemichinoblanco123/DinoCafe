from rest_framework import status, viewsets
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework_simplejwt.views import TokenObtainPairView
from rest_framework.views import APIView

from dinocafe.permissions import EsAdministrador
from .models import Usuario
from .serializers import LoginSerializer, UsuarioGestionSerializer


class LoginView(TokenObtainPairView):
    serializer_class = LoginSerializer


class UsuarioActualView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response({
            "username": request.user.username,
            "rol": request.user.rol,
        })


class UsuarioGestionViewSet(viewsets.ModelViewSet):
    serializer_class = UsuarioGestionSerializer
    permission_classes = [EsAdministrador]
    queryset = Usuario.objects.order_by("username")

    def perform_update(self, serializer):
        usuario = serializer.instance
        datos = serializer.validated_data
        if usuario.pk == self.request.user.pk and (
            datos.get("is_active") is False
            or datos.get("rol", usuario.rol) != "administrador"
        ):
            raise ValidationError({"usuario": "No puedes desactivar ni quitarte el rol de administrador."})
        self._validar_ultimo_administrador(usuario, datos)
        serializer.save()

    def destroy(self, request, *args, **kwargs):
        usuario = self.get_object()
        if usuario.pk == request.user.pk:
            raise ValidationError({"usuario": "No puedes desactivar tu propia cuenta."})
        self._validar_ultimo_administrador(usuario, {"is_active": False})
        usuario.is_active = False
        usuario.save(update_fields=["is_active"])
        return Response(status=status.HTTP_204_NO_CONTENT)

    def _validar_ultimo_administrador(self, usuario, datos):
        va_a_desactivar = datos.get("is_active") is False
        va_a_cambiar_rol = datos.get("rol", usuario.rol) != "administrador"
        if usuario.rol == "administrador" and usuario.is_active and (va_a_desactivar or va_a_cambiar_rol):
            quedan_administradores = Usuario.objects.filter(
                rol="administrador",
                is_active=True,
            ).exclude(pk=usuario.pk).exists()
            if not quedan_administradores:
                raise ValidationError({"usuario": "Debe quedar al menos un administrador activo."})
