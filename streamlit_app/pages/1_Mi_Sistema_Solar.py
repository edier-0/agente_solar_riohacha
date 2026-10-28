"""Mi sistema solar: paneles, banco de baterías, inversor y perfil de consumo de la cuenta.

Aquí se agregan o quitan baterías (una fila por batería, o varias iguales con 'Cantidad').
Al guardar se actualizan la potencia pico y la energía de las baterías que usan el Panel y las alertas.
"""

import os
import sys

import streamlit as st

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from api_client import api_get, api_put, get_current_user, is_authenticated
from design import render_hero, render_section_header
from registro import INSTALACION_DEFECTO, ORIENTACIONES, QUIMICAS, TIPOS_PANEL
from ui import render_user_sidebar


st.set_page_config(page_title="Mi sistema solar", layout="wide", initial_sidebar_state="auto")
render_user_sidebar()

if not is_authenticated():
    st.warning("Debe iniciar sesion primero.")
    st.stop()

user = get_current_user() or {}
empresas = api_get("/empresas/") or []
if not empresas:
    st.warning("No hay empresas registradas.")
    st.stop()

if user.get("role") == "empresa" and user.get("empresa_id"):
    empresa_id = user["empresa_id"]
    empresa_sel = next((e for e in empresas if e["id"] == empresa_id), empresas[0])
else:
    opciones = {f"{e['nombre']} (ID:{e['id']})": e for e in empresas}
    empresa_sel = opciones[st.selectbox("Selecciona una empresa", list(opciones.keys()))]
    empresa_id = empresa_sel["id"]

puede_editar = user.get("role") in ("empresa", "admin")
inst = api_get(f"/empresas/{empresa_id}/instalacion")
base = inst or {}

QUIMICAS_NOMBRES = [corto for _, corto in QUIMICAS.values()]
TIPOS_NOMBRES = [corto for _, corto in TIPOS_PANEL.values()]
DEFECTO_BATERIA = {"quimica": "Litio LiFePO4", "voltaje_v": 48.0, "capacidad_ah": 100.0, "cantidad": 1}

ss = st.session_state
if ss.get("mss_empresa") != empresa_id or ss.get("mss_version") != base.get("updated_at"):
    # Al cambiar de empresa o después de guardar se vuelve a leer la lista de baterías
    ss["mss_empresa"] = empresa_id
    ss["mss_version"] = base.get("updated_at")
    ss["mss_seq"] = 0
    ss["mss_baterias"] = []
    for b in base.get("baterias") or []:
        ss["mss_seq"] += 1
        ss["mss_baterias"].append({"uid": ss["mss_seq"], **{k: b.get(k) for k in DEFECTO_BATERIA}})
    for k in [k for k in ss.keys() if str(k).startswith("mss_bat_")]:
        del ss[k]


def _agregar_bateria() -> None:
    # La nueva copia los datos de la última: lo normal es que el banco tenga baterías iguales
    ultima = ss["mss_baterias"][-1] if ss["mss_baterias"] else DEFECTO_BATERIA
    if ss["mss_baterias"]:
        uid = ultima["uid"]
        ultima = {k: ss.get(f"mss_bat_{uid}_{k}", ultima.get(k)) for k in DEFECTO_BATERIA}
    ss["mss_seq"] += 1
    ss["mss_baterias"].append({"uid": ss["mss_seq"], **{k: ultima.get(k) for k in DEFECTO_BATERIA}, "cantidad": 1})


def _quitar_bateria(uid: int) -> None:
    ss["mss_baterias"] = [b for b in ss["mss_baterias"] if b["uid"] != uid]


def _valor(uid: int, campo: str, defecto):
    return ss.get(f"mss_bat_{uid}_{campo}", defecto)


kwp = base.get("potencia_pico_kw") or 0
render_hero(
    "Mi sistema solar",
    (
        f"{kwp:g} kWp · {base.get('numero_baterias', 0)} batería(s) · {base.get('bateria_kwh', 0):g} kWh almacenables"
        if inst else "Registra tus paneles y baterías para ver tu producción real en el Panel."
    ),
    icon="sun",
    eyebrow=empresa_sel["nombre"],
    tone="warning",
)

aviso = st.session_state.pop("mss_aviso", None)
if aviso:
    st.success(aviso)

