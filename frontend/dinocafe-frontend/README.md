# DinoCafé — frontend React + Vite

Interfaz de catálogo público y operación interna de la cafetería. Conserva React 18, Vite 5 y la hoja de estilos del proyecto original.

## Vistas

- **Catálogo público:** lectura sin iniciar sesión; el cliente consulta productos, categorías, precios y disponibilidad. No registra pedidos.
- **Caja:** cajero selecciona productos, cantidades, asigna una de las diez mesas y registra el pago.
- **Cocina:** recibe exclusivamente pedidos con pago verificado; marca en preparación y listo.
- **Entregas:** el mesero recibe avisos de pedidos listos y solo confirma la entrega.
- **Seguimiento:** administración observa todos los pedidos, mesas, pagos, responsables y fechas.
- **Productos, ventas y usuarios:** funciones de administración y conciliación.

## Ejecutar

El backend Django debe estar levantado en `http://localhost:8000`.

```powershell
npm install
copy .env.example .env
npm run dev
```

Abre `http://localhost:5173`.

## QR empresarial

Coloca el archivo real de la empresa en `public/qr-empresa.png`. Si no existe, la pantalla de caja muestra un espacio de reemplazo. La verificación del QR es manual; esta aplicación no se conecta a un banco.

## Cuentas de demostración

| Usuario | Contraseña | Rol |
|---|---|---|
| admin | admin123 | administrador |
| cajero | cajero123 | cajero |
| cocina | cocina123 | cocina |
| mesero | mesero123 | mesero |

## Pruebas

```powershell
npm test
npm run build
```

La API REST se centraliza en `src/api.js`; los componentes mantienen la presentación y las reglas de interfaz en `src/components/`. Los estilos se conservan en `src/styles.css`.
