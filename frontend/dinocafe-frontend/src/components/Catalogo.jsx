import { useCallback, useEffect, useState } from "react";
import { getRol, productosApi } from "../api";
import BuscadorProductos from "./BuscadorProductos";
import CarruselCategorias from "./CarruselCategorias";
import ImagenProducto from "./ImagenProducto";
import ProductoForm from "./ProductoForm";
import StockBadge from "./StockBadge";

// RF1 (S1-T04): gestión y consulta del catálogo. RF9 (S2-T08): buscador. RF4 (S2-T02): stock.
export default function Catalogo({ publico = false }) {
  const esAdmin = !publico && getRol() === "administrador";
  const [categorias, setCategorias] = useState([]);
  const [productos, setProductos] = useState([]);
  const [busqueda, setBusqueda] = useState("");
  const [categoria, setCategoria] = useState("");
  const [filtroActivo, setFiltroActivo] = useState("todos");
  const [editando, setEditando] = useState(null); // null | "nuevo" | producto
  const [estado, setEstado] = useState("cargando"); // cargando | listo | error
  const [error, setError] = useState("");
  const [errorCategorias, setErrorCategorias] = useState("");
  const [aviso, setAviso] = useState("");

  const alBuscar = useCallback((q) => setBusqueda(q), []);

  useEffect(() => {
    productosApi.categorias().then(setCategorias).catch((e) => setErrorCategorias(e.message));
  }, []);

  const cargar = useCallback(async () => {
    setEstado("cargando");
    try {
      const activo = esAdmin && filtroActivo !== "todos" ? filtroActivo : "";
      setProductos(await productosApi.listar({ q: busqueda, categoria, activo }));
      setError("");
      setEstado("listo");
    } catch (e) {
      setError(e.message);
      setEstado("error");
    }
  }, [busqueda, categoria, esAdmin, filtroActivo]);

  useEffect(() => { cargar(); }, [cargar]);

  async function guardar(datos) {
    const esNuevo = editando === "nuevo";
    if (esNuevo) await productosApi.crear(datos);
    else await productosApi.actualizar(editando.id, datos);

    setEditando(null);
    setAviso(esNuevo ? "Producto agregado al catálogo." : "Producto actualizado.");
    await cargar();
  }

  async function cambiarActivo(producto) {
    const siguiente = !producto.activo;
    const mensaje = siguiente
      ? `¿Reactivar ${producto.nombre} para volver a venderlo?`
      : `¿Desactivar ${producto.nombre}? Se conservará en el historial y podrás reactivarlo después.`;
    if (!window.confirm(mensaje)) return;

    try {
      await productosApi.actualizar(producto.id, { activo: siguiente });
      setAviso(siguiente ? `${producto.nombre} volvió al catálogo.` : `${producto.nombre} fue desactivado. No se eliminó de la base de datos.`);
      await cargar();
    } catch (e) {
      setError(e.message);
    }
  }

  if (editando) {
    return (
      <ProductoForm
        categorias={categorias}
        puedeCambiarPrecio={esAdmin}
        producto={editando === "nuevo" ? null : editando}
        onGuardar={guardar}
        onCancelar={() => setEditando(null)}
      />
    );
  }

  const resumen = `${productos.length} producto${productos.length === 1 ? "" : "s"}`;

  return (
    <section>
      {publico && <CarruselCategorias categorias={categorias} />}
      <header className="encabezado">
        <div>
          <h1>{publico ? "Menú DinoCafé" : "Catálogo"}</h1>
          {publico && <p className="detalle">Consulta los productos y sus precios. Para realizar un pedido, acércate a caja.</p>}
          {estado === "listo" && (
            <p className="detalle" aria-live="polite">
              {resumen}{busqueda ? ` para “${busqueda}”` : ""}{categoria ? " en la categoría elegida" : ""}
            </p>
          )}
        </div>
        {esAdmin && (
          <button className="btn" onClick={() => { setAviso(""); setEditando("nuevo"); }}>
            Agregar producto
          </button>
        )}
      </header>

      <BuscadorProductos onBuscar={alBuscar} />

      <div className="chips" role="group" aria-label="Filtrar por categoría">
        <button className={`chip ${categoria === "" ? "activo" : ""}`} onClick={() => setCategoria("")}>Todos</button>
        {categorias.map((c) => (
          <button key={c.id} className={`chip ${categoria === String(c.id) ? "activo" : ""}`}
            onClick={() => setCategoria(String(c.id))}>{c.nombre}</button>
        ))}
      </div>

      {esAdmin && (
        <div className="chips filtros-activos" role="group" aria-label="Estado de productos">
          <span className="detalle">Mostrar:</span>
          {[ ["todos", "Todos"], ["true", "Activos"], ["false", "Inactivos"] ].map(([valor, etiqueta]) => (
            <button key={valor} className={`chip ${filtroActivo === valor ? "activo" : ""}`}
              onClick={() => setFiltroActivo(valor)}>{etiqueta}</button>
          ))}
        </div>
      )}

      {aviso && <p className="aviso" role="status">{aviso}</p>}
      {errorCategorias && <p className="error" role="alert">No se pudieron cargar las categorías: {errorCategorias}</p>}
      {estado === "error" && <p className="error" role="alert">No se pudo cargar el catálogo: {error}</p>}
      {estado === "cargando" && <p className="vacio">Cargando productos…</p>}
      {estado === "listo" && productos.length === 0 && (
        <p className="vacio">
          {filtroActivo === "false" ? "No hay productos desactivados." : busqueda ? `No hay productos que coincidan con “${busqueda}”.` : "Aún no hay productos. Agrega el primero."}
        </p>
      )}

      <ul className="lista-productos">
        {productos.map((p) => (
          <li key={p.id} className={`producto ${p.activo === false ? "producto-inactivo" : ""}`}>
            <ImagenProducto src={p.imagen} nombre={p.nombre} />
            <div className="producto-informacion">
              <h3>{p.nombre}</h3>
              <p className="detalle">{p.categoria_nombre}</p>
              {p.activo === false && <span className="producto-inactivo-etiqueta">Desactivado · no se vende</span>}
            </div>
            <div className="producto-derecha">
              <strong className="precio">Bs {p.precio}</strong>
              <StockBadge stock={p.stock} />
              {esAdmin && (
                <>
                  <button className="btn-texto" onClick={() => { setAviso(""); setEditando(p); }}>Editar</button>
                  <button className="btn-texto" onClick={() => cambiarActivo(p)}>
                    {p.activo === false ? "Reactivar" : "Desactivar"}
                  </button>
                </>
              )}
            </div>
          </li>
        ))}
      </ul>
    </section>
  );
}
