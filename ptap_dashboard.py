import streamlit as st
import pandas as pd
import gspread
import plotly.graph_objects as go
from google.oauth2.service_account import Credentials
from datetime import datetime, time
import pytz

# === USUARIOS ===
USUARIOS = {
    "admin": "1234",
    "jperez": "jperez2025",
    "lsangama": "lsangama2025",
    "jsoto": "jsoto2025",
}

USUARIOS_NOMBRES = {
    "jperez": "Jorge Perez Padilla",
    "lsangama": "Luis Sangama Ricopa",
    "jsoto": "Jose Soto Dávila",
}

scope = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive"
]

@st.cache_resource(show_spinner=False)
def get_worksheet():
    creds = Credentials.from_service_account_info(
        st.secrets["gcp_service_account"], scopes=scope
    )
    gc = gspread.authorize(creds)
    SHEET_URL = "https://docs.google.com/spreadsheets/d/19AZGamcT9AIkV6aR4Xs7CCObgBo8xKFlv4eXfrAUJuU/edit?usp=sharing"
    sh = gc.open_by_url(SHEET_URL)
    return sh.sheet1

worksheet = None
try:
    worksheet = get_worksheet()
except Exception as e:
    st.error(f"Error conectando a Google Sheets: {e}")

def leer_datos():
    if worksheet is None:
        return pd.DataFrame()
    data = worksheet.get_all_records()
    df = pd.DataFrame(data)
    if not df.empty and "Fecha" in df.columns and "Hora de toma" in df.columns:
        # Crea columna de datetime combinando fecha y hora de toma
        df["Fecha_Hora"] = pd.to_datetime(
            df["Fecha"].astype(str) + " " + df["Hora de toma"].astype(str),
            errors="coerce"
        )
    return df

def guardar_muestra(muestra):
    if worksheet is not None:
        worksheet.append_row(muestra)

tecnicos = ["Luis Sangama Ricopa", "Jorge Perez Padilla", "Jose Soto Dávila"]
locaciones = [
    "Planta de Agua Potable", "Cocina", "Equipo Purificador - PTAP", "Dispensador - Comedor 2",
    "Dispensador - Oficina Gerencia", "Dispensador - HSE 01", "Dispensador - HSE 02", "Dispensador - Producción"
]

SOLO_CLORO_LOCACIONES = [
    "Equipo Purificador - PTAP", "Dispensador - Comedor 2", "Dispensador - Oficina Gerencia",
    "Dispensador - HSE 01", "Dispensador - HSE 02", "Dispensador - Producción"
]
SOLO_CLORO_LOCACIONES_NORM = [x.strip().lower() for x in SOLO_CLORO_LOCACIONES]

# === Estado inicial de sesión y navegación ===
if "logueado" not in st.session_state:
    st.session_state['logueado'] = False
if "show_login" not in st.session_state:
    st.session_state['show_login'] = False
if "menu" not in st.session_state:
    st.session_state['menu'] = "📊 KPIs y Análisis"
if "usuario" not in st.session_state:
    st.session_state['usuario'] = ""

# Sidebar de navegación
st.set_page_config(page_title="Control Logístico PTAP", page_icon="🚛", layout="wide")
st.image(
    "https://hcmpinturas.com/wp-content/uploads/2023/10/PetroTal-logo-star.png",
    width=230
)
st.sidebar.header("📂 Menú")
menu_options = ["📊 KPIs y Análisis"]
if st.session_state['logueado']:
    menu_options = ["➕ Ingreso de muestra", "📊 KPIs y Análisis", "📄 Historial", "📥 Exportar"]

if st.session_state['show_login']:
    st.session_state['menu'] = "login"
else:
    selected = st.sidebar.radio("Ir a:", menu_options, index=menu_options.index(st.session_state['menu']))
    st.session_state['menu'] = selected

if not st.session_state['logueado']:
    if not st.session_state['show_login']:
        if st.sidebar.button("Iniciar sesión"):
            st.session_state['show_login'] = True
    else:
        pass
