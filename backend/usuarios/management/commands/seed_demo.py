"""Crea usuarios, categorías, productos y un flujo de pedidos de demostración.

Uso:
    python manage.py seed_demo
    python manage.py seed_demo --reset-pedidos

Las cuentas son exclusivamente de demostración.
"""
from datetime import timedelta
from decimal import Decimal

from django.core.management.base import BaseCommand
from django.utils import timezone

from catalogo.models import Categoria, Producto
from pedidos.models import DetallePedido, Pago, Pedido, Reembolso
from usuarios.models import Usuario

USUARIOS = [
    ("admin", "admin123", Usuario.Rol.ADMINISTRADOR, True, True),
    ("mesero", "mesero123", Usuario.Rol.MESERO, False, False),
    ("cajero", "cajero123", Usuario.Rol.CAJERO, False, False),
    ("cocina", "cocina123", Usuario.Rol.COCINA, False, False),
]

PRODUCTOS = [
    ("Té", "Bebidas", "5.00", 20),
    ("Café", "Bebidas", "7.00", 15),
    ("Cocoa", "Bebidas", "8.00", 4),
    ("Cocoa con leche", "Bebidas", "9.50", 0),
    ("Leche", "Bebidas", "6.00", 25),
    ("Pan", "Acompañamientos", "3.00", 30),
    ("Empanada", "Acompañamientos", "5.50", 12),
    ("Trozo de torta", "Acompañamientos", "12.00", 3),
    ("Trozo de rollo", "Acompañamientos", "10.00", 8),
    ("Sándwich de huevo", "Acompañamientos", "9.00", 2),
]

PEDIDOS = [
    (Pedido.Estado.PENDIENTE_PAGO, 2, 1, [("Café", 2), ("Pan", 1)], None),
    (Pedido.Estado.ESPERA, 9, 2, [("Cocoa", 1), ("Trozo de torta", 1)], Pago.Metodo.EFECTIVO),
    (Pedido.Estado.EN_PREPARACION, 14, 3, [("Té", 1), ("Empanada", 2)], Pago.Metodo.EFECTIVO),
    (Pedido.Estado.LISTO, 21, 4, [("Leche", 1), ("Sándwich de huevo", 1)], Pago.Metodo.QR),
    (Pedido.Estado.ENTREGADO, 35, 5, [("Leche", 2), ("Trozo de rollo", 1)], Pago.Metodo.EFECTIVO),
]


