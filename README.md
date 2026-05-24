# ☀️ Agente Solar Inteligente

> Dashboard Solar con IA para Ahorro Energético en Riohacha, La Guajira

Plataforma que analiza datos históricos de radiación solar y perfiles de consumo energético de empresas locales, generando recomendaciones automáticas de ahorro mediante un **Agente Solar con IA**.

## 🎯 Stack tecnológico

| Capa                     | Tecnología                                                                                                   |
| ------------------------ | ------------------------------------------------------------------------------------------------------------ |
| Backend / API REST       | **FastAPI**                                                                                                  |
| Frontend / Visualización | **Streamlit**                                                                                                |
| Base de datos            | **MySQL 8**                                                                                                  |
| LLM (cloud)              | **Google Gemini (Flash Lite)** (con fallback a reglas)                                                       |
| Datos solares            | **Open-Meteo** (núcleo), **OpenWeather** (complemento), **PVGIS** (baseline opcional), NASA POWER (respaldo) |
| Reportes                 | ReportLab (PDF), XlsxWriter (Excel)                                                                          |
| Despliegue               | **Docker + Docker Compose**                                                                                  |

La API REST está diseñada para ser consumida también desde apps móviles (no incluidas).

---

## 🚀 Instalación y configuración con Docker

Todo el sistema se levanta con **un solo comando** usando Docker Compose. No necesitas instalar Python, MySQL, ni dependencias en tu máquina.

### Paso 1 — Instalar Docker Desktop

#### Windows
1. Descarga **Docker Desktop para Windows**: https://www.docker.com/products/docker-desktop/
2. Ejecuta el instalador (`Docker Desktop Installer.exe`).
3. Marca la opción **"Use WSL 2 instead of Hyper-V"** durante la instalación.
4. Reinicia el equipo cuando lo solicite.
5. Abre **Docker Desktop** y espera hasta que diga: **`Docker Desktop is running`** (esquina inferior izquierda).

#### Linux (Ubuntu/Debian)
```bash
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
sudo usermod -aG docker $USER
newgrp docker
```

#### Verificar instalación
Abre PowerShell, CMD, Git Bash o terminal y ejecuta:

```bash
docker --version
docker compose version
```

Debes ver versiones de ambos. Ejemplo:
```
Docker version 27.x.x
Docker Compose version v2.x.x
```

### Paso 2 — Clonar / ubicarse en el proyecto

```bash
cd ruta/al/proyecto/pero-se-va-a
```

### Paso 3 — Crear archivo `.env`

```bash
# Windows (PowerShell o CMD)
copy .env.example .env

# Linux / Mac / Git Bash
cp .env.example .env
```

