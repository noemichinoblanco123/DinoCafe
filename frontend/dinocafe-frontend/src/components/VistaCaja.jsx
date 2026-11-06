import { useCallback, useEffect, useMemo, useState } from "react";
import { pedidosApi, productosApi } from "../api";
import StockBadge from "./StockBadge";
import ImagenProducto from "./ImagenProducto";

const MESAS = Array.from({ length: 10 }, (_, index) => index + 1);

function moneda(valor) {
  return new Intl.NumberFormat("es-BO", { style: "currency", currency: "BOB" }).format(Number(valor));
}

function NuevoPedidoCaja({ alCrear, refreshToken }) {
  const [productos, setProductos] = useState([]);
  const [categorias, setCategorias] = useState([]);
  const [categoria, setCategoria] = useState("");
  const [busqueda, setBusqueda] = useState("");
  const [mesa, setMesa] = useState("1");
  const [carrito, setCarrito] = useState([]);
  const [cargando, setCargando] = useState(true);
  const [guardando, setGuardando] = useState(false);
  const [error, setError] = useState("");
  const [aviso, setAviso] = useState("");

  const cargarCatalogo = useCallback(async () => {
    setCargando(true);
    try {
      const [listaProductos, listaCategorias] = await Promise.all([
        productosApi.listar(),
        productosApi.categorias(),
      ]);
      setProductos(listaProductos);
      setCategorias(listaCategorias);
      setError("");
    } catch (e) {
      setError(e.message);
    } finally {
      setCargando(false);
    }
  }, []);

  useEffect(() => { cargarCatalogo(); }, [cargarCatalogo, refreshToken]);

  const visibles = useMemo(() => productos.filter((producto) => {
    const coincideTexto = producto.nombre.toLowerCase().includes(busqueda.trim().toLowerCase());
    const coincideCategoria = !categoria || String(producto.categoria) === categoria;
    return coincideTexto && coincideCategoria;
  }), [productos, busqueda, categoria]);

  const total = carrito.reduce((suma, linea) => suma + Number(linea.precio) * linea.cantidad, 0);

  function agregar(producto) {
    setError("");
    setAviso("");
    const existente = carrito.find((linea) => linea.id === producto.id);
    if (existente) {
      if (existente.cantidad >= producto.stock) {
        setError(`No hay suficiente stock de ${producto.nombre}.`);
        return;
      }
      setCarrito(carrito.map((linea) => linea.id === producto.id ? { ...linea, cantidad: linea.cantidad + 1 } : linea));
      return;
    }
    if (producto.stock < 1) {
      setError(`${producto.nombre} está agotado.`);
      return;
    }
    setCarrito([...carrito, { id: producto.id, nombre: producto.nombre, precio: producto.precio, stock: producto.stock, cantidad: 1 }]);
  }

  function cambiarCantidad(id, cantidad) {
    const producto = carrito.find((linea) => linea.id === id);
    if (!producto) return;
    if (cantidad < 1) {
      setCarrito((actual) => actual.filter((linea) => linea.id !== id));
      return;
    }
    if (cantidad > producto.stock) {
      setError(`Stock máximo de ${producto.nombre}: ${producto.stock}.`);
      return;
    }
    setCarrito((actual) => actual.map((linea) => linea.id === id ? { ...linea, cantidad } : linea));
    setError("");
  }

  async function registrarPedido(event) {
    event.preventDefault();
    if (carrito.length === 0) {
      setError("Agrega al menos un producto al pedido.");
      return;
    }
    setGuardando(true);
    setError("");
    setAviso("");
    try {
      const pedido = await pedidosApi.crear({
        mesa: Number(mesa),
        detalles: carrito.map((linea) => ({ producto: linea.id, cantidad: linea.cantidad })),
      });
      setCarrito([]);
      setAviso(`Pedido #${pedido.id} registrado para la Mesa ${pedido.mesa}. Ahora realiza el cobro.`);
      await alCrear();
    } catch (e) {
      setError(e.message);
      await cargarCatalogo();
    } finally {
      setGuardando(false);
    }
  }

  return (
    <section className="panel caja-nuevo-pedido">
      <div className="tabla-cabecera">
        <div>
          <p className="sobretitulo">Atención en caja</p>
          <h2>Registrar nuevo pedido</h2>
          <p className="detalle">El cajero selecciona los productos, asigna la mesa y registra el cobro.</p>
        </div>
        <label className="selector-mesa">Mesa
          <select value={mesa} onChange={(event) => setMesa(event.target.value)}>
            {MESAS.map((numero) => <option key={numero} value={numero}>Mesa {numero}</option>)}
          </select>
        </label>
      </div>

      <div className="caja-constructor">
        <div>
          <div className="buscador caja-buscador">
            <input aria-label="Buscar producto para el pedido" placeholder="Buscar producto…" value={busqueda}
              onChange={(event) => setBusqueda(event.target.value)} />
          </div>
          <div className="chips" role="group" aria-label="Categorías de productos para el pedido">
            <button className={`chip ${categoria === "" ? "activo" : ""}`} onClick={() => setCategoria("")}>Todos</button>
            {categorias.map((item) => (
              <button key={item.id} className={`chip ${categoria === String(item.id) ? "activo" : ""}`}
                onClick={() => setCategoria(String(item.id))}>{item.nombre}</button>
            ))}
          </div>
          {cargando && <p className="vacio">Cargando catálogo…</p>}
          <div className="productos-caja">
            {visibles.map((producto) => (
              <article className="producto producto-caja" key={producto.id}>
                <ImagenProducto src={producto.imagen} nombre={producto.nombre} />
                <div className="producto-informacion">
                  <h3>{producto.nombre}</h3>
                  <p className="detalle">{producto.categoria_nombre}</p>
                  <strong className="precio">{moneda(producto.precio)}</strong>
                </div>
                <div className="producto-derecha">
                  <StockBadge stock={producto.stock} />
                  <button className="btn-secundario" disabled={producto.stock < 1 || cargando}
                    onClick={() => agregar(producto)}>{producto.stock < 1 ? "Agotado" : "Agregar"}</button>
                </div>
              </article>
            ))}
            {!cargando && visibles.length === 0 && <p className="vacio">No se encontraron productos.</p>}
          </div>
        </div>

        <aside className="carrito-caja">
          <div className="pedido-operacion-cabecera">
            <div><p className="sobretitulo">Mesa {mesa}</p><h2>Carrito</h2></div>
            <span className="contador">{carrito.reduce((suma, linea) => suma + linea.cantidad, 0)} artículos</span>
          </div>
          {carrito.length === 0 ? <p className="vacio">Selecciona productos para comenzar el pedido.</p> : (
            <ul className="carrito-lista">
              {carrito.map((linea) => (
                <li key={linea.id}>
                  <div><b>{linea.nombre}</b><small>{moneda(linea.precio)} c/u</small></div>
                  <div className="cantidad-control">
                    <button type="button" className="btn-texto" aria-label={`Quitar una unidad de ${linea.nombre}`}
                      onClick={() => cambiarCantidad(linea.id, linea.cantidad - 1)}>−</button>
                    <strong>{linea.cantidad}</strong>
                    <button type="button" className="btn-texto" aria-label={`Agregar una unidad de ${linea.nombre}`}
                      disabled={linea.cantidad >= linea.stock}
                      onClick={() => cambiarCantidad(linea.id, linea.cantidad + 1)}>+</button>
                  </div>
                </li>
              ))}
            </ul>
          )}
          <div className="carrito-total"><span>Total del pedido</span><strong>{moneda(total)}</strong></div>
          <button className="btn" disabled={guardando || carrito.length === 0} onClick={registrarPedido}>
            {guardando ? "Registrando…" : "Registrar pedido y pasar al cobro"}
          </button>
        </aside>
      </div>
      {error && <p className="error" role="alert">{error}</p>}
      {aviso && <p className="aviso" role="status">{aviso}</p>}
    </section>
  );
}

