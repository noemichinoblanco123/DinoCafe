from decimal import Decimal

from django.conf import settings
from django.db import models

from catalogo.models import Producto


MESAS = [(numero, f"Mesa {numero}") for numero in range(1, 11)]


class Pedido(models.Model):
    """Pedido registrado por caja y liberado a cocina solo después del pago."""

    class Estado(models.TextChoices):
        PENDIENTE_PAGO = "PENDIENTE_PAGO", "Pendiente de pago"
        ESPERA = "ESPERA", "En espera"
        EN_PREPARACION = "EN_PREPARACION", "En preparación"
        LISTO = "LISTO", "Listo para entregar"
        ENTREGADO = "ENTREGADO", "Entregado"

    estado = models.CharField(
        max_length=20,
        choices=Estado.choices,
        default=Estado.PENDIENTE_PAGO,
    )
    mesa = models.PositiveSmallIntegerField(choices=MESAS, default=1)
    registrado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="pedidos_registrados",
    )
    preparado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="pedidos_iniciados",
    )
    listo_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="pedidos_listos",
    )
    entregado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="pedidos_entregados",
    )
    en_preparacion_en = models.DateTimeField(null=True, blank=True)
    listo_en = models.DateTimeField(null=True, blank=True)
    entregado_en = models.DateTimeField(null=True, blank=True)
    creado_en = models.DateTimeField(auto_now_add=True)
    actualizado_en = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["creado_en"]
        verbose_name = "pedido"
        verbose_name_plural = "pedidos"

    @property
    def total(self):
        """Suma exacta de subtotales con Decimal (RNF7)."""
        return sum((detalle.subtotal for detalle in self.detalles.all()), Decimal("0.00"))

    def __str__(self):
        return f"Pedido #{self.pk} · Mesa {self.mesa} ({self.get_estado_display()})"


class DetallePedido(models.Model):
    pedido = models.ForeignKey(
        Pedido,
        on_delete=models.CASCADE,
        related_name="detalles",
    )
    producto = models.ForeignKey(Producto, on_delete=models.PROTECT)
    cantidad = models.PositiveIntegerField()
    # Se guarda el precio aplicado para que un cambio de catálogo no altere la venta.
    precio_unitario = models.DecimalField(max_digits=8, decimal_places=2)

    class Meta:
        verbose_name = "detalle de pedido"
        verbose_name_plural = "detalles de pedido"

    @property
    def subtotal(self):
        return self.precio_unitario * self.cantidad

    def __str__(self):
        return f"{self.cantidad} x {self.producto.nombre}"


class Pago(models.Model):
    class Metodo(models.TextChoices):
        EFECTIVO = "EFECTIVO", "Efectivo"
        QR = "QR", "QR"

    pedido = models.OneToOneField(Pedido, on_delete=models.PROTECT, related_name="pago")
    monto_recibido = models.DecimalField(max_digits=10, decimal_places=2)
    metodo = models.CharField(max_length=10, choices=Metodo.choices)
    referencia_comprobante = models.CharField(max_length=120, blank=True)
    verificado = models.BooleanField(default=False)
    verificado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="pagos_verificados",
    )
    verificado_en = models.DateTimeField(null=True, blank=True)
    creado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="pagos_registrados",
    )
    creado_en = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-creado_en"]

    @property
    def cambio(self):
        return self.monto_recibido - self.pedido.total


class Reembolso(models.Model):
    pago = models.ForeignKey(Pago, on_delete=models.PROTECT, related_name="reembolsos")
    monto = models.DecimalField(max_digits=10, decimal_places=2)
    motivo = models.CharField(max_length=240)
    registrado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="reembolsos_registrados",
    )
    creado_en = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-creado_en"]
