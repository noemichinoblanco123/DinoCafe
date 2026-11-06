from rest_framework import status, viewsets
from rest_framework.permissions import AllowAny, SAFE_METHODS
from rest_framework.response import Response

from dinocafe.permissions import EsAdministrador

from .models import Categoria, Producto
from .serializers import CategoriaSerializer, ProductoSerializer


class CategoriaViewSet(viewsets.ReadOnlyModelViewSet):
    """Las categorías del catálogo son visibles sin iniciar sesión."""

    queryset = Categoria.objects.all()
    serializer_class = CategoriaSerializer
    permission_classes = [AllowAny]


class ProductoViewSet(viewsets.ModelViewSet):
    """Lectura pública del catálogo; solo administración puede modificarlo."""

    serializer_class = ProductoSerializer

    def get_permissions(self):
        if self.request.method in SAFE_METHODS:
            return [AllowAny()]
        return [EsAdministrador()]

    def get_queryset(self):
        qs = Producto.objects.select_related("categoria")
        es_admin = (
            self.request.user.is_authenticated
            and getattr(self.request.user, "rol", None) == "administrador"
        )

        # El catálogo público y los demás roles nunca reciben productos inactivos.
        # Administración sí puede consultar todos para reactivar productos de temporada.
        if not es_admin:
            qs = qs.filter(activo=True)
        else:
            activo = self.request.query_params.get("activo")
            if activo in {"true", "false"}:
                qs = qs.filter(activo=(activo == "true"))

        q = self.request.query_params.get("q", "").strip()
        categoria = self.request.query_params.get("categoria", "").strip()
        if q:
            qs = qs.filter(nombre__icontains=q)
        if categoria:
            qs = qs.filter(categoria_id=categoria)
        return qs

    def destroy(self, request, *args, **kwargs):
        """DELETE realiza baja lógica; nunca elimina físicamente un producto."""
        producto = self.get_object()
        if not producto.activo:
            return Response({"detail": "El producto ya estaba desactivado."}, status=status.HTTP_200_OK)
        producto.activo = False
        producto.save(update_fields=["activo", "actualizado_en"])
        return Response(
            {"detail": "Producto desactivado. Puedes reactivarlo cuando vuelva la temporada."},
            status=status.HTTP_200_OK,
        )