class Command(BaseCommand):
    help = "Crea usuarios, catálogo y pedidos de demostración para el flujo de caja."

    def add_arguments(self, parser):
        parser.add_argument("--reset-pedidos", action="store_true", help="Reinicia los pedidos de demostración.")

    def handle(self, *args, **options):
        self._crear_usuarios()
        self._crear_catalogo()
        if options["reset_pedidos"]:
            Reembolso.objects.all().delete()
            Pago.objects.all().delete()
            Pedido.objects.all().delete()
            self.stdout.write("  Pedidos anteriores eliminados.")
        self._crear_pedidos()
        self.stdout.write(self.style.SUCCESS("Datos de demostración listos."))
        self.stdout.write("  admin/admin123 · mesero/mesero123 · cajero/cajero123 · cocina/cocina123")

    def _crear_usuarios(self):
        for username, password, rol, is_staff, is_superuser in USUARIOS:
            usuario, creado = Usuario.objects.get_or_create(username=username)
            usuario.rol = rol
            usuario.is_staff = is_staff
            usuario.is_superuser = is_superuser
            usuario.is_active = True
            usuario.set_password(password)
            usuario.save()
            estado = "creado" if creado else "actualizado"
            self.stdout.write(f"  Usuario {username} ({rol}) {estado}.")

    def _crear_catalogo(self):
        imagenes_carrusel = {
            "Bebidas": "/images/carrusel/bebidas.jpg",
            "Acompañamientos": "/images/carrusel/acompanamientos.jpg",
        }
        for nombre, categoria_nombre, precio, stock in PRODUCTOS:
            categoria, _ = Categoria.objects.get_or_create(nombre=categoria_nombre)
            if not categoria.imagen_carrusel and categoria_nombre in imagenes_carrusel:
                categoria.imagen_carrusel = imagenes_carrusel[categoria_nombre]
                categoria.save(update_fields=["imagen_carrusel"])
            producto, _ = Producto.objects.update_or_create(
                nombre=nombre, categoria=categoria,
                defaults={"precio": Decimal(precio), "stock": stock},
            )
            # Rutas preparadas para que el equipo coloque sus propias fotografías en public/.
            nombre_archivo = {
                "Té": "te.jpg", "Café": "cafe.jpg", "Cocoa": "cocoa.jpg",
                "Cocoa con leche": "cocoa-con-leche.jpg", "Leche": "leche.jpg",
                "Pan": "pan.jpg", "Empanada": "empanada.jpg",
                "Trozo de torta": "trozo-de-torta.jpg", "Trozo de rollo": "trozo-de-rollo.jpg",
                "Sándwich de huevo": "sandwich-de-huevo.jpg",
            }.get(nombre, "")
            if nombre_archivo and not producto.imagen:
                producto.imagen = f"/images/productos/{nombre_archivo}"
                producto.save(update_fields=["imagen"])
        self.stdout.write(f"  {Categoria.objects.count()} categorías y {Producto.objects.count()} productos.")

    def _crear_pedidos(self):
        if Pedido.objects.exists():
            self.stdout.write("  Los pedidos ya existen; no se recrean.")
            return

        cajero = Usuario.objects.get(username="cajero")
        cocina = Usuario.objects.get(username="cocina")
        mesero = Usuario.objects.get(username="mesero")
        for estado, minutos, mesa, lineas, metodo in PEDIDOS:
            pedido = Pedido.objects.create(estado=estado, mesa=mesa, registrado_por=cajero)
            for nombre_producto, cantidad in lineas:
                producto = Producto.objects.get(nombre=nombre_producto)
                DetallePedido.objects.create(
                    pedido=pedido, producto=producto, cantidad=cantidad, precio_unitario=producto.precio,
                )
            if metodo:
                # Los ejemplos que ya fueron cobrados también reducen las existencias.
                for nombre_producto, cantidad in lineas:
                    producto = Producto.objects.get(nombre=nombre_producto)
                    producto.stock = max(0, producto.stock - cantidad)
                    producto.save(update_fields=["stock", "actualizado_en"])
                Pago.objects.create(
                    pedido=pedido,
                    monto_recibido=pedido.total,
                    metodo=metodo,
                    referencia_comprobante=f"DEMO-QR-{pedido.pk}" if metodo == Pago.Metodo.QR else "",
                    verificado=True,
                    verificado_por=cajero,
                    creado_por=cajero,
                    verificado_en=timezone.now(),
                )
            if estado in {Pedido.Estado.EN_PREPARACION, Pedido.Estado.LISTO, Pedido.Estado.ENTREGADO}:
                pedido.preparado_por = cocina
                pedido.en_preparacion_en = timezone.now() - timedelta(minutes=max(1, minutos - 4))
            if estado in {Pedido.Estado.LISTO, Pedido.Estado.ENTREGADO}:
                pedido.listo_por = cocina
                pedido.listo_en = timezone.now() - timedelta(minutes=max(1, minutos - 2))
            if estado == Pedido.Estado.ENTREGADO:
                pedido.entregado_por = mesero
                pedido.entregado_en = timezone.now() - timedelta(minutes=1)
            pedido.save()
            Pedido.objects.filter(pk=pedido.pk).update(creado_en=timezone.now() - timedelta(minutes=minutos))
        self.stdout.write(f"  {Pedido.objects.count()} pedidos de ejemplo con flujo de cobro y atención.")
