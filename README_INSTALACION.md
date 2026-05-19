# Agente Solar Riohacha - Guía de Instalación y Uso

## Descripción del Proyecto

**Agente Solar Riohacha** es una aplicación web monolítica desarrollada en **Laravel 11** con **MySQL** que permite gestionar datos de radiación solar, consumo energético, empresas y generar alertas y reportes. La aplicación cuenta con:

- **API REST completa** para consumo en aplicaciones móviles
- **Interfaz web moderna** con diseño minimalista técnico
- **Vistas Blade** que consumen la API mediante JavaScript Fetch
- **Base de datos relacional** con 8 tablas principales
- **Estilos CSS puros** organizados en carpetas temáticas

---

## Requisitos Previos

- **PHP 8.1+** (se incluye en la instalación)
- **MySQL 8.0+** (se incluye en la instalación)
- **Composer** (se incluye en la instalación)
- **Node.js 16+** (opcional, para compilación de assets)

---

## Instalación

### 1. Clonar o Descargar el Proyecto

```bash
cd /ruta/deseada
git clone <repositorio> agente-solar-riohacha
cd agente-solar-riohacha
```

### 2. Instalar Dependencias

```bash
composer install
```

### 3. Configurar el Archivo `.env`

Copiar el archivo de ejemplo y configurar:

```bash
cp .env.example .env
```

Editar el archivo `.env` con tus credenciales de base de datos:

```env
APP_NAME="Agente Solar Riohacha"
APP_ENV=local
APP_DEBUG=true
APP_URL=http://localhost:8000

DB_CONNECTION=mysql
DB_HOST=127.0.0.1
DB_PORT=3306
DB_DATABASE=agente_solar_riohacha
DB_USERNAME=root
DB_PASSWORD=root
```

### 4. Generar la Clave de Aplicación

```bash
php artisan key:generate
```

### 5. Crear la Base de Datos

```bash
sudo mysql -u root -proot -e "CREATE DATABASE IF NOT EXISTS agente_solar_riohacha CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;"
```

### 6. Ejecutar las Migraciones

```bash
php artisan migrate:fresh
```

### 7. Iniciar el Servidor de Desarrollo

```bash
php artisan serve
```

La aplicación estará disponible en: **http://localhost:8000**

---

## Estructura del Proyecto

```
agente-solar-riohacha/
├── app/
│   ├── Http/
│   │   ├── Controllers/
│   │   │   ├── Api/              # Controladores de API REST
│   │   │   └── Web/              # Controladores de vistas web
│   │   └── Requests/
│   └── Models/                   # Modelos Eloquent
├── database/
│   └── migrations/               # Migraciones de base de datos
├── public/
│   ├── css/
│   │   ├── global.css           # Estilos globales
│   │   ├── layouts/             # Estilos de layouts
│   │   └── components/          # Estilos de componentes
│   └── js/
│       └── api.js               # Cliente de API
├── resources/
│   └── views/
│       ├── layouts/             # Layouts Blade
│       ├── dashboard.blade.php
│       ├── empresas/
│       ├── consumos/
│       ├── radiaciones/
│       ├── alertas/
│       └── reportes/
├── routes/
│   ├── api.php                  # Rutas de API
│   └── web.php                  # Rutas web
└── README_INSTALACION.md
```

---

## Endpoints de la API

### Usuarios
- `GET /api/usuarios` - Listar todos los usuarios
- `POST /api/usuarios` - Crear nuevo usuario
- `GET /api/usuarios/{id}` - Obtener usuario por ID
- `PUT /api/usuarios/{id}` - Actualizar usuario
- `DELETE /api/usuarios/{id}` - Eliminar usuario

### Empresas
- `GET /api/empresas` - Listar todas las empresas
- `POST /api/empresas` - Crear nueva empresa
- `GET /api/empresas/{id}` - Obtener empresa con relaciones
- `PUT /api/empresas/{id}` - Actualizar empresa
- `DELETE /api/empresas/{id}` - Eliminar empresa

### Consumos Energéticos
- `GET /api/consumos` - Listar consumos
- `POST /api/consumos` - Crear nuevo consumo
- `GET /api/consumos/{id}` - Obtener consumo
- `PUT /api/consumos/{id}` - Actualizar consumo
- `DELETE /api/consumos/{id}` - Eliminar consumo

### Radiación Solar
- `GET /api/radiaciones` - Listar radiaciones
- `POST /api/radiaciones` - Crear nuevo registro
- `GET /api/radiaciones/{id}` - Obtener radiación
- `PUT /api/radiaciones/{id}` - Actualizar radiación
- `DELETE /api/radiaciones/{id}` - Eliminar radiación

### Recomendaciones
- `GET /api/recomendaciones` - Listar recomendaciones
- `POST /api/recomendaciones` - Crear recomendación
- `GET /api/recomendaciones/{id}` - Obtener recomendación
- `PUT /api/recomendaciones/{id}` - Actualizar recomendación
- `DELETE /api/recomendaciones/{id}` - Eliminar recomendación

