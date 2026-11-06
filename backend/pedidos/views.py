from decimal import Decimal, InvalidOperation

from django.db import transaction
from django.db.models import DecimalField, ExpressionWrapper, F, Sum
from django.utils import timezone
from django.utils.dateparse import parse_date
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from catalogo.models import Producto
from dinocafe.permissions import EsAdministrador, EsCajero, EsCajeroOAdministrador

from .models import Pago, Pedido, Reembolso
from .serializers import PagoSerializer, PedidoCreateSerializer, PedidoSerializer, ReembolsoSerializer

# Solo el personal indicado puede avanzar cada etapa del servicio.
TRANSICIONES = {
    Pedido.Estado.ESPERA: (Pedido.Estado.EN_PREPARACION, {"cocina"}),
    Pedido.Estado.EN_PREPARACION: (Pedido.Estado.LISTO, {"cocina"}),
    Pedido.Estado.LISTO: (Pedido.Estado.ENTREGADO, {"mesero"}),
}


def descontar_stock_del_pedido(pedido):
    """Descuenta existencias una sola vez, al confirmar que el pedido fue pagado."""
    for detalle in pedido.detalles.all():
        producto = Producto.objects.select_for_update().get(pk=detalle.producto_id)
        if producto.stock < detalle.cantidad:
            raise ValidationError({
                "stock": f"Stock insuficiente de {producto.nombre}. Disponible: {producto.stock}; solicitado: {detalle.cantidad}."
            })
        producto.stock -= detalle.cantidad
        producto.save(update_fields=["stock", "actualizado_en"])


