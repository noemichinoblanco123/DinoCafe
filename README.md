# DinoCafé — sistema de pedidos, cobro y entrega

Aplicación de gestión para cafetería con frontend React + Vite y backend Django + Django REST Framework. Conserva la interfaz y las dependencias del proyecto base y aplica el flujo acordado:

1. El cliente consulta el catálogo público sin iniciar sesión ni registrar pedidos.
2. El cajero registra los productos, cantidades y una de las 10 mesas.
3. El cajero cobra en efectivo o registra un comprobante QR y verifica manualmente la recepción del dinero.
4. Solo después de un pago verificado, el pedido aparece en cocina.
5. Cocina marca el pedido en preparación y luego listo.
6. El mesero recibe el aviso del pedido listo, lo lleva a la mesa y confirma la entrega.
7. Administración supervisa pedidos, mesas, cobros, responsables y marcas de tiempo en todas las etapas.

## Tecnologías

- Frontend: React 18, Vite 5, JavaScript y CSS.
- Backend: Python, Django 5.1, Django REST Framework y SimpleJWT.
- Datos local: SQLite (`backend/db.sqlite3`).
- Datos en Docker: PostgreSQL 16.
- Entorno opcional: Docker Compose.

## Estructura

```text
DinoCafe-Frontend-main/
├── frontend/dinocafe-frontend/  # React + Vite
│   ├── public/                  # Colocar aquí qr-empresa.png
│   └── src/components/          # Vistas de catálogo, caja, cocina, mesero y administración
├── backend/                     # Django + DRF
│   ├── catalogo/                # Categorías y productos
│   ├── pedidos/                 # Pedidos, detalle, pago, reembolsos y estados
│   ├── usuarios/                # Roles y autenticación
│   └── dinocafe/                # Configuración y permisos
└── docker-compose.yml
```

## Ejecución local en Windows (SQLite)

Requisitos: Python 3.12 o superior y Node.js 20 o superior.

### 1. Backend

Abre PowerShell en la carpeta del proyecto:

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe manage.py migrate
.\.venv\Scripts\python.exe manage.py seed_demo
.\.venv\Scripts\python.exe manage.py runserver 127.0.0.1:8000
```

Mantén esa terminal abierta. El catálogo público queda disponible mediante la API en `http://localhost:8000/api/`.

### 2. Frontend

Abre una segunda terminal:

```powershell
cd frontend\dinocafe-frontend
npm install
copy .env.example .env
npm run dev
```

Abre `http://localhost:5173`. La primera pantalla es el catálogo público; para entrar a los módulos internos usa **Acceso del personal**.

### 3. Reiniciar los datos de demostración

Para volver a crear los pedidos de ejemplo:

```powershell
cd backend
.\.venv\Scripts\python.exe manage.py seed_demo --reset-pedidos
```

Este comando elimina únicamente pedidos, sus pagos y reembolsos de demostración, y vuelve a generarlos.

## Cuentas de demostración

| Usuario | Contraseña | Rol | Permisos principales |
|---|---|---|---|
| `admin` | `admin123` | Administrador | Seguimiento completo, catálogo, cocina, reportes y usuarios |
| `cajero` | `cajero123` | Cajero | Registrar productos del pedido, asignar mesa y cobrar |
| `cocina` | `cocina123` | Cocina | Recibir pedidos pagados y marcar preparación/listo |
| `mesero` | `mesero123` | Mesero | Ver pedidos listos y confirmar entrega |

Estas contraseñas son solo para desarrollo y no deben utilizarse en producción.

## Flujo de pagos

- Efectivo: el cajero introduce el monto recibido; el sistema calcula el cambio, descuenta el stock y libera inmediatamente el pedido a cocina.
- QR: el frontend muestra `/qr-empresa.png`; el cajero registra la referencia y confirma manualmente el pago después de comprobar el abono en la cuenta. Solo entonces el sistema descuenta el stock y libera el pedido a cocina.
- El proyecto no se conecta a una pasarela bancaria ni comprueba transferencias automáticamente.

### Colocar el QR real de la empresa

Copia la imagen QR que proporcione la empresa en:

```text
frontend/dinocafe-frontend/public/qr-empresa.png
```