function PedidoCaja({ pedido, alActualizar }) {
  const [metodo, setMetodo] = useState("EFECTIVO");
  const [monto, setMonto] = useState(pedido.total);
  const [referencia, setReferencia] = useState("");
  const [montoReembolso, setMontoReembolso] = useState("");
  const [motivo, setMotivo] = useState("");
  const [qrDisponible, setQrDisponible] = useState(true);
  const [ocupado, setOcupado] = useState(false);
  const [error, setError] = useState("");
  const [aviso, setAviso] = useState("");
  const pago = pedido.pago;
  const reembolsado = Number(pago?.reembolsado ?? 0);
  const disponible = Math.max(0, Number(pedido.total) - reembolsado);

  async function ejecutar(accion, mensaje, filtroSiguiente = null) {
    setOcupado(true);
    setError("");
    setAviso("");
    try {
      await accion();
      setAviso(mensaje);
      await alActualizar(filtroSiguiente);
    } catch (e) {
      setError(e.message);
    } finally {
      setOcupado(false);
    }
  }

  function cobrar(event) {
    event.preventDefault();
    ejecutar(
      () => pedidosApi.registrarPago(pedido.id, {
        metodo,
        monto_recibido: metodo === "QR" ? pedido.total : monto,
        referencia_comprobante: referencia,
      }),
      metodo === "QR"
        ? "Referencia registrada. Verifica que el dinero haya llegado antes de confirmar el pago."
        : "Cobro registrado. El pedido fue enviado a cocina.",
      metodo === "QR" ? "verificar" : "pagados",
    );
  }

  function reembolsar(event) {
    event.preventDefault();
    ejecutar(
      () => pedidosApi.registrarReembolso(pedido.id, { monto: montoReembolso, motivo }),
      "Reembolso registrado.",
    );
    setMontoReembolso("");
    setMotivo("");
  }

  return (
    <article className="pedido-operacion">
      <header className="pedido-operacion-cabecera">
        <div>
          <p className="sobretitulo">Pedido · Mesa {pedido.mesa}</p>
          <h2>#{pedido.id}</h2>
          <p className="detalle">Registrado por: {pedido.registrado_por || "Caja"}</p>
        </div>
        <strong className="total-pedido">{moneda(pedido.total)}</strong>
      </header>
      <ul className="lineas-pedido">
        {pedido.detalles.map((detalle) => (
          <li key={detalle.id}><span>{detalle.cantidad}× {detalle.producto}</span><span>{moneda(detalle.subtotal)}</span></li>
        ))}
      </ul>

      {!pago && pedido.estado === "PENDIENTE_PAGO" && (
        <form className="form-cobro" onSubmit={cobrar}>
          <label>Método de pago
            <select value={metodo} onChange={(event) => setMetodo(event.target.value)}>
              <option value="EFECTIVO">Efectivo</option>
              <option value="QR">QR</option>
            </select>
          </label>
          {metodo === "QR" ? (
            <div className="qr-empresa">
              <p><b>QR de la empresa</b></p>
              {qrDisponible ? (
                <img src="/qr-empresa.png" alt="Código QR de pago de la empresa"
                  onError={() => setQrDisponible(false)} />
              ) : (
                <div className="qr-placeholder">
                  <span>QR EMPRESA</span>
                  <small>Coloca la imagen en<br /><code>public/qr-empresa.png</code></small>
                </div>
              )}
              <p className="detalle">El cajero debe comprobar el abono en la cuenta antes de verificarlo aquí.</p>
            </div>
          ) : (
            <label>Monto recibido (Bs)
              <input type="number" min={pedido.total} step="0.01" value={monto}
                onChange={(event) => setMonto(event.target.value)} required />
            </label>
          )}
          {metodo === "QR" && (
            <label>Referencia o número de comprobante
              <input value={referencia} onChange={(event) => setReferencia(event.target.value)} maxLength="120" required />
            </label>
          )}
          {metodo === "EFECTIVO" && Number(monto) >= Number(pedido.total) && (
            <p className="detalle">Cambio: <strong>{moneda(Number(monto) - Number(pedido.total))}</strong></p>
          )}
          <button className="btn" disabled={ocupado}>{ocupado ? "Guardando…" : metodo === "QR" ? "Registrar comprobante QR" : "Confirmar cobro y enviar a cocina"}</button>
        </form>
      )}

      {pago && (
        <div className="resumen-pago">
          <p><b>{pago.metodo === "QR" ? "Pago QR" : "Pago en efectivo"}</b> · {pago.verificado ? "Verificado" : "Pendiente de verificación"}</p>
          {pago.metodo === "QR" && <p className="detalle">Comprobante: {pago.referencia_comprobante}</p>}
          {pago.metodo === "EFECTIVO" && <p className="detalle">Recibido: {moneda(pago.monto_recibido)} · Cambio: {moneda(pago.cambio)}</p>}
          {!pago.verificado && pago.metodo === "QR" && (
            <button className="btn-secundario" disabled={ocupado} onClick={() =>
              ejecutar(() => pedidosApi.verificarQr(pedido.id), "Pago QR verificado. El pedido fue enviado a cocina.", "pagados")
            }>Confirmar que el pago QR llegó</button>
          )}
          {pago.verificado && (
            <>
              <p className="detalle">Estado del pedido: {pedido.estado.replaceAll("_", " ").toLowerCase()}</p>
              <p className="detalle">Reembolsado: {moneda(reembolsado)} · Disponible: {moneda(disponible)}</p>
              {pago.reembolsos?.map((reembolso) => (
                <p className="detalle" key={reembolso.id}>{moneda(reembolso.monto)} · {reembolso.motivo}</p>
              ))}
              {disponible > 0 && pedido.estado === "ENTREGADO" && (
                <form className="form-cobro form-reembolso" onSubmit={reembolsar}>
                  <label>Monto a reembolsar (máx. {moneda(disponible)})
                    <input type="number" min="0.01" max={disponible} step="0.01" value={montoReembolso}
                      onChange={(event) => setMontoReembolso(event.target.value)} required />
                  </label>
                  <label>Motivo
                    <input value={motivo} onChange={(event) => setMotivo(event.target.value)} maxLength="240" required />
                  </label>
                  <button className="btn-secundario" disabled={ocupado}>Registrar reembolso</button>
                </form>
              )}
            </>
          )}
        </div>
      )}
      {error && <p className="error" role="alert">{error}</p>}
      {aviso && <p className="aviso" role="status">{aviso}</p>}
    </article>
  );
}

