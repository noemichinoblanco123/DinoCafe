from rest_framework.routers import DefaultRouter
from django.urls import path

from .views import PedidoViewSet, ReporteVentasView

router = DefaultRouter()
router.register("pedidos", PedidoViewSet, basename="pedidos")

urlpatterns = [path("reporte-ventas/", ReporteVentasView.as_view(), name="reporte-ventas")] + router.urls
