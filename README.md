# Baby shower de Eliz Maribeth

Aplicación React + FastAPI + MongoDB Atlas para reservar regalos. La vista pública tiene ilustraciones para los 16 regalos, filtros por categoría y disponibilidad, una elección sorpresa y una búsqueda para recordar un regalo mediante el primer nombre y primer apellido usados en la reserva, sin mostrar la lista de nombres. El panel de administración permite ver reservas, agregar y editar regalos, quitar reservas y eliminar regalos sin reservas.

## Inicio rápido

1. Crea un clúster en MongoDB Atlas y permite la IP desde la que correrá el backend. Copia su URI de conexión.
2. Copia `backend/.env.example` a `backend/.env`. Completa `MONGODB_URI`, `ADMIN_PASSWORD` y `SECRET_KEY` con valores propios. Nunca subas este archivo al repositorio.
3. Instala las dependencias del backend y ejecútalo:

   ```powershell
   cd backend
   py -m venv .venv
   .\.venv\Scripts\Activate.ps1
   pip install -r requirements.txt
   uvicorn main:app --reload
   ```

4. En otra terminal, desde la raíz del proyecto:

   ```powershell
   npm install
   npm run dev
   ```

5. Abre `http://127.0.0.1:5173`. El panel privado se abre directamente en `http://127.0.0.1:5173/admin` y requiere contraseña. No aparece en la navegación pública.

Para revisar el diseño sin Atlas, ejecuta `npm run dev:api` en otra terminal antes de abrir el frontend. Este servidor de muestra conserva las reservas solo mientras esté encendido; para datos reales usa FastAPI y Atlas. En esta vista local, el panel acepta cualquier contraseña de prueba.

Si el backend está en otra dirección, copia `.env.example` a `.env` y cambia `VITE_API_URL`. Configura también `CORS_ORIGINS` en `backend/.env` con el origen del frontend.

La primera vez que el backend inicia con la colección vacía, agrega los 16 regalos proporcionados. Cada uno comienza con una unidad disponible; puedes ajustar cantidades y detalles desde el panel.

## Despliegue en Vercel

El repositorio ya incluye `vercel.json`, la función Python `api/index.py`, `requirements.txt` y `.python-version`. Importa la **raíz del repositorio** en Vercel, con Framework Preset `Vite`, Build Command `npm run build` y Output Directory `dist`.

En **Project Settings → Environment Variables**, agrega estos valores para Production (y Preview si vas a usar esas implementaciones):

| Variable | Valor |
| --- | --- |
| `MONGODB_URI` | URI de Atlas con el usuario y contraseña de la base de datos; usa el valor de `backend/.env` local y no lo pegues en el código ni en Git. |
| `MONGODB_DB` | `babyshower_eliz` |
| `ADMIN_PASSWORD` | Contraseña propia para entrar a `/admin`. El archivo local `backend/.env` contiene una generada para pruebas. |
| `SECRET_KEY` | Cadena aleatoria larga para firmar la sesión; el archivo local contiene una generada. |

No definas `VITE_API_URL` en Vercel: el frontend usa `/api` en el mismo dominio. Tampoco necesitas `CORS_ORIGINS` allí. Después del despliegue, prueba `/api/health`, la página principal y `/admin`.

Atlas solo tiene autorizada la IP local de la captura. Las funciones de Vercel salen por IP dinámicas, así que debes permitir su acceso en **Atlas → Network Access** o configurar una salida fija de Vercel. La opción habitual `0.0.0.0/0` permite conexiones desde cualquier IP: mantenla solo con una contraseña fuerte y un usuario de base de datos con permisos limitados a esta aplicación. El usuario mostrado en la captura tiene rol Atlas Admin; conviene sustituirlo por uno con `readWrite` en `babyshower_eliz` antes de publicar.

Las credenciales visibles en la captura deben considerarse expuestas. Rota la contraseña del usuario de Atlas después de configurar Vercel y actualiza `MONGODB_URI` allí y en el archivo local ignorado por Git.