else:
    if st.sidebar.button("Cerrar sesión"):
        st.session_state['logueado'] = False
        st.session_state['show_login'] = False
        st.session_state['menu'] = "📊 KPIs y Análisis"
        st.session_state['usuario'] = ""
        st.success("Sesión cerrada. Solo puedes ver KPIs.")

# === Vista de Login ===
def show_login():
    st.title("Acceso restringido")
    with st.form("login_form", clear_on_submit=False):
        usuario = st.text_input("Usuario")
        password = st.text_input("Contraseña", type="password")
        login_btn = st.form_submit_button("Ingresar")
        volver_btn = st.form_submit_button("Volver a KPIs y Análisis")
        
    if login_btn:
        if usuario in USUARIOS and password == USUARIOS[usuario]:
            st.session_state['logueado'] = True
            st.session_state['show_login'] = False
            st.session_state['usuario'] = usuario
            st.session_state['menu'] = "➕ Ingreso de muestra"
            st.success("Acceso concedido. Ya puedes usar todas las secciones.")
        else:
            st.error("Usuario o contraseña incorrectos.")
            st.session_state['logueado'] = False

    if volver_btn:
        st.session_state['show_login'] = False
        st.session_state['menu'] = "📊 KPIs y Análisis"

# === Lógica de navegación y contenido ===
if st.session_state['menu'] == "login":
    show_login()
    st.stop()

if st.session_state['menu'] == "➕ Ingreso de muestra" and st.session_state['logueado']:
    st.title("➕ Registro de nueva muestra")
    col1, col2 = st.columns(2)
    tz = pytz.timezone("America/Lima")
    now = datetime.now(tz)
    usuario_actual = st.session_state.get("usuario", "")
    is_admin = usuario_actual == "admin"

    with col1:
        # Operador
        if is_admin:
            tecnico = st.selectbox("👷 Operador", tecnicos)
        else:
            nombre_tecnico = USUARIOS_NOMBRES.get(usuario_actual, usuario_actual)
            st.markdown("**👷 Operador**")
            st.info(f"{nombre_tecnico}")
            tecnico = nombre_tecnico

        # Fecha
        fecha = st.date_input("Fecha", value=now.date(), max_value=now.date())
        # Hora de toma de muestra, aquí SIEMPRE aparece
        hora_muestra = st.time_input("Hora de toma de muestra", value=now.time())
        # Locación
        locacion = st.selectbox("📍 Locación de muestreo", locaciones)

    with col2:
        loc_norm = locacion.strip().lower()
        if loc_norm in SOLO_CLORO_LOCACIONES_NORM:
            ph = ""
            turbidez = ""
            cloro = st.number_input("Cloro Residual (mg/L)", min_value=0.0, step=0.1)
        else:
            ph = st.number_input("pH", min_value=0.0, max_value=14.0, step=0.1)
            turbidez = st.number_input("Turbidez (NTU)", min_value=0.0, step=0.1)
            cloro = st.number_input("Cloro Residual (mg/L)", min_value=0.0, step=0.1)

    observaciones = st.text_area("📝 Observaciones")
    foto = st.file_uploader("📷 Adjuntar foto (opcional)", type=["jpg", "jpeg", "png"])
    hora_registro = now.strftime("%H:%M:%S")

    if st.button("Guardar muestra"):
        nombre_foto = ""
        if foto and hasattr(foto, "name") and isinstance(foto.name, str) and foto.name:
            nombre_foto = f"{fecha.strftime('%Y%m%d')}_{locacion.replace(' ', '_')}_{foto.name}"
        muestra = [
            fecha.strftime("%Y-%m-%d"),
            hora_muestra.strftime("%H:%M"),
            hora_registro,
            tecnico,
            locacion,
            ph,
            turbidez,
            cloro,
            observaciones,
            nombre_foto
        ]
        guardar_muestra(muestra)
        st.success("✅ Registro guardado correctamente.")


