import { useEffect, useState } from "react";
import { getRol, reportesApi } from "../api";

function fechaLocal() {
  const hoy = new Date();
  hoy.setMinutes(hoy.getMinutes() - hoy.getTimezoneOffset());
  return hoy.toISOString().slice(0, 10);
}

function moneda(valor) {
  return new Intl.NumberFormat("es-BO", { style: "currency", currency: "BOB" }).format(Number(valor));
}

export default function ReportesVentas() {
  const esCaja = getRol() === "cajero";
  const [desde, setDesde] = useState(fechaLocal);
  const [hasta, setHasta] = useState(fechaLocal);
  const [reporte, setReporte] = useState(null);
  const [cargando, setCargando] = useState(false);
  const [error, setError] = useState("");

  async function consultar(event) {
    event?.preventDefault();
    setCargando(true);
    setError("");
    try {
      setReporte(await reportesApi.ventas(desde, hasta));
    } catch (e) {
      setError(e.message);
    } finally {
      setCargando(false);
    }
  }

  useEffect(() => { consultar(); }, []);

  return (
    <section>
      <header className="encabezado">
        <div>
          <p className="sobretitulo">{esCaja ? "Conciliación diaria" : "Administración"}</p>
          <h1>{esCaja ? "Ventas del día" : "Reportes de ventas"}</h1>
          <p className="detalle">{esCaja ? "Resumen de cobros y reembolsos de hoy." : "Consulta ventas por producto, categoría y periodo."}</p>
        </div>
      </header>
      <form className="filtros-periodo" onSubmit={consultar}>
        <label>Desde
          <input type="date" value={desde} max={hasta} onChange={(event) => setDesde(event.target.value)} disabled={esCaja} />
        </label>
        <label>Hasta
          <input type="date" value={hasta} min={desde} max={fechaLocal()} onChange={(event) => setHasta(event.target.value)} disabled={esCaja} />
        </label>
        {!esCaja && <button className="btn" disabled={cargando}>{cargando ? "Consultando…" : "Consultar periodo"}</button>}
        {esCaja && <button className="btn-secundario" disabled={cargando}>{cargando ? "Actualizando…" : "Conciliar de nuevo"}</button>}
      </form>
      {error && <p className="error" role="alert">{error}</p>}
      {reporte && (
        <>
          <div className="resumen-ventas">
            <article className="indicador"><span>Ventas brutas</span><strong>{moneda(reporte.ventas_brutas)}</strong></article>
            <article className="indicador"><span>Reembolsos</span><strong>{moneda(reporte.reembolsos)}</strong></article>
            <article className="indicador indicador-destacado"><span>Ventas netas</span><strong>{moneda(reporte.ventas_net)}</strong></article>
            <article className="indicador"><span>Pedidos cobrados</span><strong>{reporte.cantidad_pedidos}</strong></article>
          </div>
          <div className="reportes-grid">
            <section className="panel reporte-panel">
              <h2>Por método de pago</h2>
              {reporte.por_metodo.length === 0 ? <p className="vacio">Sin ventas para este periodo.</p> : (
                <ul className="reporte-lista">
                  {reporte.por_metodo.map((fila) => (
                    <li key={fila.metodo}><span>{fila.metodo === "EFECTIVO" ? "Efectivo" : "QR"}</span><strong>{moneda(fila.total)}</strong></li>
                  ))}
                </ul>
              )}
            </section>
            <section className="panel reporte-panel">
              <h2>Por categoría</h2>
              {reporte.categorias.length === 0 ? <p className="vacio">Sin ventas para este periodo.</p> : (
                <ul className="reporte-lista">
                  {reporte.categorias.map((fila) => (
                    <li key={fila.categoria}><span>{fila.categoria} <small>{fila.unidades} unidades</small></span><strong>{moneda(fila.total)}</strong></li>
                  ))}
                </ul>
              )}
            </section>
          </div>
          <section className="panel tabla-panel">
            <div className="tabla-cabecera"><h2>Ventas por producto</h2><span className="detalle">{reporte.desde} — {reporte.hasta}</span></div>
            <div className="tabla-scroll">
              <table>
                <thead><tr><th>Producto</th><th>Categoría</th><th>Unidades</th><th>Total</th></tr></thead>
                <tbody>
                  {reporte.productos.map((fila) => (
                    <tr key={fila.id}><td>{fila.nombre}</td><td>{fila.categoria}</td><td>{fila.unidades}</td><td>{moneda(fila.total)}</td></tr>
                  ))}
                  {reporte.productos.length === 0 && <tr><td colSpan="4" className="vacio">Sin ventas para este periodo.</td></tr>}
                </tbody>
              </table>
            </div>
          </section>
        </>
      )}
    </section>
  );
}