No se incluye un QR bancario en esta entrega. Mientras no coloques la imagen, la caja mostrará un espacio indicativo.

## Estados y reglas de acceso

| Estado | Responsable / evento |
|---|---|
| `PENDIENTE_PAGO` | Caja registró pedido; aún no llega a cocina |
| `ESPERA` | Pago efectivo o QR verificado; disponible para cocina |
| `EN_PREPARACION` | Cocina inició la preparación |
| `LISTO` | Cocina terminó; se notifica al mesero |
| `ENTREGADO` | Mesero confirma que llevó el pedido a la mesa |

- Catálogo: lectura pública sin login; crear, editar, desactivar y reactivar productos solo administrador.
- Los productos agotados aparecen identificados como “Agotado” y el botón para agregarlos al carrito de caja queda deshabilitado. El backend vuelve a validar activo y stock al registrar el pedido.
- Baja lógica: desactivar un producto cambia `activo` a falso. No se borra físicamente y puede reactivarse cuando vuelva la temporada. Los productos inactivos no aparecen en el catálogo público ni en la lista de caja.
- Crear pedidos, asignar mesa y registrar/verificar pagos: solo cajero.
- Avanzar estados de preparación: solo cocina.
- Confirmar entrega: solo mesero.
- Seguimiento general: solo administrador.
- Las mesas están limitadas a Mesa 1 hasta Mesa 10. El stock del producto se descuenta al confirmar el pago (efectivo o QR verificado), no al dejar un pedido sin cobrar.
- El servidor guarda quién registró, inició, marcó listo y entregó cada pedido, además de sus marcas de tiempo.

## Imágenes del catálogo

Las imágenes se sirven desde `frontend/dinocafe-frontend/public/`; no necesitas configurar un servidor de archivos. La migración deja preparadas estas rutas y la aplicación muestra un recuadro de reemplazo mientras no hayas copiado las fotografías.

**Carrusel superior por categoría:**

- `public/images/carrusel/bebidas.jpg`
- `public/images/carrusel/acompanamientos.jpg`

**Fotografías de productos:**

- `public/images/productos/te.jpg`
- `public/images/productos/cafe.jpg`
- `public/images/productos/cocoa.jpg`
- `public/images/productos/cocoa-con-leche.jpg`
- `public/images/productos/leche.jpg`
- `public/images/productos/pan.jpg`
- `public/images/productos/empanada.jpg`
- `public/images/productos/trozo-de-torta.jpg`
- `public/images/productos/trozo-de-rollo.jpg`
- `public/images/productos/sandwich-de-huevo.jpg`

Puedes usar otros nombres: en el formulario de producto, el administrador escribe la ruta pública en el campo **Ruta de imagen** (por ejemplo, `/images/productos/cafe.jpg`). Los archivos del carrusel pueden reemplazarse directamente por tus propias imágenes conservando esos nombres. Formatos recomendados: JPG o PNG; conserva la extensión indicada en la ruta.

## Base de datos

Modelos propios del negocio:

- `usuarios_usuario`: cuentas y roles.
- `catalogo_categoria`: categorías y ruta de imagen del carrusel.
- `catalogo_producto`: productos, precios, stock, ruta de imagen y estado activo/inactivo.
- `pedidos_pedido`: mesa, estado, responsables y marcas de tiempo.
- `pedidos_detallepedido`: productos, cantidades y precio unitario histórico.
- `pedidos_pago`: método, monto y verificación del pago.
- `pedidos_reembolso`: devoluciones registradas.

Django crea además sus tablas internas de autenticación, permisos, sesiones y administración.

## Pruebas

Backend:

```powershell
cd backend
.\.venv\Scripts\python.exe manage.py test
```

Contrato de integración (backend y frontend levantados en terminales distintas):

```powershell
node backend/scripts/smoke_api.mjs
```

Frontend:

```powershell
cd frontend\dinocafe-frontend
npm test
npm run build
```

## Docker opcional (PostgreSQL + Django + React)

Desde la raíz:

```powershell
Copy-Item .env.example .env
docker compose up --build
```

Por defecto: frontend `http://localhost:5173`, API `http://localhost:8000/api/` y PostgreSQL en el puerto `5432`.