elif st.session_state['menu'] == "📊 KPIs y Análisis":
    st.title("📊 Monitoreo de Parámetros en Agua Potable")
    df = leer_datos()
    if not df.empty:
        locaciones_mostrar = sorted(df["Locación"].dropna().unique())
        locacion_seleccionada = st.selectbox("Locación", locaciones_mostrar)
        loc_norm = locacion_seleccionada.strip().lower()
        df_filtrado = df[df["Locación"] == locacion_seleccionada]
        ultimos_30 = df_filtrado[df_filtrado["Fecha_Hora"] >= datetime.now() - pd.Timedelta(days=30)].sort_values("Fecha_Hora")
        # ---- FIX DECIMALES para gráficos
        for col in ["pH", "Turbidez (NTU)", "Cloro Residual (mg/L)"]:
            if col in ultimos_30.columns:
                ultimos_30[col] = (
                    ultimos_30[col]
                    .astype(str)
                    .str.replace(",", ".", regex=False)
                    .replace("", None)
                    .astype(float)
                )
        # ---------------
        if not ultimos_30.empty:
            # Eje x: Fecha + Hora de toma de muestra
            x_axis = ultimos_30["Fecha_Hora"]
            if loc_norm in SOLO_CLORO_LOCACIONES_NORM:
                # Solo mostrar cloro residual
                st.subheader("Cloro Residual (mg/L)")
                fig_cloro = go.Figure()
                fig_cloro.add_trace(go.Scatter(
                    x=x_axis,
                    y=ultimos_30["Cloro Residual (mg/L)"],
                    mode="lines+markers",
                    name="Cloro",
                    line=dict(color="purple")
                ))
                fig_cloro.add_hrect(y0=0.5, y1=1.5, fillcolor="green", opacity=0.15, line_width=0, annotation_text="Rango óptimo", annotation_position="top left")
                fig_cloro.add_hrect(y0=0.2, y1=0.5, fillcolor="yellow", opacity=0.13, line_width=0)
                fig_cloro.add_hrect(y0=1.5, y1=2.0, fillcolor="yellow", opacity=0.13, line_width=0)
                fig_cloro.add_hrect(y0=0, y1=0.2, fillcolor="red", opacity=0.07, line_width=0)
                fig_cloro.add_hrect(y0=2.0, y1=5, fillcolor="red", opacity=0.07, line_width=0)
                fig_cloro.update_layout(yaxis_title="Cloro Residual (mg/L)", xaxis_title="Fecha y hora de muestra", height=300)
                st.plotly_chart(fig_cloro, use_container_width=True)
            else:
                # Mostrar los tres: pH, Turbidez, Cloro
                st.subheader("pH")
                fig_ph = go.Figure()
                fig_ph.add_trace(go.Scatter(
                    x=x_axis,
                    y=ultimos_30["pH"],
                    mode="lines+markers",
                    name="pH",
                    line=dict(color="blue")
                ))
                fig_ph.add_hrect(y0=6.5, y1=8.5, fillcolor="green", opacity=0.15, line_width=0, annotation_text="Rango óptimo", annotation_position="top left")
                fig_ph.add_hrect(y0=6.0, y1=9.0, fillcolor="yellow", opacity=0.12, line_width=0)
                fig_ph.add_hrect(y0=0, y1=6.0, fillcolor="red", opacity=0.07, line_width=0)
                fig_ph.add_hrect(y0=9.0, y1=14.0, fillcolor="red", opacity=0.07, line_width=0)
                fig_ph.update_layout(yaxis_title="pH", xaxis_title="Fecha y hora de muestra", height=300)
                st.plotly_chart(fig_ph, use_container_width=True)

                st.subheader("Turbidez (NTU)")
                fig_turb = go.Figure()
                fig_turb.add_trace(go.Scatter(
                    x=x_axis,
                    y=ultimos_30["Turbidez (NTU)"],
                    mode="lines+markers",
                    name="Turbidez",
                    line=dict(color="orange")
                ))
                fig_turb.add_hrect(y0=0, y1=5, fillcolor="green", opacity=0.15, line_width=0, annotation_text="Rango óptimo (<5)", annotation_position="top left")
                fig_turb.add_hrect(y0=5, y1=10, fillcolor="yellow", opacity=0.13, line_width=0)
                fig_turb.add_hrect(y0=10, y1=100, fillcolor="red", opacity=0.09, line_width=0)
                fig_turb.update_layout(yaxis_title="Turbidez (NTU)", xaxis_title="Fecha y hora de muestra", height=300)
                st.plotly_chart(fig_turb, use_container_width=True)

                st.subheader("Cloro Residual (mg/L)")
                fig_cloro = go.Figure()
                fig_cloro.add_trace(go.Scatter(
                    x=x_axis,
                    y=ultimos_30["Cloro Residual (mg/L)"],
                    mode="lines+markers",
                    name="Cloro",
                    line=dict(color="purple")
                ))
                fig_cloro.add_hrect(y0=0.5, y1=1.5, fillcolor="green", opacity=0.15, line_width=0, annotation_text="Rango óptimo", annotation_position="top left")
                fig_cloro.add_hrect(y0=0.2, y1=0.5, fillcolor="yellow", opacity=0.13, line_width=0)
                fig_cloro.add_hrect(y0=1.5, y1=2.0, fillcolor="yellow", opacity=0.13, line_width=0)
                fig_cloro.add_hrect(y0=0, y1=0.2, fillcolor="red", opacity=0.07, line_width=0)
                fig_cloro.add_hrect(y0=2.0, y1=5, fillcolor="red", opacity=0.07, line_width=0)
                fig_cloro.update_layout(yaxis_title="Cloro Residual (mg/L)", xaxis_title="Fecha y hora de muestra", height=300)
                st.plotly_chart(fig_cloro, use_container_width=True)
        else:
            st.info("No hay registros de los últimos 30 días para graficar ni mostrar.")
    else:
        st.info("No hay datos registrados.")