class PedidoViewSet(viewsets.ModelViewSet):
    """Pedidos registrados en caja y flujo de pago, cocina y entrega."""

    permission_classes = [IsAuthenticated]
    serializer_class = PedidoSerializer

    def get_permissions(self):
        if self.action == "create":
            return [EsCajero()]
        if self.action in {"update", "partial_update", "destroy"}:
            return [EsAdministrador()]
        if self.action in {"registrar_pago", "verificar_qr", "registrar_reembolso"}:
            return [EsCajero()]
        return [IsAuthenticated()]

    def get_queryset(self):
        qs = Pedido.objects.select_related(
            "pago", "registrado_por", "preparado_por", "listo_por", "entregado_por"
        ).prefetch_related("detalles__producto", "pago__reembolsos")

        # Cada rol recibe únicamente las operaciones que necesita. Administración
        # puede consultar el historial completo para supervisar el proceso.
        rol = getattr(self.request.user, "rol", None)
        if rol == "cocina":
            qs = qs.filter(
                pago__verificado=True,
                estado__in=[Pedido.Estado.ESPERA, Pedido.Estado.EN_PREPARACION, Pedido.Estado.LISTO],
            )
        elif rol == "mesero":
            qs = qs.filter(pago__verificado=True, estado=Pedido.Estado.LISTO)

        estados = self.request.query_params.get("estado", "").strip()
        if estados:
            lista = [e.strip() for e in estados.split(",") if e.strip()]
            qs = qs.filter(estado__in=lista)
        return qs

    def get_serializer_class(self):
        if self.action == "create":
            return PedidoCreateSerializer
        return PedidoSerializer

    def create(self, request, *args, **kwargs):
        if request.user.rol != "cajero":
            raise PermissionDenied("Solo caja registra pedidos y asigna la mesa.")
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        pedido = serializer.save(registrado_por=request.user)
        return Response(
            PedidoSerializer(pedido, context=self.get_serializer_context()).data,
            status=status.HTTP_201_CREATED,
        )

    @action(detail=True, methods=["patch"], url_path="estado")
    def cambiar_estado(self, request, pk=None):
        pedido = self.get_object()
        nuevo = request.data.get("estado")

        if nuevo not in Pedido.Estado.values:
            raise ValidationError({"estado": "Estado no válido."})
        if not hasattr(pedido, "pago") or not pedido.pago.verificado:
            raise ValidationError({"estado": "Cocina solo recibe pedidos con el pago verificado."})

        transicion = TRANSICIONES.get(pedido.estado)
        if not transicion:
            raise ValidationError({"estado": "El pedido no admite más cambios de estado."})

        siguiente, roles = transicion
        if request.user.rol not in roles:
            raise PermissionDenied(
                f"El rol {request.user.rol} no puede cambiar el estado {pedido.estado}."
            )
        if nuevo != siguiente:
            raise ValidationError({"estado": f"Transición inválida. El siguiente estado debe ser {siguiente}."})

        ahora = timezone.now()
        pedido.estado = nuevo
        campos = ["estado", "actualizado_en"]
        if nuevo == Pedido.Estado.EN_PREPARACION:
            pedido.preparado_por = request.user
            pedido.en_preparacion_en = ahora
            campos.extend(["preparado_por", "en_preparacion_en"])
        elif nuevo == Pedido.Estado.LISTO:
            pedido.listo_por = request.user
            pedido.listo_en = ahora
            campos.extend(["listo_por", "listo_en"])
        elif nuevo == Pedido.Estado.ENTREGADO:
            pedido.entregado_por = request.user
            pedido.entregado_en = ahora
            campos.extend(["entregado_por", "entregado_en"])
        pedido.save(update_fields=campos)
        pedido.refresh_from_db()
        return Response(PedidoSerializer(pedido, context=self.get_serializer_context()).data)

    @action(detail=True, methods=["post"], url_path="pago", permission_classes=[EsCajero])
    def registrar_pago(self, request, pk=None):
        self.get_object()  # transforma IDs inexistentes en un 404 DRF claro
        metodo = request.data.get("metodo")
        referencia = str(request.data.get("referencia_comprobante", "")).strip()
        try:
            monto = Decimal(str(request.data.get("monto_recibido", "")))
        except (InvalidOperation, ValueError) as exc:
            raise ValidationError({"monto_recibido": "Ingresa un monto válido."}) from exc

        with transaction.atomic():
            pedido = Pedido.objects.select_for_update().get(pk=pk)
            total = pedido.total
            if pedido.estado != Pedido.Estado.PENDIENTE_PAGO:
                raise ValidationError({"pago": "El pedido no está pendiente de cobro."})
            if Pago.objects.filter(pedido=pedido).exists():
                raise ValidationError({"pago": "Este pedido ya tiene un pago registrado."})
            if total <= 0:
                raise ValidationError({"pago": "No se puede cobrar un pedido sin productos."})
            if not monto.is_finite() or monto < total:
                raise ValidationError({"monto_recibido": "El monto debe cubrir el total del pedido."})
            if monto > Decimal("99999999.99"):
                raise ValidationError({"monto_recibido": "El monto excede el límite permitido."})
            if monto.as_tuple().exponent < -2:
                raise ValidationError({"monto_recibido": "El monto admite como máximo dos decimales."})
            if metodo not in Pago.Metodo.values:
                raise ValidationError({"metodo": "El método debe ser EFECTIVO o QR."})
            if metodo == Pago.Metodo.QR and monto != total:
                raise ValidationError({"monto_recibido": "El pago QR debe coincidir con el total exacto."})
            if metodo == Pago.Metodo.QR and not referencia:
                raise ValidationError({"referencia_comprobante": "Ingresa la referencia del comprobante QR."})

            efectivo = metodo == Pago.Metodo.EFECTIVO
            if efectivo:
                descontar_stock_del_pedido(pedido)
            pago = Pago.objects.create(
                pedido=pedido,
                monto_recibido=monto,
                metodo=metodo,
                referencia_comprobante=referencia if metodo == Pago.Metodo.QR else "",
                verificado=efectivo,
                verificado_por=request.user if efectivo else None,
                verificado_en=timezone.now() if efectivo else None,
                creado_por=request.user,
            )
            # El pedido llega a cocina solo después de cobrar/verificar.
            if efectivo:
                pedido.estado = Pedido.Estado.ESPERA
                pedido.save(update_fields=["estado", "actualizado_en"])

        return Response(PagoSerializer(pago).data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["post"], url_path="verificar-qr", permission_classes=[EsCajero])
    def verificar_qr(self, request, pk=None):
        self.get_object()
        with transaction.atomic():
            pedido = Pedido.objects.select_for_update().get(pk=pk)
            try:
                pago = Pago.objects.select_for_update().get(pedido=pedido)
            except Pago.DoesNotExist as exc:
                raise ValidationError({"pago": "El pedido todavía no tiene un pago."}) from exc
            if pago.metodo != Pago.Metodo.QR:
                raise ValidationError({"pago": "Solo se verifica el comprobante de pagos QR."})
            if pago.verificado:
                raise ValidationError({"pago": "El comprobante ya fue verificado."})
            descontar_stock_del_pedido(pedido)
            pago.verificado = True
            pago.verificado_por = request.user
            pago.verificado_en = timezone.now()
            pago.save(update_fields=["verificado", "verificado_por", "verificado_en"])
            pedido.estado = Pedido.Estado.ESPERA
            pedido.save(update_fields=["estado", "actualizado_en"])
        return Response(PagoSerializer(pago).data)

    @action(detail=True, methods=["post"], url_path="reembolsos", permission_classes=[EsCajero])
    def registrar_reembolso(self, request, pk=None):
        pedido = self.get_object()
        try:
            pago = pedido.pago
        except Pago.DoesNotExist as exc:
            raise ValidationError({"pago": "El pedido no tiene un pago registrado."}) from exc
        if not pago.verificado:
            raise ValidationError({"pago": "Verifica el pago antes de registrar un reembolso."})
        try:
            monto = Decimal(str(request.data.get("monto", "")))
        except (InvalidOperation, ValueError) as exc:
            raise ValidationError({"monto": "Ingresa un monto válido."}) from exc
        motivo = str(request.data.get("motivo", "")).strip()
        if not monto.is_finite() or monto <= 0:
            raise ValidationError({"monto": "El monto del reembolso debe ser mayor que cero."})
        if monto > Decimal("99999999.99"):
            raise ValidationError({"monto": "El monto excede el límite permitido."})
        if monto.as_tuple().exponent < -2:
            raise ValidationError({"monto": "El monto admite como máximo dos decimales."})
        if not motivo:
            raise ValidationError({"motivo": "Indica el motivo del reembolso."})
        with transaction.atomic():
            pago = Pago.objects.select_for_update().select_related("pedido").get(pk=pago.pk)
            reembolsado = pago.reembolsos.aggregate(total=Sum("monto"))["total"] or Decimal("0.00")
            disponible = pago.pedido.total - reembolsado
            if monto > disponible:
                raise ValidationError({"monto": f"El reembolso no puede superar Bs {disponible}."})
            reembolso = Reembolso.objects.create(
                pago=pago,
                monto=monto,
                motivo=motivo[:240],
                registrado_por=request.user,
            )
        return Response(ReembolsoSerializer(reembolso).data, status=status.HTTP_201_CREATED)