export default function VistaCaja() {
  const [pedidos, setPedidos] = useState([]);
  const [error, setError] = useState("");
  const [filtro, setFiltro] = useState("pendientes");
  const [versionCatalogo, setVersionCatalogo] = useState(0);

  const cargar = useCallback(async (filtroSiguiente = null) => {
    try {
      setPedidos(await pedidosApi.listarCaja());
      if (filtroSiguiente) setFiltro(filtroSiguiente);
      if (filtroSiguiente === "pagados") setVersionCatalogo((version) => version + 1);
      setError("");
    } catch (e) {
      setError(e.message);
    }
  }, []);

  useEffect(() => {
    cargar();
    const timer = setInterval(cargar, 5000);
    return () => clearInterval(timer);
  }, [cargar]);

  const visibles = pedidos.filter((pedido) => {
    if (filtro === "pendientes") return !pedido.pago;
    if (filtro === "verificar") return Boolean(pedido.pago && !pedido.pago.verificado);
    return pedido.pago?.verificado;
  });

  return (
    <section>
      <header className="encabezado">
        <div>
          <p className="sobretitulo">Operaciones</p>
          <h1>Caja</h1>
          <p className="detalle">Registra el pedido, asigna una de las 10 mesas y cobra antes de enviarlo a cocina.</p>
        </div>
        <button className="btn-secundario" onClick={cargar}>Actualizar</button>
      </header>

      <NuevoPedidoCaja alCrear={cargar} refreshToken={versionCatalogo} />

      <section className="caja-pedidos">
        <div className="tabla-cabecera"><div><h2>Pedidos registrados</h2><p className="detalle">Seguimiento de cobros y pedidos enviados a cocina.</p></div></div>
        <div className="chips" role="group" aria-label="Filtrar pedidos de caja">
          {[["pendientes", "Por cobrar"], ["verificar", "Verificar QR"], ["pagados", "Pagados / en proceso"]].map(([id, titulo]) => (
            <button key={id} className={`chip ${filtro === id ? "activo" : ""}`} onClick={() => setFiltro(id)}>{titulo}</button>
          ))}
        </div>
        {error && <p className="error" role="alert">{error}</p>}
        {visibles.length === 0 && !error && <p className="vacio">No hay pedidos en esta sección.</p>}
        <div className="lista-operaciones">
          {visibles.map((pedido) => <PedidoCaja key={pedido.id} pedido={pedido} alActualizar={cargar} />)}
        </div>
      </section>
    </section>
  );
}