elif st.session_state['menu'] == "📄 Historial" and st.session_state['logueado']:
    st.title("📄 Historial de muestras registradas")
    df = leer_datos()
    if not df.empty:
        locaciones_mostrar = sorted(df["Locación"].dropna().unique())
        locacion_hist = st.selectbox("Locación", locaciones_mostrar)
        loc_hist_norm = locacion_hist.strip().lower()
        df_filtrado = df[df["Locación"] == locacion_hist]
        min_fecha = df_filtrado["Fecha"].min()
        max_fecha = df_filtrado["Fecha"].max()
        if pd.isnull(min_fecha):
            min_fecha = datetime.now().date()
        else:
            min_fecha = min_fecha.date()
        if pd.isnull(max_fecha):
            max_fecha = datetime.now().date()
        else:
            max_fecha = max_fecha.date()
        col1, col2 = st.columns(2)
        with col1:
            fecha_ini = st.date_input("Desde", value=min_fecha)
        with col2:
            fecha_fin = st.date_input("Hasta", value=max_fecha)
        filtrado = df_filtrado[(df_filtrado["Fecha"] >= pd.to_datetime(fecha_ini)) & (df_filtrado["Fecha"] <= pd.to_datetime(fecha_fin))]
        # ---- FIX DECIMALES para historial
        for col in ["pH", "Turbidez (NTU)", "Cloro Residual (mg/L)"]:
            if col in filtrado.columns:
                filtrado[col] = (
                    filtrado[col]
                    .astype(str)
                    .str.replace(",", ".", regex=False)
                    .replace("", None)
                    .astype(float)
                )
        # Columnas a mostrar según locación
        if loc_hist_norm in SOLO_CLORO_LOCACIONES_NORM:
            columnas = ['Fecha', 'Hora de toma', 'Hora de registro', 'Técnico', 'Locación', 'Cloro Residual (mg/L)', '📝 Observaciones', 'Foto']
        else:
            columnas = ['Fecha', 'Hora de toma', 'Hora de registro', 'Técnico', 'Locación', 'pH', 'Turbidez (NTU)', 'Cloro Residual (mg/L)', '📝 Observaciones', 'Foto']
        columnas = [c for c in columnas if c in filtrado.columns]
        st.dataframe(filtrado[columnas])
    else:
        st.warning("No hay registros para mostrar.")

elif st.session_state['menu'] == "📥 Exportar" and st.session_state['logueado']:
    st.title("📥 Exportar registros en Excel")
    df = leer_datos()
    if not df.empty:
        st.download_button("📄 Descargar Excel", data=df.to_csv(index=False).encode("utf-8"), file_name="ptap_registros.csv", mime="text/csv")
    else:
        st.info("No hay datos para exportar.")
