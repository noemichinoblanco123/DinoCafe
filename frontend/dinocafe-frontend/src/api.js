// Capa de presentación: único punto de contacto con la API REST de Django (RNF5).
const BASE = import.meta.env.VITE_API_URL ?? "http://localhost:8000/api";

export const getToken = () => localStorage.getItem("access_token");
export const getRefreshToken = () => localStorage.getItem("refresh_token");
export const getRol = () => localStorage.getItem("rol");
export const getUsuario = () => localStorage.getItem("username");

export function guardarSesion({ access, refresh, rol, username }) {
  localStorage.setItem("access_token", access);
  if (refresh) localStorage.setItem("refresh_token", refresh);
  localStorage.setItem("rol", rol);
  if (username) localStorage.setItem("username", username);
}

export function cerrarSesion() {
  localStorage.removeItem("access_token");
  localStorage.removeItem("refresh_token");
  localStorage.removeItem("rol");
  localStorage.removeItem("username");
}

let refreshEnCurso;

async function renovarSesion() {
  const refresh = getRefreshToken();
  if (!refresh) {
    cerrarSesion();
    const error = new Error("La sesión expiró. Ingresa de nuevo.");
    error.status = 401;
    throw error;
  }
  if (!refreshEnCurso) {
    refreshEnCurso = fetch(`${BASE}/auth/refresh/`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ refresh }),
    }).then(async (res) => {
      if (!res.ok) {
        cerrarSesion();
        const error = new Error("La sesión expiró. Ingresa de nuevo.");
        error.status = 401;
        throw error;
      }
      const datos = await res.json();
      if (!datos.access) {
        cerrarSesion();
        throw new Error("El servidor no pudo renovar la sesión.");
      }
      localStorage.setItem("access_token", datos.access);
      if (datos.refresh) localStorage.setItem("refresh_token", datos.refresh);
      return datos.access;
    }).finally(() => {
      refreshEnCurso = null;
    });
  }
  return refreshEnCurso;
}

async function request(path, options = {}, reintentar = true) {
  const enviar = (token) => fetch(`${BASE}${path}`, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      ...(token && { Authorization: `Bearer ${token}` }),
      ...options.headers,
    },
  });
  let res = await enviar(getToken());
  if (res.status === 401 && reintentar && !["/auth/login/", "/auth/refresh/"].includes(path)) {
    res = await enviar(await renovarSesion());
  }
  if (!res.ok) {
    let detalle = "";
    try {
      const d = await res.json();
      detalle = d.detail || Object.values(d).flat().join(" ");
    } catch { /* respuesta sin cuerpo JSON */ }
    const error = new Error(detalle || `Error ${res.status}`);
    error.status = res.status;
    throw error;
  }
  return res.status === 204 ? null : res.json();
}

export const authApi = {
  login: (username, password) =>
    request("/auth/login/", { method: "POST", body: JSON.stringify({ username, password }) }),
  me: () => request("/auth/me/"),
};

// Los precios viajan como string decimal ("12.50") para no perder exactitud (RNF7).
export const productosApi = {
  listar: ({ q = "", categoria = "", activo = "" } = {}) => {
    const params = new URLSearchParams({ q, categoria });
    if (activo) params.set("activo", activo);
    return request(`/productos/?${params}`);
  },
  categorias: () => request("/categorias/"),
  crear: (datos) => request("/productos/", { method: "POST", body: JSON.stringify(datos) }),
  actualizar: (id, datos) =>
    request(`/productos/${id}/`, { method: "PATCH", body: JSON.stringify(datos) }),
};

export const pedidosApi = {
  crear: (datos) => request("/pedidos/", { method: "POST", body: JSON.stringify(datos) }),
  listarCocina: () => request("/pedidos/?estado=ESPERA,EN_PREPARACION,LISTO"),
  listarMesero: () => request("/pedidos/?estado=LISTO"),
  listarCaja: () => request("/pedidos/"),
  listarAdministrador: () => request("/pedidos/"),
  cambiarEstado: (id, estado) =>
    request(`/pedidos/${id}/estado/`, { method: "PATCH", body: JSON.stringify({ estado }) }),
  registrarPago: (id, datos) =>
    request(`/pedidos/${id}/pago/`, { method: "POST", body: JSON.stringify(datos) }),
  verificarQr: (id) =>
    request(`/pedidos/${id}/verificar-qr/`, { method: "POST", body: "{}" }),
  registrarReembolso: (id, datos) =>
    request(`/pedidos/${id}/reembolsos/`, { method: "POST", body: JSON.stringify(datos) }),
};

export const reportesApi = {
  ventas: (desde, hasta) =>
    request(`/reporte-ventas/?${new URLSearchParams({ desde, hasta })}`),
};

export const usuariosApi = {
  listar: () => request("/usuarios/"),
  crear: (datos) => request("/usuarios/", { method: "POST", body: JSON.stringify(datos) }),
  actualizar: (id, datos) =>
    request(`/usuarios/${id}/`, { method: "PATCH", body: JSON.stringify(datos) }),
};