class ReporteVentasView(APIView):
    permission_classes = [EsCajeroOAdministrador]

    def get(self, request):
        hoy = timezone.localdate()
        desde_texto = request.query_params.get("desde", hoy.isoformat())
        hasta_texto = request.query_params.get("hasta", hoy.isoformat())
        desde = parse_date(desde_texto)
        hasta = parse_date(hasta_texto)
        if not desde or not hasta:
            raise ValidationError({"periodo": "Usa fechas válidas con formato AAAA-MM-DD."})
        if desde > hasta:
            raise ValidationError({"periodo": "La fecha inicial no puede ser posterior a la final."})
        if hasta > hoy:
            raise ValidationError({"periodo": "La fecha final no puede ser futura."})
        if request.user.rol == "cajero" and (desde != hoy or hasta != hoy):
            raise PermissionDenied("Caja solo puede consultar y conciliar las ventas del día actual.")

        pagos = list(
            Pago.objects.filter(
                verificado=True,
                creado_en__date__range=(desde, hasta),
            ).select_related("pedido").prefetch_related("pedido__detalles")
        )
        ventas_brutas = sum((p.pedido.total for p in pagos), Decimal("0.00"))
        por_metodo = {}
        for pago in pagos:
            por_metodo[pago.metodo] = por_metodo.get(pago.metodo, Decimal("0.00")) + pago.pedido.total

        reembolsos = Reembolso.objects.filter(creado_en__date__range=(desde, hasta))
        total_reembolsado = reembolsos.aggregate(total=Sum("monto"))["total"] or Decimal("0.00")
        lineas = Pedido.objects.filter(
            pago__verificado=True,
            pago__creado_en__date__range=(desde, hasta),
        ).values(
            "detalles__producto_id",
            "detalles__producto__nombre",
            "detalles__producto__categoria__nombre",
        ).annotate(
            unidades=Sum("detalles__cantidad"),
            total=Sum(ExpressionWrapper(
                F("detalles__cantidad") * F("detalles__precio_unitario"),
                output_field=DecimalField(max_digits=12, decimal_places=2),
            )),
        ).order_by("detalles__producto__nombre")

        productos = [
            {
                "id": fila["detalles__producto_id"],
                "nombre": fila["detalles__producto__nombre"],
                "categoria": fila["detalles__producto__categoria__nombre"],
                "unidades": fila["unidades"],
                "total": fila["total"] or Decimal("0.00"),
            }
            for fila in lineas
        ]
        por_categoria = {}
        for producto in productos:
            nombre = producto["categoria"]
            fila = por_categoria.setdefault(nombre, {"categoria": nombre, "unidades": 0, "total": Decimal("0.00")})
            fila["unidades"] += producto["unidades"]
            fila["total"] += producto["total"]

        return Response({
            "desde": desde,
            "hasta": hasta,
            "cantidad_pedidos": len(pagos),
            "ventas_brutas": ventas_brutas,
            "reembolsos": total_reembolsado,
            "ventas_net": ventas_brutas - total_reembolsado,
            "por_metodo": [
                {"metodo": metodo, "total": total}
                for metodo, total in sorted(por_metodo.items())
            ],
            "productos": productos,
            "categorias": list(por_categoria.values()),
        })