> ✏️ **Edita `.env` solo si quieres usar OpenWeather real** (poniendo tu API key gratuita de https://openweathermap.org/api). **Open-Meteo y PVGIS no requieren API key.** Si lo dejas vacío, el sistema usará Open-Meteo + datos sintéticos como fallback.

### Paso 4 — Levantar todo el stack

Desde la carpeta del proyecto:

```bash
docker compose up --build
```

La primera vez tarda **5-10 minutos** porque:
1. Descarga la imagen de MySQL 8
2. Construye la imagen de la API (FastAPI)
3. Construye la imagen del frontend (Streamlit)
4. Inicializa la base de datos `agente_solar_db`

Cuando veas estos logs, todo está listo:

```
agente_solar_mysql     | [System] [MY-010931] ready for connections
agente_solar_api       | INFO:     Uvicorn running on http://0.0.0.0:8000
agente_solar_streamlit | You can now view your Streamlit app in your browser.
```

> 💡 **Tip**: para correrlo en segundo plano, usa `docker compose up --build -d`.

### Paso 5 — Cargar datos demo (seed)

Abre **otra terminal** (sin cerrar la anterior) y ejecuta:

```bash
docker compose exec api python scripts/seed.py
```

> Si tu volumen de MySQL viene de una versión anterior del proyecto, el arranque y el seed intentan reparar automáticamente columnas faltantes como `users.vista_preferida`. Si sigue fallando, recrea la base con `docker compose down -v` y vuelve a levantar el stack.

Esto crea:
- 3 usuarios demo (admin, empresa, analista)
- Empresa piloto **"Hotel Solar Riohacha"**
- 60 días de datos sintéticos de consumo y radiación solar

Verás al final:
```
============================================================
✅ SEED COMPLETO
============================================================
Credenciales de acceso:
  Admin:    admin@agentesolar.co    / admin123
  Empresa:  hotel@agentesolar.co    / hotel123
  Analista: analista@agentesolar.co / analista123
============================================================
```

### Paso 6 — Acceder a la aplicación

| Servicio                 | URL                         | Descripción                      |
| ------------------------ | --------------------------- | -------------------------------- |
| 🎨 **Frontend Streamlit** | http://localhost:8502       | Dashboard, gráficas, IA          |
| 📡 **API Swagger Docs**   | http://localhost:8001/docs  | Documentación interactiva        |
| 📡 **API ReDoc**          | http://localhost:8001/redoc | Documentación alternativa        |
| 🗄️ **MySQL**              | `localhost:3306`            | DB (user: `root` / pass: `root`) |

### Paso 7 — Activar IA con Gemini

Crea tu clave de API en Google AI Studio y asegúrate de establecerla en tus variables de entorno para habilitar el motor de recomendaciones.

1. Consigue tu API KEY en Google AI Studio.
2. Cópiala en tu archivo `.env`: `GEMINI_API_KEY=tu_key`
3. Reinicia los contenedores:
   ```bash
   docker compose down
   docker compose up -d
   ```

La API detectará Gemini automáticamente.

---

## 🔐 Credenciales demo

| Rol                    | Email                     | Contraseña    |
| ---------------------- | ------------------------- | ------------- |
| Admin                  | `admin@agentesolar.co`    | `admin123`    |
| Empresa (Hotel piloto) | `hotel@agentesolar.co`    | `hotel123`    |
| Analista               | `analista@agentesolar.co` | `analista123` |

---

## 🛠️ Comandos Docker útiles

| Acción                                    | Comando                                                         |
| ----------------------------------------- | --------------------------------------------------------------- |
| Iniciar todo (primera vez o tras cambios) | `docker compose up --build`                                     |
| Iniciar en segundo plano                  | `docker compose up -d`                                          |
| Ver logs en vivo                          | `docker compose logs -f`                                        |
| Ver logs de un servicio                   | `docker compose logs -f api`                                    |
| Detener todo                              | `docker compose down`                                           |
| Detener y borrar datos MySQL              | `docker compose down -v`                                        |
| Reiniciar la API                          | `docker compose restart api`                                    |
| Reconstruir desde cero (sin caché)        | `docker compose build --no-cache`                               |
| Entrar a la consola de la API             | `docker compose exec api bash`                                  |
| Entrar a MySQL                            | `docker compose exec mysql mysql -uroot -proot agente_solar_db` |
| Re-ejecutar seed                          | `docker compose exec api python scripts/seed.py`                |
| Ver contenedores activos                  | `docker compose ps`                                             |

---

## 📂 Estructura del proyecto

```
.
├── app/                          # Backend FastAPI
│   ├── main.py                   # Entrada API
│   ├── core/                     # Config, security (JWT)
│   ├── db/                       # SQLAlchemy session
│   ├── models/                   # Modelos ORM
│   ├── schemas/                  # Schemas Pydantic
│   ├── api/
│   │   ├── deps/                 # Dependencias (auth)
│   │   └── routes/               # Endpoints REST
│   └── services/
│       ├── nasa_power.py         # NASA POWER API (respaldo legacy)
│       ├── openmeteo.py          # Open-Meteo API (NÚCLEO PRINCIPAL)
│       ├── openweather.py        # OpenWeather API (complemento + AQI)
│       ├── pvgis.py              # PVGIS API (baseline TMY opcional)
│       ├── consumo_parser.py     # Parser CSV/Excel
│       ├── reportes.py           # Generación PDF/Excel
│       └── agents/               # 5 Agentes IA
│           ├── agente_solar.py
│           ├── agente_consumo.py
│           ├── agente_recomendaciones.py
│           ├── agente_prediccion.py
│           └── agente_alertas.py
├── streamlit_app/                # Frontend Streamlit
│   ├── Home.py                   # Login + landing
│   ├── api_client.py             # Cliente HTTP a la API
│   └── pages/                    # Dashboard, Consumo, IA, etc.
├── scripts/
│   ├── seed.py                   # Datos demo
│   └── init_db.sql               # Init de la BD
├── docker-compose.yml            # Orquestación Docker
├── Dockerfile.api                # Imagen FastAPI
├── Dockerfile.streamlit          # Imagen Streamlit
├── requirements.txt              # Dependencias Python
├── .env.example                  # Template de variables
└── README.md                     # Este archivo
```

---

## 🗄️ Base de datos — construcción y migración

### Construir la BD desde cero (si no existe)

Las tablas se crean **automáticamente** al iniciar la API gracias a `Base.metadata.create_all()` en `app/main.py`. No requiere paso manual la primera vez.

### Si cambias el modelo o el esquema de la BD

Este proyecto usa Docker y un volumen persistente de MySQL. Eso significa que un cambio en los modelos ORM no se aplica solo por reconstruir la imagen: si la BD ya existía, el volumen puede seguir teniendo la estructura vieja.

Regla práctica:

1. Si el cambio es de desarrollo y puedes perder datos, usa `docker compose down -v` y luego `docker compose up --build`.
2. Después vuelve a ejecutar `docker compose exec api python scripts/seed.py`.
3. Si no puedes borrar datos, agrega una migración explícita o una corrección puntual de esquema. El proyecto ya incluye una compatibilidad mínima para columnas conocidas que quedaron desfasadas, pero no reemplaza un sistema de migraciones completo.

Cuando aparezca un error como `Unknown column ... in field list`, casi siempre significa que el código cambió antes que la BD del volumen. En ese caso, revisa primero el `SHOW CREATE TABLE` de la tabla afectada dentro del contenedor MySQL.

Si quieres forzar la creación o reconstruir desde cero:

```bash
# Opción A — Recrear todo (borra datos existentes)
docker compose down -v
docker compose up --build
docker compose exec api python scripts/seed.py

# Opción B — Crear solo tablas (sin borrar volumen)
docker compose exec api python -c "from app.db.session import engine, Base; from app.models import models; Base.metadata.create_all(bind=engine); print('Tablas creadas')"
```

---

## 🌐 Fuentes de datos meteorológicos / solares

| Fuente          | Rol                 | API key       | Datos clave                                                |
| --------------- | ------------------- | ------------- | ---------------------------------------------------------- |
| **Open-Meteo**  | 🟢 Núcleo            | ❌ No requiere | GHI / DNI / DHI horarios, ERA5 histórico, calidad del aire |
| **OpenWeather** | 🔵 Complemento       | ✅ Gratuita    | Clima actual, pronóstico 5d, AQI, validación cruzada       |
| **PVGIS**       | 🟡 Baseline opcional | ❌ No requiere | TMY 15+ años, radiación mensual, simulación PV             |
| **NASA POWER**  | ⚪ Respaldo legacy   | ❌ No requiere | Radiación diaria histórica                                 |

> **Por qué esta arquitectura:** Open-Meteo entrega GHI/DNI/DHI nativos sin pago, hasta 16 días de pronóstico y archivo ERA5 — ideal como núcleo. OpenWeather complementa con AQI y permite contrastar pronósticos. PVGIS provee la línea base climatológica para Riohacha.

---

| Método | Endpoint                              | Descripción                                     |
| ------ | ------------------------------------- | ----------------------------------------------- |
| `POST` | `/api/v1/auth/login`                  | Login (form-urlencoded), retorna JWT            |
| `POST` | `/api/v1/auth/register`               | Registro de usuarios                            |
| `GET`  | `/api/v1/auth/me`                     | Info del usuario actual                         |
| `GET`  | `/api/v1/empresas/`                   | Lista empresas                                  |
| `POST` | `/api/v1/empresas/`                   | Crear empresa (admin)                           |
| `GET`  | `/api/v1/consumo/empresa/{id}`        | Consumo histórico                               |
| `POST` | `/api/v1/consumo/upload/{id}`         | Upload CSV/Excel                                |
| `GET`  | `/api/v1/consumo/kpis/{id}`           | KPIs del dashboard                              |
| `POST` | `/api/v1/solar/sync/openmeteo`        | Sincronizar histórico Open-Meteo (núcleo)       |
| `POST` | `/api/v1/solar/sync/nasa`             | Sincronizar NASA POWER (respaldo)               |
| `GET`  | `/api/v1/solar/radiacion`             | Radiación histórica (filtro `fuente=`)          |
| `GET`  | `/api/v1/solar/forecast/horario`      | Pronóstico horario con GHI/DNI/DHI (Open-Meteo) |
| `GET`  | `/api/v1/solar/forecast/diario`       | Pronóstico diario (Open-Meteo)                  |
| `GET`  | `/api/v1/solar/air-quality`           | Calidad del aire / polvo (Open-Meteo)           |
| `GET`  | `/api/v1/solar/weather/current`       | Clima actual (OpenWeather)                      |
| `GET`  | `/api/v1/solar/weather/forecast`      | Pronóstico OpenWeather                          |
| `GET`  | `/api/v1/solar/weather/air-pollution` | AQI (OpenWeather)                               |
| `GET`  | `/api/v1/solar/weather/cross-check`   | Validación cruzada Open-Meteo vs OpenWeather    |
| `GET`  | `/api/v1/solar/pvgis/tmy`             | Año Meteorológico Típico de Riohacha            |
| `GET`  | `/api/v1/solar/pvgis/monthly`         | Promedios mensuales históricos                  |
| `GET`  | `/api/v1/solar/pvgis/pvcalc`          | Estimación de generación PV                     |
| `POST` | `/api/v1/ia/recomendaciones/{id}`     | Generar recomendaciones IA                      |
| `POST` | `/api/v1/predicciones/generar/{id}`   | Predicciones 24-72h                             |
| `POST` | `/api/v1/alertas/evaluar/{id}`        | Evaluar alertas                                 |
| `GET`  | `/api/v1/reportes/pdf/{id}`           | Descargar reporte PDF                           |
| `GET`  | `/api/v1/reportes/excel/{id}`         | Descargar reporte Excel                         |

📖 **Documentación interactiva completa**: http://localhost:8000/docs

---

## 🤖 Arquitectura IA (5 Agentes)

| Agente              | Responsabilidad                                       |
| ------------------- | ----------------------------------------------------- |
| **Análisis Solar**  | Calcula potencial de generación según radiación       |
| **Consumo**         | Detecta patrones, anomalías, picos                    |
| **Recomendaciones** | Genera sugerencias en lenguaje natural (LLM o reglas) |
| **Predicción**      | Pronostica producción/consumo/costo a 24-72h          |
| **Alertas**         | Monitorea umbrales y dispara notificaciones           |

### Modos de operación

- **Con Gemini activo** → usa **Gemini 2.5 Flash Lite** para generar recomendaciones en lenguaje natural.
- **Sin Gemini** → fallback automático a **reglas heurísticas** basadas en el contexto local de Riohacha.

---

## 📊 Funcionalidades MVP cubiertas

- [x] Login con 3 roles (admin / empresa / analista) y JWT
- [x] Dashboard con KPIs: radiación, consumo, costo, batería, ahorro
- [x] Carga de archivos CSV/Excel con validación
- [x] Integración **Open-Meteo** (núcleo: GHI/DNI/DHI horario, archive ERA5, calidad del aire)
- [x] Integración **OpenWeather** (complemento: validación cruzada + AQI)
- [x] Integración **PVGIS** (opcional: baseline TMY climatológico de 15+ años)
- [x] Integración NASA POWER (respaldo histórico)
- [x] Motor IA con 5 agentes
- [x] Reportes PDF + Excel exportables
- [x] Sistema de alertas configurable
- [x] Empresa piloto pre-cargada (Hotel Solar Riohacha)
- [x] Datos sintéticos de 60 días para demo

---

## 📁 Formato del archivo de consumo (carga CSV/Excel)

**Columnas requeridas:** `fecha`, `consumo_kwh`
**Columnas opcionales:** `costo_cop`, `demanda_pico_kw`, `produccion_solar_kwh`, `nivel_bateria_pct`, `periodo`

Ejemplo:

```csv
fecha,consumo_kwh,costo_cop,demanda_pico_kw,produccion_solar_kwh,nivel_bateria_pct,periodo
2026-01-01,120.5,113550,15.2,45.0,85.0,diario
2026-01-02,135.2,127430,18.4,50.2,78.0,diario
```

> 💡 Una plantilla descargable está disponible en la página **Consumo** del frontend.

---

## 🔧 Variables de entorno (`.env`)

| Variable                    | Descripción                           | Default                                                 |
| --------------------------- | ------------------------------------- | ------------------------------------------------------- |
| `MYSQL_HOST`                | Host MySQL (en Docker = `mysql`)      | `mysql`                                                 |
| `MYSQL_USER`                | Usuario MySQL                         | `root`                                                  |
| `MYSQL_PASSWORD`            | Password MySQL                        | `root`                                                  |
| `MYSQL_DATABASE`            | Nombre BD                             | `agente_solar_db`                                       |
| `SECRET_KEY`                | JWT secret (cambiar en producción)    | `cambiar-en-produccion-2026`                            |
| `OPENMETEO_FORECAST_URL`    | Endpoint forecast Open-Meteo (núcleo) | `https://api.open-meteo.com/v1/forecast`                |
| `OPENMETEO_ARCHIVE_URL`     | Endpoint histórico ERA5               | `https://archive-api.open-meteo.com/v1/archive`         |
| `OPENMETEO_AIR_QUALITY_URL` | Endpoint calidad del aire             | `https://air-quality-api.open-meteo.com/v1/air-quality` |
| `OPENWEATHER_API_KEY`       | API key OpenWeather (opcional)        | (vacío → fallback sintético)                            |
| `PVGIS_BASE_URL`            | Endpoint PVGIS v5_3 (opcional)        | `https://re.jrc.ec.europa.eu/api/v5_3`                  |
| `PVGIS_ENABLED`             | Habilitar PVGIS                       | `true`                                                  |
| `NASA_POWER_BASE_URL`       | NASA POWER (respaldo)                 | `https://power.larc.nasa.gov/api/temporal/daily/point`  |

---

## 🆘 Solución de problemas

### "Docker Desktop is not running"
Abre Docker Desktop y espera a que el icono esté verde / en estado "running".

### Puerto 3306, 8000 u 8501 ya en uso
Detén el servicio que ocupe el puerto, o cambia los puertos en `docker-compose.yml`:
```yaml
ports:
  - "3307:3306"   # cambia 3306 → 3307 (o el que prefieras)
```

### "Cannot connect to the Docker daemon"
- En **Windows**: abre Docker Desktop.
- En **Linux**: `sudo systemctl start docker`.

### El seed falla con error de conexión
Espera 30 segundos a que MySQL termine de inicializarse. Vuelve a ejecutar:
```bash
docker compose exec api python scripts/seed.py
```

### Quiero empezar de cero (borrar BD y datos)
```bash
docker compose down -v
docker compose up --build
docker compose exec api python scripts/seed.py
```

### Cambié código y no se refleja
La API tiene `--reload` activo, pero si modificaste `requirements.txt` o `Dockerfile`:
```bash
docker compose up --build
```

---

## 🌟 Licencia

MIT — Proyecto académico para Hackatón Riohacha 2026.

📍 **Riohacha, La Guajira — Colombia**
🌞 *Capital colombiana de energía solar (hasta 7.0 kWh/m²/día)*