if inst:
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Potencia pico", f"{kwp:g} kWp", help="Potencia de cada panel × cantidad de paneles.")
    c2.metric("Paneles", f"{base.get('cantidad_paneles')} × {base.get('potencia_panel_w', 0):,.0f} W")
    c3.metric("Baterías", f"{base.get('numero_baterias', 0)}", help="Suma de las cantidades de la lista.")
    c4.metric("Energía de las baterías", f"{base.get('bateria_kwh', 0):g} kWh", help="Voltaje × Ah × cantidad de cada batería.")
else:
    st.info("Esta cuenta aún no tiene paneles registrados. Completa los datos y guarda.")

if not puede_editar:
    st.caption("Con el rol analista solo puedes consultar estos datos.")

# ---- Paneles ----
with st.container(border=True):
    render_section_header("Paneles fotovoltaicos", "sun", "La potencia está en la etiqueta del panel (Pmax).")
    c1, c2, c3, c4 = st.columns(4)
    potencia_panel = c1.number_input(
        "Potencia por panel (W)", min_value=10.0, max_value=2000.0, step=10.0, format="%.0f",
        value=float(base.get("potencia_panel_w") or INSTALACION_DEFECTO["potencia_panel_w"]), key="mss_pot_panel",
    )
    cantidad_paneles = c2.number_input(
        "Cantidad de paneles", min_value=1, max_value=10000, step=1,
        value=int(base.get("cantidad_paneles") or INSTALACION_DEFECTO["cantidad_paneles"]), key="mss_cant_paneles",
    )
    claves_or = list(ORIENTACIONES)
    orientacion = c3.selectbox(
        "Orientación", claves_or,
        index=claves_or.index(base.get("orientacion")) if base.get("orientacion") in claves_or else 0,
        format_func=lambda k: ORIENTACIONES[k][1], key="mss_orientacion",
    )
    inclinacion = c4.number_input(
        "Inclinación (°)", min_value=0.0, max_value=90.0, step=1.0, format="%.0f",
        value=float(base.get("inclinacion_grados") if base.get("inclinacion_grados") is not None else INSTALACION_DEFECTO["inclinacion_grados"]),
        key="mss_inclinacion", help="En La Guajira lo óptimo es entre 10° y 15°.",
    )
    tipo_actual = base.get("tipo_panel") if base.get("tipo_panel") in TIPOS_NOMBRES else TIPOS_NOMBRES[0]
    tipo_panel = st.selectbox("Tipo de panel", TIPOS_NOMBRES, index=TIPOS_NOMBRES.index(tipo_actual), key="mss_tipo_panel")
    st.caption(f"Potencia pico: **{potencia_panel * cantidad_paneles / 1000:,.2f} kWp**")