### Alertas
- `GET /api/alertas` - Listar alertas
- `POST /api/alertas` - Crear alerta
- `GET /api/alertas/{id}` - Obtener alerta
- `PUT /api/alertas/{id}` - Actualizar alerta
- `DELETE /api/alertas/{id}` - Eliminar alerta

### Reportes
- `GET /api/reportes` - Listar reportes
- `POST /api/reportes` - Crear reporte
- `GET /api/reportes/{id}` - Obtener reporte
- `PUT /api/reportes/{id}` - Actualizar reporte
- `DELETE /api/reportes/{id}` - Eliminar reporte

### Predicciones
- `GET /api/predicciones` - Listar predicciones
- `POST /api/predicciones` - Crear predicción
- `GET /api/predicciones/{id}` - Obtener predicción
- `PUT /api/predicciones/{id}` - Actualizar predicción
- `DELETE /api/predicciones/{id}` - Eliminar predicción

---

## Uso de la API desde JavaScript

El archivo `/public/js/api.js` proporciona funciones auxiliares para consumir la API:

```javascript
// Obtener todas las empresas
const empresas = await empresasAPI.getAll();

// Crear una nueva empresa
const nuevaEmpresa = await empresasAPI.create({
    nombre: 'Mi Empresa',
    tipo: 'Hotel',
    usuario_id: 1
});

// Obtener una empresa específica
const empresa = await empresasAPI.getById(1);

// Actualizar una empresa
await empresasAPI.update(1, {
    nombre: 'Nombre Actualizado'
});

// Eliminar una empresa
await empresasAPI.delete(1);
```

---

## Vistas Disponibles

### Dashboard
- **Ruta:** `/dashboard`
- **Descripción:** Panel de control con KPIs, alertas recientes y empresas registradas
- **Funcionalidades:** Carga dinámica de datos desde la API

### Empresas
- **Ruta:** `/empresas`
- **Descripción:** Listado de todas las empresas registradas
- **Funcionalidades:** CRUD completo, búsqueda y filtrado

### Consumos Energéticos
- **Ruta:** `/consumos`
- **Descripción:** Registro de consumos diarios por empresa
- **Funcionalidades:** Visualización de costos estimados

### Radiación Solar
- **Ruta:** `/radiaciones`
- **Descripción:** Datos históricos de radiación solar
- **Funcionalidades:** Filtrado por fecha, visualización de tendencias

### Alertas
- **Ruta:** `/alertas`
- **Descripción:** Sistema de alertas del sistema
- **Funcionalidades:** Clasificación por tipo, eliminación

### Reportes
- **Ruta:** `/reportes`
- **Descripción:** Gestión de reportes en PDF y Excel
- **Funcionalidades:** Descarga y visualización

---

## Diseño Visual

La aplicación sigue el patrón **Minimalismo Técnico Moderno** con:

- **Paleta de colores:** Blanco, gris oscuro, azul confiable (#1E40AF) y verde energético (#10B981)
- **Tipografía:** IBM Plex Sans para cuerpo e IBM Plex Mono para datos técnicos
- **Layout:** Sidebar fijo izquierdo con navegación jerárquica
- **Componentes:** Tarjetas, KPIs, tablas de datos, formularios y alertas

---

## Configuración de Base de Datos

### Tablas Principales

1. **usuarios** - Gestión de usuarios del sistema
2. **empresas** - Registro de empresas clientes
3. **consumoenergetico** - Consumo diario de energía
4. **radiacionsolar** - Datos de radiación solar
5. **recomendaciones** - Recomendaciones del sistema
6. **alertas** - Alertas y notificaciones
7. **reportes** - Almacenamiento de reportes
8. **predicciones** - Predicciones de consumo y riesgos

---

## Troubleshooting

### Error: "SQLSTATE[HY000]: General error: 1698"
**Solución:** Ejecutar el comando para cambiar la autenticación de MySQL:
```bash
sudo mysql -u root -proot -e "ALTER USER 'root'@'localhost' IDENTIFIED WITH mysql_native_password BY 'root'; FLUSH PRIVILEGES;"
```

### Error: "No application encryption key has been specified"
**Solución:** Ejecutar:
```bash
php artisan key:generate
```

### Error: "Class not found"
**Solución:** Ejecutar:
```bash
composer dump-autoload
```

### La API no responde
**Solución:** Verificar que el servidor está corriendo:
```bash
php artisan serve
```

---

## Notas Importantes

- ✅ **Sin integración de IA:** La aplicación no incluye integración con modelos de lenguaje
- ✅ **API completamente funcional:** Todos los endpoints están listos para consumo en aplicaciones móviles
- ✅ **Vistas con Fetch:** Las vistas web consumen la API mediante JavaScript vanilla
- ✅ **CSS Puro:** Sin frameworks de utilidad, solo CSS organizado en carpetas
- ✅ **Escalable:** Estructura lista para agregar nuevas funcionalidades

---

## Soporte y Contacto

Para reportar problemas o sugerencias, contactar al equipo de desarrollo.

---

**Versión:** 1.0.0  
**Última actualización:** Mayo 2026  
**Licencia:** MIT
