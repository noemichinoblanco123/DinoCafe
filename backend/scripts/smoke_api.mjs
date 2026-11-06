/**
 * Smoke test del flujo de servicio: catálogo público -> caja -> pago -> cocina -> mesero.
 * Uso: node backend/scripts/smoke_api.mjs
 * Requiere el backend en http://localhost:8000 y el frontend en 5173.
 */
import assert from "node:assert/strict";

const API = process.env.API_URL ?? "http://localhost:8000/api";
const WEB = process.env.WEB_URL ?? "http://localhost:5173";
const ORIGEN = new URL(WEB).origin;

async function pedir(ruta, { token, ...opciones } = {}) {
  const res = await fetch(`${API}${ruta}`, {
    ...opciones,
    headers: {
      "Content-Type": "application/json",
      Origin: ORIGEN,
      ...(token && { Authorization: `Bearer ${token}` }),
      ...opciones.headers,
    },
  });
  return res;
}

async function json(ruta, opciones) {
  const res = await pedir(ruta, opciones);
  assert.ok(res.ok, `${ruta} respondió ${res.status}`);
  return res.json();
}

async function iniciarSesion(username, password) {
  const response = await pedir("/auth/login/", {
    method: "POST", body: JSON.stringify({ username, password }),
  });
  assert.equal(response.status, 200, `login de ${username}`);
  return response.json();
}

// El catálogo se puede consultar sin credenciales.
const categoriasPublicas = await json("/categorias/");
const productosPublicos = await json("/productos/");
assert.ok(categoriasPublicas.some((c) => c.nombre === "Bebidas"), "categoría pública Bebidas");
assert.ok(productosPublicos.length >= 10, "catálogo público con productos");
assert.equal(typeof productosPublicos[0].precio, "string", "precio decimal como string");

const sesionAdmin = await iniciarSesion("admin", "admin123");
assert.equal(sesionAdmin.rol, "administrador");
const origen = await pedir("/auth/me/", { token: sesionAdmin.access });
assert.equal(origen.headers.get("access-control-allow-origin"), ORIGEN, "CORS acepta Vite");

const sesionCajero = await iniciarSesion("cajero", "cajero123");
const producto = productosPublicos.find((p) => p.stock > 0);
assert.ok(producto, "hay al menos un producto con stock");
const creado = await pedir("/pedidos/", {
  method: "POST", token: sesionCajero.access,
  body: JSON.stringify({ mesa: 10, detalles: [{ producto: producto.id, cantidad: 1 }] }),
});
assert.equal(creado.status, 201, "caja registra un pedido");
const pedido = await creado.json();
assert.equal(pedido.estado, "PENDIENTE_PAGO", "nuevo pedido espera el cobro");
assert.equal(pedido.mesa, 10, "caja asignó mesa 10");
assert.equal(pedido.registrado_por, "cajero", "se guarda quién registró el pedido");

const sesionCocina = await iniciarSesion("cocina", "cocina123");
const cocinaAntes = await json("/pedidos/", { token: sesionCocina.access });
assert.ok(!cocinaAntes.some((p) => p.id === pedido.id), "cocina no ve pedidos pendientes de pago");

const pago = await pedir(`/pedidos/${pedido.id}/pago/`, {
  method: "POST", token: sesionCajero.access,
  body: JSON.stringify({ metodo: "EFECTIVO", monto_recibido: pedido.total }),
});
assert.equal(pago.status, 201, "cajero confirma pago efectivo");

const cocinaDespues = await json("/pedidos/", { token: sesionCocina.access });
assert.ok(cocinaDespues.some((p) => p.id === pedido.id), "pedido pagado aparece en cocina");
const empezar = await pedir(`/pedidos/${pedido.id}/estado/`, {
  method: "PATCH", token: sesionCocina.access,
  body: JSON.stringify({ estado: "EN_PREPARACION" }),
});
assert.equal(empezar.status, 200, "cocina inicia preparación");
const listo = await pedir(`/pedidos/${pedido.id}/estado/`, {
  method: "PATCH", token: sesionCocina.access,
  body: JSON.stringify({ estado: "LISTO" }),
});
assert.equal(listo.status, 200, "cocina marca pedido listo");

const sesionMesero = await iniciarSesion("mesero", "mesero123");
const entregas = await json("/pedidos/?estado=LISTO", { token: sesionMesero.access });
assert.ok(entregas.some((p) => p.id === pedido.id), "mesero recibe el pedido listo");
const entrega = await pedir(`/pedidos/${pedido.id}/estado/`, {
  method: "PATCH", token: sesionMesero.access,
  body: JSON.stringify({ estado: "ENTREGADO" }),
});
assert.equal(entrega.status, 200, "mesero confirma la entrega");
assert.equal((await entrega.json()).entregado_por, "mesero", "queda registrada la persona que entregó");

const seguimiento = await json("/pedidos/", { token: sesionAdmin.access });
assert.ok(seguimiento.some((p) => p.id === pedido.id && p.estado === "ENTREGADO"), "administración ve el flujo completo");

const noPuedeCrear = await pedir("/pedidos/", {
  method: "POST", token: sesionMesero.access,
  body: JSON.stringify({ mesa: 1, detalles: [{ producto: producto.id, cantidad: 1 }] }),
});
assert.equal(noPuedeCrear.status, 403, "mesero no registra pedidos");

const noPuedeCrearProducto = await pedir("/productos/", {
  method: "POST", token: sesionMesero.access,
  body: JSON.stringify({ nombre: "No permitido", categoria: categoriasPublicas[0].id, precio: "1.00", stock: 1 }),
});
assert.equal(noPuedeCrearProducto.status, 403, "mesero no crea productos");

const html = await fetch(WEB).then((response) => response.text());
assert.ok(html.includes('id="root"'), "Vite sirve la aplicación");
console.log("OK: catálogo público, caja, cobro, cocina, entrega y supervisión administrativa.");
