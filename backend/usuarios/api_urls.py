from rest_framework.routers import DefaultRouter

from .views import UsuarioGestionViewSet

router = DefaultRouter()
router.register("usuarios", UsuarioGestionViewSet, basename="usuarios")

urlpatterns = router.urls