# ---- Baterías ----
with st.container(border=True):
    render_section_header(
        "Banco de baterías", "battery",
        "Agrega una fila por batería, o una sola fila con la cantidad si todas son iguales.",
    )
    tiene_bateria = st.toggle(
        "Tengo baterías", value=bool(base.get("tiene_bateria")) if inst else True, key="mss_tiene_bateria"
    )
    total_kwh = 0.0
    total_unidades = 0
    if tiene_bateria:
        if not ss["mss_baterias"]:
            _agregar_bateria()
        for n, bat in enumerate(ss["mss_baterias"], start=1):
            uid = bat["uid"]
            cols = st.columns([2.2, 1.2, 1.2, 1, 1.3, 0.9], vertical_alignment="bottom")
            quimica_actual = _valor(uid, "quimica", bat.get("quimica"))
            if quimica_actual not in QUIMICAS_NOMBRES:
                quimica_actual = QUIMICAS_NOMBRES[0]
            cols[0].selectbox(
                f"Batería {n}: química", QUIMICAS_NOMBRES, index=QUIMICAS_NOMBRES.index(quimica_actual),
                key=f"mss_bat_{uid}_quimica",
            )
            voltaje = cols[1].number_input(
                "Voltaje (V)", min_value=1.0, max_value=1500.0, step=12.0, format="%.0f",
                value=float(bat.get("voltaje_v") or 48.0), key=f"mss_bat_{uid}_voltaje_v",
            )
            capacidad = cols[2].number_input(
                "Capacidad (Ah)", min_value=1.0, max_value=100000.0, step=10.0, format="%.0f",
                value=float(bat.get("capacidad_ah") or 100.0), key=f"mss_bat_{uid}_capacidad_ah",
            )
            cantidad = cols[3].number_input(
                "Cantidad", min_value=1, max_value=500, step=1, value=int(bat.get("cantidad") or 1),
                key=f"mss_bat_{uid}_cantidad",
            )
            energia = voltaje * capacidad * cantidad / 1000
            total_kwh += energia
            total_unidades += cantidad
            cols[4].markdown(f"**{energia:,.2f} kWh**")
            cols[5].button(
                "Quitar", key=f"mss_quitar_{uid}", on_click=_quitar_bateria, args=(uid,),
                disabled=len(ss["mss_baterias"]) == 1 or not puede_editar, use_container_width=True,
            )
        st.button("＋ Agregar batería", on_click=_agregar_bateria, disabled=not puede_editar, key="mss_agregar")
        st.markdown(f"Total: **{total_unidades} batería(s) · {total_kwh:,.2f} kWh**")

        c1, c2, c3, c4 = st.columns(4)
        soc = c1.number_input(
            "Carga actual (SOC %)", min_value=0.0, max_value=100.0, step=5.0, format="%.0f",
            value=float(base.get("soc_pct") if base.get("soc_pct") is not None else INSTALACION_DEFECTO["soc_pct"]),
            key="mss_soc",
        )
        dod = c2.number_input(
            "Descarga máxima (DoD %)", min_value=10.0, max_value=100.0, step=5.0, format="%.0f",
            value=float(base.get("dod_pct") or INSTALACION_DEFECTO["dod_pct"]), key="mss_dod",
            help="La app nunca baja de una reserva del 30 % para los cortes de luz.",
        )
        eficiencia = c3.number_input(
            "Eficiencia de ciclo (%)", min_value=50.0, max_value=100.0, step=0.5, format="%.1f",
            value=float(base.get("eficiencia_ciclo_pct") or INSTALACION_DEFECTO["eficiencia_ciclo_pct"]),
            key="mss_eficiencia",
        )
        descarga = c4.number_input(
            "Potencia máx. de descarga (W)", min_value=100.0, max_value=1000000.0, step=100.0, format="%.0f",
            value=float(base.get("potencia_descarga_w") or INSTALACION_DEFECTO["potencia_descarga_w"]),
            key="mss_descarga",
        )
        util = total_kwh * min(dod / 100, 0.70)
        st.caption(f"Energía útil por noche: **{util:,.2f} kWh** (se deja una reserva para cortes de luz).")

# ---- Inversor ----
with st.container(border=True):
    render_section_header("Inversor y rendimiento", "bolt")
    c1, c2, c3, c4 = st.columns(4)
    inversor = c1.number_input(
        "Potencia del inversor (W)", min_value=100.0, max_value=1000000.0, step=100.0, format="%.0f",
        value=float(base.get("potencia_inversor_w") or INSTALACION_DEFECTO["potencia_inversor_w"]), key="mss_inversor",
    )
    eficiencia_inv = c2.number_input(
        "Eficiencia del inversor (%)", min_value=80.0, max_value=100.0, step=0.1, format="%.1f",
        value=float(base.get("eficiencia_inversor_pct") or INSTALACION_DEFECTO["eficiencia_inversor_pct"]), key="mss_ef_inv",
    )
    pr = c3.number_input(
        "Rendimiento global (PR %)", min_value=50.0, max_value=100.0, step=1.0, format="%.0f",
        value=float(base.get("rendimiento_pr_pct") or INSTALACION_DEFECTO["rendimiento_pr_pct"]), key="mss_pr",
        help="Lo que queda después de pérdidas por temperatura, polvo y cableado. Si no lo sabes, deja 80 %.",
    )
    pv_max = c4.number_input(
        "Máx. CC admisible (W)", min_value=100.0, max_value=1000000.0, step=100.0, format="%.0f",
        value=float(base.get("potencia_pv_max_w") or INSTALACION_DEFECTO["potencia_pv_max_w"]), key="mss_pv_max",
    )

