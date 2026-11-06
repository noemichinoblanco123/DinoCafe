import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { authApi, guardarSesion } from "./api";

function respuesta(status, datos) {
  return {
    ok: status >= 200 && status < 300,
    status,
    json: async () => datos,
  };
}

describe("API: renovación de sesión", () => {
  beforeEach(() => {
    localStorage.clear();
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("renueva el token de acceso y reintenta la petición protegida", async () => {
    guardarSesion({
      access: "access-vencido",
      refresh: "refresh-valido",
      rol: "mesero",
      username: "ana",
    });
    const fetch = vi.fn()
      .mockResolvedValueOnce(respuesta(401, { detail: "Token expirado" }))
      .mockResolvedValueOnce(respuesta(200, { access: "access-nuevo" }))
      .mockResolvedValueOnce(respuesta(200, { username: "ana", rol: "mesero" }));
    vi.stubGlobal("fetch", fetch);

    await expect(authApi.me()).resolves.toEqual({ username: "ana", rol: "mesero" });
    expect(fetch).toHaveBeenCalledTimes(3);
    expect(fetch.mock.calls[0][1].headers.Authorization).toBe("Bearer access-vencido");
    expect(fetch.mock.calls[1][0]).toContain("/auth/refresh/");
    expect(fetch.mock.calls[2][1].headers.Authorization).toBe("Bearer access-nuevo");
    expect(localStorage.getItem("access_token")).toBe("access-nuevo");
    expect(localStorage.getItem("refresh_token")).toBe("refresh-valido");
  });

  it("borra la sesión cuando el refresh token ya no es válido", async () => {
    guardarSesion({
      access: "access-vencido",
      refresh: "refresh-vencido",
      rol: "mesero",
      username: "ana",
    });
    const fetch = vi.fn()
      .mockResolvedValueOnce(respuesta(401, { detail: "Token expirado" }))
      .mockResolvedValueOnce(respuesta(401, { detail: "Refresh inválido" }));
    vi.stubGlobal("fetch", fetch);

    await expect(authApi.me()).rejects.toMatchObject({ status: 401 });
    expect(localStorage.getItem("access_token")).toBeNull();
    expect(localStorage.getItem("refresh_token")).toBeNull();
  });
});
