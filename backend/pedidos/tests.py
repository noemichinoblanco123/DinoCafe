from datetime import timedelta
from decimal import Decimal

from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from catalogo.models import Categoria, Producto
from pedidos.models import DetallePedido, Pedido
from usuarios.models import Usuario


class OperacionesApiTests(APITestCase):
    def setUp(self):
        self.admin = Usuario.objects.create_user(username="admin_test", password="secret", rol="administrador")
        self.cajero = Usuario.objects.create_user(username="cajero_test", password="secret", rol="cajero")
        self.mesero = Usuario.objects.create_user(username="mesero_test", password="secret", rol="mesero")
        self.cocina = Usuario.objects.create_user(username="cocina_test", password="secret", rol="cocina")
        self.producto = Producto.objects.create(
            nombre="Café", categoria=Categoria.objects.create(nombre="Bebidas"),
            precio=Decimal("10.00"), stock=5,
        )

    def crear_pedido(self, estado=Pedido.Estado.PENDIENTE_PAGO, mesa=3, registrado_por=None):
        pedido = Pedido.objects.create(estado=estado, mesa=mesa, registrado_por=registrado_por)
        DetallePedido.objects.create(
            pedido=pedido, producto=self.producto, cantidad=1, precio_unitario=Decimal("10.00")
        )
        return pedido

    def pagar_efectivo(self, pedido, monto="10.00"):
        self.client.force_authenticate(self.cajero)
        return self.client.post(
            reverse("pedidos-registrar-pago", args=[pedido.pk]),
            {"metodo": "EFECTIVO", "monto_recibido": monto}, format="json",
        )

    def test_catalogo_publico_no_exige_inicio_de_sesion(self):
        productos = self.client.get(reverse("productos-list"))
        categorias = self.client.get(reverse("categorias-list"))
        self.assertEqual(productos.status_code, status.HTTP_200_OK)
        self.assertEqual(categorias.status_code, status.HTTP_200_OK)
        self.assertEqual(productos.data[0]["nombre"], "Café")

    def test_productos_inactivos_no_aparecen_en_catalogo_publico_y_admin_puede_verlos(self):
        producto_inactivo = Producto.objects.create(
            nombre="Bebida de temporada", categoria=self.producto.categoria,
            precio=Decimal("8.00"), stock=4, activo=False,
        )

        publico = self.client.get(reverse("productos-list"))
        self.assertEqual(publico.status_code, status.HTTP_200_OK)
        self.assertNotIn(producto_inactivo.pk, [item["id"] for item in publico.data])

        self.client.force_authenticate(self.admin)
        admin = self.client.get(reverse("productos-list"))
        self.assertIn(producto_inactivo.pk, [item["id"] for item in admin.data])

    def test_solo_admin_puede_desactivar_y_reactivar_producto_sin_borrarlo(self):
        url = reverse("productos-detail", args=[self.producto.pk])
        self.client.force_authenticate(self.cajero)
        no_autorizado = self.client.patch(url, {"activo": False}, format="json")
        self.assertEqual(no_autorizado.status_code, status.HTTP_403_FORBIDDEN)

        self.client.force_authenticate(self.admin)
        desactivado = self.client.patch(url, {"activo": False}, format="json")
        self.assertEqual(desactivado.status_code, status.HTTP_200_OK)
        self.producto.refresh_from_db()
        self.assertFalse(self.producto.activo)
        self.assertTrue(Producto.objects.filter(pk=self.producto.pk).exists())

        reactivado = self.client.patch(url, {"activo": True}, format="json")
        self.assertEqual(reactivado.status_code, status.HTTP_200_OK)
        self.producto.refresh_from_db()
        self.assertTrue(self.producto.activo)

    def test_producto_agotado_o_inactivo_no_puede_agregarse_a_un_pedido(self):
        self.client.force_authenticate(self.cajero)
        self.producto.stock = 0
        self.producto.save(update_fields=["stock"])
        agotado = self.client.post(
            reverse("pedidos-list"),
            {"mesa": 2, "detalles": [{"producto": self.producto.pk, "cantidad": 1}]},
            format="json",
        )
        self.assertEqual(agotado.status_code, status.HTTP_400_BAD_REQUEST)

        self.producto.stock = 5
        self.producto.activo = False
        self.producto.save(update_fields=["stock", "activo"])
        inactivo = self.client.post(
            reverse("pedidos-list"),
            {"mesa": 2, "detalles": [{"producto": self.producto.pk, "cantidad": 1}]},
            format="json",
        )
        self.assertEqual(inactivo.status_code, status.HTTP_400_BAD_REQUEST)

    def test_solo_cajero_registra_pedido_y_asigna_mesa(self):
        self.client.force_authenticate(self.cajero)
        response = self.client.post(
            reverse("pedidos-list"),
            {"mesa": 6, "detalles": [{"producto": self.producto.pk, "cantidad": 2}]},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["mesa"], 6)
        self.assertEqual(response.data["estado"], "PENDIENTE_PAGO")
        self.assertEqual(response.data["registrado_por"], self.cajero.username)
        self.assertEqual(response.data["total"], "20.00")

    def test_mesero_no_puede_registrar_pedidos(self):
        self.client.force_authenticate(self.mesero)
        response = self.client.post(
            reverse("pedidos-list"),
            {"mesa": 2, "detalles": [{"producto": self.producto.pk, "cantidad": 1}]},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_pedido_no_llega_a_cocina_antes_del_pago(self):
        pedido = self.crear_pedido(registrado_por=self.cajero)
        self.client.force_authenticate(self.cocina)
        response = self.client.get(reverse("pedidos-list"))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 0)
        self.assertEqual(pedido.estado, Pedido.Estado.PENDIENTE_PAGO)

    def test_efectivo_habilita_cocina_y_calcula_cambio(self):
        pedido = self.crear_pedido(registrado_por=self.cajero)
        pago = self.pagar_efectivo(pedido, "15.00")
        self.assertEqual(pago.status_code, status.HTTP_201_CREATED)
        self.assertEqual(pago.data["cambio"], "5.00")
        self.assertTrue(pago.data["verificado"])
        pedido.refresh_from_db()
        self.assertEqual(pedido.estado, Pedido.Estado.ESPERA)
        self.producto.refresh_from_db()
        self.assertEqual(self.producto.stock, 4)

        self.client.force_authenticate(self.cocina)
        cocina_lista = self.client.get(reverse("pedidos-list"))
        self.assertEqual(len(cocina_lista.data), 1)
        empezado = self.client.patch(
            reverse("pedidos-cambiar-estado", args=[pedido.pk]),
            {"estado": "EN_PREPARACION"}, format="json",
        )
        self.assertEqual(empezado.status_code, status.HTTP_200_OK)
        self.assertEqual(empezado.data["preparado_por"], self.cocina.username)

        listo = self.client.patch(
            reverse("pedidos-cambiar-estado", args=[pedido.pk]),
            {"estado": "LISTO"}, format="json",
        )
        self.assertEqual(listo.status_code, status.HTTP_200_OK)
        self.assertEqual(listo.data["listo_por"], self.cocina.username)

        self.client.force_authenticate(self.mesero)
        entrega = self.client.patch(
            reverse("pedidos-cambiar-estado", args=[pedido.pk]),
            {"estado": "ENTREGADO"}, format="json",
        )
        self.assertEqual(entrega.status_code, status.HTTP_200_OK)
        self.assertEqual(entrega.data["entregado_por"], self.mesero.username)

    def test_qr_no_llega_a_cocina_hasta_que_cajero_verifique(self):
        pedido = self.crear_pedido(registrado_por=self.cajero)
        self.client.force_authenticate(self.cajero)
        pago = self.client.post(
            reverse("pedidos-registrar-pago", args=[pedido.pk]),
            {"metodo": "QR", "monto_recibido": "10.00", "referencia_comprobante": "QR-123"},
            format="json",
        )
        self.assertEqual(pago.status_code, status.HTTP_201_CREATED)
        self.assertFalse(pago.data["verificado"])
        pedido.refresh_from_db()
        self.assertEqual(pedido.estado, Pedido.Estado.PENDIENTE_PAGO)

        self.client.force_authenticate(self.cocina)
        self.assertEqual(len(self.client.get(reverse("pedidos-list")).data), 0)

        self.client.force_authenticate(self.cajero)
        verificado = self.client.post(reverse("pedidos-verificar-qr", args=[pedido.pk]))
        self.assertEqual(verificado.status_code, status.HTTP_200_OK)
        pedido.refresh_from_db()
        self.assertEqual(pedido.estado, Pedido.Estado.ESPERA)
        self.producto.refresh_from_db()
        self.assertEqual(self.producto.stock, 4)

        self.client.force_authenticate(self.cocina)
        self.assertEqual(len(self.client.get(reverse("pedidos-list")).data), 1)

    def test_cajero_no_puede_asignar_mesa_fuera_del_rango(self):
        self.client.force_authenticate(self.cajero)
        response = self.client.post(
            reverse("pedidos-list"),
            {"mesa": 11, "detalles": [{"producto": self.producto.pk, "cantidad": 1}]},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_cobro_efectivo_y_reembolso_parcial(self):
        pedido = self.crear_pedido(registrado_por=self.cajero)
        pago = self.pagar_efectivo(pedido, "15.00")
        self.assertEqual(pago.status_code, status.HTTP_201_CREATED)
        self.assertEqual(pago.data["cambio"], "5.00")

        self.client.force_authenticate(self.cajero)
        reembolso = self.client.post(
            reverse("pedidos-registrar-reembolso", args=[pedido.pk]),
            {"monto": "4.00", "motivo": "Producto devuelto"}, format="json",
        )
        self.assertEqual(reembolso.status_code, status.HTTP_201_CREATED)
        excedido = self.client.post(
            reverse("pedidos-registrar-reembolso", args=[pedido.pk]),
            {"monto": "7.00", "motivo": "Supera el saldo disponible"}, format="json",
        )
        self.assertEqual(excedido.status_code, status.HTTP_400_BAD_REQUEST)

        hoy = timezone.localdate().isoformat()
        reporte = self.client.get(reverse("reporte-ventas"), {"desde": hoy, "hasta": hoy})
        self.assertEqual(reporte.status_code, status.HTTP_200_OK)
        self.assertEqual(reporte.data["ventas_brutas"], Decimal("10.00"))
        self.assertEqual(reporte.data["reembolsos"], Decimal("4.00"))
        self.assertEqual(reporte.data["ventas_net"], Decimal("6.00"))

    def test_administrador_puede_supervisar_todos_los_pedidos(self):
        pedido = self.crear_pedido(registrado_por=self.cajero)
        self.pagar_efectivo(pedido)
        self.client.force_authenticate(self.admin)
        response = self.client.get(reverse("pedidos-list"))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]["mesa"], 3)
        self.assertEqual(response.data[0]["registrado_por"], self.cajero.username)

    def test_solo_administrador_gestiona_usuarios(self):
        self.client.force_authenticate(self.admin)
        response = self.client.post(
            reverse("usuarios-list"),
            {"username": "nuevo", "password": "contrasena-segura", "rol": "cocina"}, format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertNotIn("password", response.data)
        self.client.force_authenticate(self.cajero)
        self.assertEqual(self.client.get(reverse("usuarios-list")).status_code, status.HTTP_403_FORBIDDEN)

    def test_administrador_no_puede_quitarse_el_rol_o_desactivarse(self):
        self.client.force_authenticate(self.admin)
        response = self.client.patch(
            reverse("usuarios-detail", args=[self.admin.pk]), {"rol": "mesero"}, format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.admin.refresh_from_db()
        self.assertEqual(self.admin.rol, "administrador")

    def test_caja_solo_consulta_ventas_del_dia_actual(self):
        self.client.force_authenticate(self.cajero)
        ayer = (timezone.localdate() - timedelta(days=1)).isoformat()
        response = self.client.get(reverse("reporte-ventas"), {"desde": ayer, "hasta": ayer})
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_usuario_actual_devuelve_identidad_autenticada_y_exige_token(self):
        response_sin_sesion = self.client.get(reverse("usuario-actual"))
        self.assertEqual(response_sin_sesion.status_code, status.HTTP_401_UNAUTHORIZED)
        self.client.force_authenticate(self.mesero)
        response = self.client.get(reverse("usuario-actual"))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, {"username": "mesero_test", "rol": "mesero"})
