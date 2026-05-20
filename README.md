# ☀️ Agente Solar Inteligente

> Dashboard Solar con IA para Ahorro Energético en Riohacha, La Guajira

Plataforma que analiza datos históricos de radiación solar y perfiles de consumo energético de empresas locales, generando recomendaciones automáticas de ahorro mediante un **Agente Solar con IA**.

## 🎯 Stack tecnológico

| Capa | Tecnología |
|------|-----------|
| Backend / API REST | **FastAPI** |
| Frontend / Visualización | **Streamlit** |
| Base de datos | **MySQL 8** |
| LLM (local) | **Ollama + Llama 3.2** (con fallback a reglas) |
| Datos solares | NASA POWER, OpenWeather |
| Reportes | ReportLab (PDF), XlsxWriter (Excel) |
| Despliegue | **Docker + Docker Compose** |

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

> ✏️ **Edita `.env` solo si quieres usar OpenWeather real** (poniendo tu API key gratuita de https://openweathermap.org/api). Si lo dejas vacío, el sistema usará datos sintéticos.

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

| Servicio | URL | Descripción |
|----------|-----|-------------|
| 🎨 **Frontend Streamlit** | http://localhost:8501 | Dashboard, gráficas, IA |
| 📡 **API Swagger Docs** | http://localhost:8000/docs | Documentación interactiva |
| 📡 **API ReDoc** | http://localhost:8000/redoc | Documentación alternativa |
| 🗄️ **MySQL** | `localhost:3306` | DB (user: `root` / pass: `root`) |

### Paso 7 (Opcional) — Activar IA con Ollama

Por defecto las recomendaciones usan reglas heurísticas. Para activar **Llama 3.2** local:

1. Instala Ollama en tu máquina (no en Docker): https://ollama.com/download
2. Descarga el modelo:
   ```bash
   ollama pull llama3.2:3b
   ```
3. Asegúrate de que Ollama esté corriendo (`ollama serve` o ya viene como servicio).
4. Reinicia la API:
   ```bash
   docker compose restart api
   ```

La API detectará Ollama automáticamente vía `host.docker.internal:11434`.

---

## 🔐 Credenciales demo

| Rol | Email | Contraseña |
|-----|-------|-----------|
| Admin | `admin@agentesolar.co` | `admin123` |
| Empresa (Hotel piloto) | `hotel@agentesolar.co` | `hotel123` |
| Analista | `analista@agentesolar.co` | `analista123` |

---

## 🛠️ Comandos Docker útiles

| Acción | Comando |
|--------|---------|
| Iniciar todo (primera vez o tras cambios) | `docker compose up --build` |
| Iniciar en segundo plano | `docker compose up -d` |
| Ver logs en vivo | `docker compose logs -f` |
| Ver logs de un servicio | `docker compose logs -f api` |
| Detener todo | `docker compose down` |
| Detener y borrar datos MySQL | `docker compose down -v` |
| Reiniciar la API | `docker compose restart api` |
| Reconstruir desde cero (sin caché) | `docker compose build --no-cache` |
| Entrar a la consola de la API | `docker compose exec api bash` |
| Entrar a MySQL | `docker compose exec mysql mysql -uroot -proot agente_solar_db` |
| Re-ejecutar seed | `docker compose exec api python scripts/seed.py` |
| Ver contenedores activos | `docker compose ps` |

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
│       ├── nasa_power.py         # NASA POWER API
│       ├── openweather.py        # OpenWeather API
│       ├── consumo_parser.py     # Parser CSV/Excel
│       ├── ollama_client.py      # Cliente LLM local
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

## 📡 Endpoints principales (API)

| Método | Endpoint | Descripción |
|--------|----------|-------------|
| `POST` | `/api/v1/auth/login` | Login (form-urlencoded), retorna JWT |
| `POST` | `/api/v1/auth/register` | Registro de usuarios |
| `GET` | `/api/v1/auth/me` | Info del usuario actual |
| `GET` | `/api/v1/empresas/` | Lista empresas |
| `POST` | `/api/v1/empresas/` | Crear empresa (admin) |
| `GET` | `/api/v1/consumo/empresa/{id}` | Consumo histórico |
| `POST` | `/api/v1/consumo/upload/{id}` | Upload CSV/Excel |
| `GET` | `/api/v1/consumo/kpis/{id}` | KPIs del dashboard |
| `POST` | `/api/v1/solar/sync/nasa` | Sincronizar NASA POWER |
| `GET` | `/api/v1/solar/radiacion` | Radiación histórica |
| `GET` | `/api/v1/solar/weather/forecast` | Pronóstico OpenWeather |
| `POST` | `/api/v1/ia/recomendaciones/{id}` | Generar recomendaciones IA |
| `POST` | `/api/v1/predicciones/generar/{id}` | Predicciones 24-72h |
| `POST` | `/api/v1/alertas/evaluar/{id}` | Evaluar alertas |
| `GET` | `/api/v1/reportes/pdf/{id}` | Descargar reporte PDF |
| `GET` | `/api/v1/reportes/excel/{id}` | Descargar reporte Excel |

📖 **Documentación interactiva completa**: http://localhost:8000/docs

---

## 🤖 Arquitectura IA (5 Agentes)

| Agente | Responsabilidad |
|--------|-----------------|
| **Análisis Solar** | Calcula potencial de generación según radiación |
| **Consumo** | Detecta patrones, anomalías, picos |
| **Recomendaciones** | Genera sugerencias en lenguaje natural (LLM o reglas) |
| **Predicción** | Pronostica producción/consumo/costo a 24-72h |
| **Alertas** | Monitorea umbrales y dispara notificaciones |

### Modos de operación

- **Con Ollama activo** → usa **Llama 3.2 3B** para generar recomendaciones en lenguaje natural.
- **Sin Ollama** → fallback automático a **reglas heurísticas** basadas en el contexto local de Riohacha.

---

## 📊 Funcionalidades MVP cubiertas

- [x] Login con 3 roles (admin / empresa / analista) y JWT
- [x] Dashboard con KPIs: radiación, consumo, costo, batería, ahorro
- [x] Carga de archivos CSV/Excel con validación
- [x] Integración NASA POWER (radiación histórica)
- [x] Integración OpenWeather (clima/pronóstico)
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

| Variable | Descripción | Default |
|----------|-------------|---------|
| `MYSQL_HOST` | Host MySQL (en Docker = `mysql`) | `mysql` |
| `MYSQL_USER` | Usuario MySQL | `root` |
| `MYSQL_PASSWORD` | Password MySQL | `root` |
| `MYSQL_DATABASE` | Nombre BD | `agente_solar_db` |
| `SECRET_KEY` | JWT secret (cambiar en producción) | `cambiar-en-produccion-2026` |
| `OPENWEATHER_API_KEY` | API key OpenWeather (opcional) | (vacío → fallback sintético) |
| `OLLAMA_BASE_URL` | URL Ollama | `http://host.docker.internal:11434` |
| `OLLAMA_MODEL` | Modelo Llama | `llama3.2:3b` |

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
