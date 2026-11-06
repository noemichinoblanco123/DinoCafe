import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { pedidosApi, productosApi } from "../api";
import VistaCaja from "./VistaCaja";

vi.mock("../api", () => ({
  pedidosApi: {
    crear: vi.fn(),
    listarCaja: vi.fn(),
    registrarPago: vi.fn(),
    verificarQr: vi.fn(),
    registrarReembolso: vi.fn(),
  },
  productosApi: { listar: vi.fn(), categorias: vi.fn() },
}));

const PRODUCTO = { id: 2, nombre: "Té", categoria: 1, categoria_nombre: "Bebidas", precio: "5.00", stock: 8 };
const PEDIDO = {
  id: 4, mesa: 3, estado: "PENDIENTE_PAGO", total: "10.00", pago: null, registrado_por: "cajero",
  detalles: [{ id: 1, producto: "Té", cantidad: 2, subtotal: "10.00" }],
};

describe("VistaCaja: registra productos, mesa y pago", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    pedidosApi.listarCaja.mockResolvedValue([]);
    pedidosApi.crear.mockResolvedValue(PEDIDO);
    pedidosApi.registrarPago.mockResolvedValue({ verificado: true });
    productosApi.listar.mockResolvedValue([PRODUCTO]);
    productosApi.categorias.mockResolvedValue([{ id: 1, nombre: "Bebidas" }]);
  });

  it("construye el carrito, asigna mesa y registra el pedido como caja", async () => {
    render(<VistaCaja />);
    expect(await screen.findByText("Té")).toBeInTheDocument();
    fireEvent.change(screen.getByLabelText("Mesa"), { target: { value: "6" } });
    fireEvent.click(screen.getByRole("button", { name: "Agregar" }));
    expect(screen.getByText("1 artículos")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Registrar pedido y pasar al cobro" }));

    await waitFor(() => expect(pedidosApi.crear).toHaveBeenCalledWith({
      mesa: 6,
      detalles: [{ producto: 2, cantidad: 1 }],
    }));
  });

  it("no permite agregar productos agotados al carrito", async () => {
    productosApi.listar.mockResolvedValue([
      PRODUCTO,
      { ...PRODUCTO, id: 3, nombre: "Cocoa", stock: 0 },
    ]);
    render(<VistaCaja />);
    expect(await screen.findByText("Cocoa")).toBeInTheDocument();
    const botonAgotado = screen.getByRole("button", { name: "Agotado" });
    expect(botonAgotado).toBeDisabled();
    fireEvent.click(screen.getByRole("button", { name: "Agregar" }));
    expect(screen.getByText("1 artículos")).toBeInTheDocument();
  });

  it("registra un cobro en efectivo con cálculo de cambio", async () => {
    pedidosApi.listarCaja.mockResolvedValue([PEDIDO]);
    render(<VistaCaja />);
    expect(await screen.findByText("#4")).toBeInTheDocument();
    fireEvent.change(screen.getByLabelText("Monto recibido (Bs)"), { target: { value: "20.00" } });
    expect(screen.getByText(/Cambio:/)).toHaveTextContent("Bs 10,00");
    fireEvent.click(screen.getByRole("button", { name: "Confirmar cobro y enviar a cocina" }));

    await waitFor(() => expect(pedidosApi.registrarPago).toHaveBeenCalledWith(4, {
      metodo: "EFECTIVO", monto_recibido: "20.00", referencia_comprobante: "",
    }));
  });

  it("muestra el espacio del QR y registra la referencia del comprobante", async () => {
    pedidosApi.listarCaja.mockResolvedValue([PEDIDO]);
    render(<VistaCaja />);
    await screen.findByText("#4");
    fireEvent.change(screen.getByLabelText("Método de pago"), { target: { value: "QR" } });
    expect(screen.getByAltText("Código QR de pago de la empresa")).toBeInTheDocument();
    fireEvent.change(screen.getByLabelText("Referencia o número de comprobante"), { target: { value: "QR-44" } });
    fireEvent.click(screen.getByRole("button", { name: "Registrar comprobante QR" }));

    await waitFor(() => expect(pedidosApi.registrarPago).toHaveBeenCalledWith(4, {
      metodo: "QR", monto_recibido: "10.00", referencia_comprobante: "QR-44",
    }));
  });
});
