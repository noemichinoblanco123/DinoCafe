from decimal import Decimal

from rest_framework import serializers

from catalogo.models import Producto
from .models import DetallePedido, Pago, Pedido, Reembolso


class DetallePedidoSerializer(serializers.ModelSerializer):
    producto = serializers.CharField(source="producto.nombre", read_only=True)
    stock = serializers.IntegerField(source="producto.stock", read_only=True)
    subtotal = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)

    class Meta:
        model = DetallePedido
        fields = ["id", "producto", "cantidad", "stock", "precio_unitario", "subtotal"]


class DetallePedidoCreateSerializer(serializers.Serializer):
    producto = serializers.PrimaryKeyRelatedField(queryset=Producto.objects.filter(activo=True))
    cantidad = serializers.IntegerField(min_value=1)

    def validate(self, attrs):
        producto = attrs["producto"]
        cantidad = attrs["cantidad"]
        if not producto.activo:
            raise serializers.ValidationError({"producto": f"{producto.nombre} está desactivado y no se puede vender."})
        if producto.stock < 1 or cantidad > producto.stock:
            raise serializers.ValidationError(
                {"cantidad": f"{producto.nombre} está agotado o no tiene stock suficiente (disponible: {producto.stock})."}
            )
        return attrs


class PedidoSerializer(serializers.ModelSerializer):
    detalles = DetallePedidoSerializer(many=True, read_only=True)
    total = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)
    pago = serializers.SerializerMethodField()
    registrado_por = serializers.SerializerMethodField()
    preparado_por = serializers.SerializerMethodField()
    listo_por = serializers.SerializerMethodField()
    entregado_por = serializers.SerializerMethodField()

    class Meta:
        model = Pedido
        fields = [
            "id", "mesa", "estado", "creado_en", "actualizado_en", "total", "detalles", "pago",
            "registrado_por", "preparado_por", "listo_por", "entregado_por",
            "en_preparacion_en", "listo_en", "entregado_en",
        ]

    @staticmethod
    def _username(user):
        return user.username if user else None

    def get_registrado_por(self, pedido):
        return self._username(pedido.registrado_por)

    def get_preparado_por(self, pedido):
        return self._username(pedido.preparado_por)

    def get_listo_por(self, pedido):
        return self._username(pedido.listo_por)

    def get_entregado_por(self, pedido):
        return self._username(pedido.entregado_por)

    def get_pago(self, pedido):
        try:
            return PagoSerializer(pedido.pago).data
        except Pago.DoesNotExist:
            return None


class ReembolsoSerializer(serializers.ModelSerializer):
    registrado_por = serializers.CharField(source="registrado_por.username", read_only=True)

    class Meta:
        model = Reembolso
        fields = ["id", "monto", "motivo", "registrado_por", "creado_en"]


class PagoSerializer(serializers.ModelSerializer):
    cambio = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)
    creado_por = serializers.CharField(source="creado_por.username", read_only=True)
    verificado_por = serializers.SerializerMethodField()
    reembolsos = ReembolsoSerializer(many=True, read_only=True)
    reembolsado = serializers.SerializerMethodField()

    class Meta:
        model = Pago
        fields = [
            "id", "monto_recibido", "metodo", "referencia_comprobante",
            "verificado", "verificado_por", "verificado_en", "creado_por",
            "creado_en", "cambio", "reembolsos", "reembolsado",
        ]

    def get_verificado_por(self, pago):
        return pago.verificado_por.username if pago.verificado_por else None

    def get_reembolsado(self, pago):
        return sum((reembolso.monto for reembolso in pago.reembolsos.all()), Decimal("0.00"))


class PedidoCreateSerializer(serializers.ModelSerializer):
    detalles = DetallePedidoCreateSerializer(many=True)

    class Meta:
        model = Pedido
        fields = ["id", "mesa", "detalles"]
        read_only_fields = ["id"]

    def validate_mesa(self, value):
        if value < 1 or value > 10:
            raise serializers.ValidationError("Selecciona una mesa entre la 1 y la 10.")
        return value

    def validate_detalles(self, detalles):
        if not detalles:
            raise serializers.ValidationError("Agrega al menos un producto al pedido.")
        ids = [item["producto"].id for item in detalles]
        if len(ids) != len(set(ids)):
            raise serializers.ValidationError("Cada producto debe aparecer una sola vez en el carrito.")
        return detalles

    def create(self, validated_data):
        detalles = validated_data.pop("detalles")
        pedido = Pedido.objects.create(**validated_data, estado=Pedido.Estado.PENDIENTE_PAGO)
        for detalle in detalles:
            producto = detalle["producto"]
            DetallePedido.objects.create(
                pedido=pedido,
                producto=producto,
                cantidad=detalle["cantidad"],
                precio_unitario=producto.precio,
            )
        return pedido
