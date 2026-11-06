from django.db import models


class Categoria(models.Model):
    """Bebidas y acompañamientos (RF1)."""

    nombre = models.CharField(max_length=80, unique=True)
    # Ruta de la imagen promocional que se mostrará en el carrusel público.
    imagen_carrusel = models.CharField(max_length=255, blank=True, default="")

    class Meta:
        ordering = ["nombre"]
        verbose_name = "categoría"
        verbose_name_plural = "categorías"

    def __str__(self):
        return self.nombre


class Producto(models.Model):
    """Producto ofrecido con precio decimal exacto y stock (RF1, RF4, RNF7)."""

    nombre = models.CharField(max_length=120)
    categoria = models.ForeignKey(
        Categoria,
        on_delete=models.PROTECT,
        related_name="productos",
    )
    precio = models.DecimalField(max_digits=8, decimal_places=2)
    stock = models.PositiveIntegerField(default=0)
    # Ruta pública, por ejemplo: /images/productos/cafe.jpg
    imagen = models.CharField(max_length=255, blank=True, default="")
    # Baja lógica: el producto se conserva para no romper pedidos históricos.
    activo = models.BooleanField(default=True)
    creado_en = models.DateTimeField(auto_now_add=True)
    actualizado_en = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["nombre"]
        verbose_name = "producto"
        verbose_name_plural = "productos"

    def __str__(self):
        return f"{self.nombre} ({self.categoria.nombre})"