# ---- Consumo ----
with st.container(border=True):
    render_section_header(
        "Perfil de consumo", "home",
        "Con tu factura, el Panel usa este consumo o el de tus aparatos: el que más se parezca a lo que facturó Air-e.",
    )
    c1, c2, c3, c4 = st.columns(4)
    diario = c1.number_input(
        "Consumo diario (kWh)", min_value=0.0, max_value=100000.0, step=0.5, format="%.1f",
        value=float(base.get("consumo_diario_kwh") if base.get("consumo_diario_kwh") is not None else INSTALACION_DEFECTO["consumo_diario_kwh"]),
        key="mss_diario",
    )
    diurna = c2.number_input(
        "De día, 06:00–18:00 (kWh)", min_value=0.0, max_value=100000.0, step=0.5, format="%.1f",
        value=float(base.get("demanda_diurna_kwh") if base.get("demanda_diurna_kwh") is not None else INSTALACION_DEFECTO["demanda_diurna_kwh"]),
        key="mss_diurna",
    )
    nocturna = c3.number_input(
        "De noche, 18:00–06:00 (kWh)", min_value=0.0, max_value=100000.0, step=0.5, format="%.1f",
        value=float(base.get("demanda_nocturna_kwh") if base.get("demanda_nocturna_kwh") is not None else INSTALACION_DEFECTO["demanda_nocturna_kwh"]),
        key="mss_nocturna",
    )
    carga_base = c4.number_input(
        "Carga base continua (W)", min_value=0.0, max_value=1000000.0, step=10.0, format="%.0f",
        value=float(base.get("carga_base_w") if base.get("carga_base_w") is not None else INSTALACION_DEFECTO["carga_base_w"]),
        key="mss_carga_base",
    )
    if diario > 0 and abs(diurna + nocturna - diario) > diario * 0.1:
        st.caption(
            f"El día y la noche suman {diurna + nocturna:,.1f} kWh y el consumo diario es {diario:,.1f} kWh: "
            "la app usa la proporción día/noche para repartir el consumo diario."
        )

if puede_editar and st.button(":material/save: Guardar mi sistema solar", type="primary", key="mss_guardar"):
    baterias = []
    if tiene_bateria:
        for bat in ss["mss_baterias"]:
            uid = bat["uid"]
            baterias.append({
                "quimica": ss.get(f"mss_bat_{uid}_quimica"),
                "voltaje_v": ss.get(f"mss_bat_{uid}_voltaje_v"),
                "capacidad_ah": ss.get(f"mss_bat_{uid}_capacidad_ah"),
                "cantidad": int(ss.get(f"mss_bat_{uid}_cantidad") or 1),
            })
    primera = baterias[0] if baterias else {}
    datos = {
        "potencia_panel_w": potencia_panel,
        "cantidad_paneles": int(cantidad_paneles),
        "orientacion": orientacion,
        "azimut_grados": ORIENTACIONES[orientacion][2] if ORIENTACIONES[orientacion][2] is not None else base.get("azimut_grados"),
        "inclinacion_grados": inclinacion,
        "tipo_panel": tipo_panel,
        "tiene_bateria": bool(baterias),
        "quimica_bateria": primera.get("quimica"),
        "voltaje_banco_v": primera.get("voltaje_v"),
        "capacidad_ah": primera.get("capacidad_ah"),
        "soc_pct": soc if baterias else None,
        "dod_pct": dod if baterias else None,
        "eficiencia_ciclo_pct": eficiencia if baterias else None,
        "potencia_descarga_w": descarga if baterias else None,
        "potencia_inversor_w": inversor,
        "eficiencia_inversor_pct": eficiencia_inv,
        "rendimiento_pr_pct": pr,
        "potencia_pv_max_w": pv_max,
        "consumo_diario_kwh": diario,
        "demanda_diurna_kwh": diurna,
        "demanda_nocturna_kwh": nocturna,
        "carga_base_w": carga_base,
        "baterias": baterias,
    }
    guardada = api_put(f"/empresas/{empresa_id}/instalacion", json=datos)
    if guardada:
        st.session_state["mss_aviso"] = (
            f"Guardado: {guardada['potencia_pico_kw']:g} kWp y {guardada['numero_baterias']} batería(s) "
            f"con {guardada['bateria_kwh']:g} kWh. El Panel y las alertas ya usan estos datos."
        )
        st.rerun()
