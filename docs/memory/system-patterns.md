# 📐 Patrones del Sistema y Lógica de Dominio

Patrones recurrentes y modelos de cálculo del Agente Solar.

## 1. Orquestación Autónoma de Almacenamiento (Baterías)
- **Carga Solar (10:00 - 14:00)**: Prioriza cargar baterías con excedentes solares.
- **Descarga Estratégica (18:00 - 22:00)**: Cubre el pico de consumo nocturno.
- **Modo Contingencia**: Reserva mínima del 30-40% ante alertas de apagón.

## 2. Capa de Datos Híbrida (Real + Sintética)
- Consulta en tiempo real a APIs climáticas (ej. Open-Meteo).
- Si la conexión falla o es demo, conmuta a `scripts/demo_data/*.json`.
- Indicador transparente de `origen_dato` (`api_real` vs `demo_sintetico`).

## 3. Modelo Financiero y Tarifario
- Tarifa base: $943 COP/kWh (Air-E La Guajira).
- Cálculo de ROI: Inversión inicial / (Ahorro solar mensual - Costo mantenimiento).
- Proyección a 5 y 10 años diferenciada por perfil Residencial vs PYME.

## 4. Adaptabilidad de Interfaz
- Detección de perfil en login (`comunidad` vs `pyme`).
- Renderizado de métricas adaptadas: lenguaje coloquial vs KPIs de ingeniería.
