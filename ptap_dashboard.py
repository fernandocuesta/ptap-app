import streamlit as st
import pandas as pd
import gspread
import plotly.graph_objects as go
from google.oauth2.service_account import Credentials
from datetime import datetime
import pytz

# --- Configuración ---
st.set_page_config(page_title="Control Logístico PTAP", page_icon="🚛", layout="wide")
LOGO_URL = "https://hcmpinturas.com/wp-content/uploads/2023/10/PetroTal-logo-star.png"
st.image(LOGO_URL, width=230)

# --- Usuarios ---
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

# --- Google Sheets ---
SHEET_URL = "https://docs.google.com/spreadsheets/d/19AZGamcT9AIkV6aR4Xs7CCObgBo8xKFlv4eXfrAUJuU/edit?usp=sharing"
SCOPE = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive"
]

@st.cache_resource(show_spinner=False)
def get_worksheet():
    creds = Credentials.from_service_account_info(st.secrets["gcp_service_account"], scopes=SCOPE)
    gc = gspread.authorize(creds)
    sh = gc.open_by_url(SHEET_URL)
    return sh.sheet1

# --- Sesión y navegación ---
for k, v in {"logueado": False, "show_login": False, "menu": "📊 KPIs y Análisis", "usuario": ""}.items():
    if k not in st.session_state:
        st.session_state[k] = v

# --- Listas base ---
TECNICOS = list(USUARIOS_NOMBRES.values())
LOCACIONES = [
    "Planta de Agua Potable", "Cocina", "Equipo Purificador - PTAP",
    "Dispensador - Comedor 2", "Dispensador - Oficina Gerencia",
    "Dispensador - HSE 01", "Dispensador - HSE 02", "Dispensador - Producción"
]
SOLO_CLORO_LOCACIONES = [
    "Equipo Purificador - PTAP", "Dispensador - Comedor 2",
    "Dispensador - Oficina Gerencia", "Dispensador - HSE 01",
    "Dispensador - HSE 02", "Dispensador - Producción"
]
SOLO_CLORO_LOCACIONES_NORM = [x.strip().lower() for x in SOLO_CLORO_LOCACIONES]

# --- Sidebar ---
st.sidebar.header("📂 Menú")
if st.session_state['logueado']:
    menu_options = ["➕ Ingreso de muestra", "📊 KPIs y Análisis", "📄 Historial", "📥 Exportar"]
else:
    menu_options = ["📊 KPIs y Análisis"]
if st.session_state['show_login']:
    st.session_state['menu'] = "login"
else:
    st.session_state['menu'] = st.sidebar.radio("Ir a:", menu_options, index=menu_options.index(st.session_state['menu']))
if not st.session_state['logueado']:
    if not st.session_state['show_login']:
        if st.sidebar.button("Iniciar sesión"):
            st.session_state['show_login'] = True
else:
    if st.sidebar.button("Cerrar sesión"):
        for k in ["logueado", "show_login"]:
            st.session_state[k] = False
        st.session_state['menu'] = "📊 KPIs y Análisis"
        st.session_state['usuario'] = ""
        st.success("Sesión cerrada. Solo puedes ver KPIs.")

# --- Funciones de datos ---
def leer_datos():
    try:
        worksheet = get_worksheet()
        data = worksheet.get_all_records()
        df = pd.DataFrame(data)
        if not df.empty and "Fecha" in df and "Hora de Toma" in df:
            df["Fecha_Hora"] = pd.to_datetime(df["Fecha"].astype(str) + " " + df["Hora de Toma"].astype(str), errors="coerce")
        return df
    except Exception as e:
        st.error(f"Error conectando a Google Sheets: {e}")
        return pd.DataFrame()

def guardar_muestra(muestra):
    try:
        worksheet = get_worksheet()
        worksheet.append_row(muestra)
    except Exception as e:
        st.error(f"Error guardando muestra: {e}")

def convertir_decimales(df, cols):
    for col in cols:
        if col in df.columns:
            df[col] = (
                df[col].astype(str)
                .str.replace(",", ".", regex=False)
                .replace("", None)
                .astype(float)
            )
    return df

# --- Login ---
def show_login():
    st.title("Acceso restringido")
    with st.form("login_form"):
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

# --- Lógica principal ---
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
            tecnico = st.selectbox("👷 Operador", TECNICOS)
        else:
            tecnico = USUARIOS_NOMBRES.get(usuario_actual, usuario_actual)
            st.markdown("**👷 Operador**")
            st.info(tecnico)

        # Fecha
        fecha = st.date_input("Fecha", value=now.date(), max_value=now.date())

        # --- HORA DE TOMA DE MUESTRA FIJA CON SESSION_STATE ---
        if "hora_toma_muestra" not in st.session_state:
            st.session_state["hora_toma_muestra"] = now.time()
        hora_muestra = st.time_input(
            "Hora de Toma de muestra",
            value=st.session_state["hora_toma_muestra"],
            key="hora_toma_muestra"
        )
        # -----------------------------------------------------

        # Locación
        locacion = st.selectbox("📍 Locación de muestreo", LOCACIONES)

    with col2:
        loc_norm = locacion.strip().lower()
        ph = turbidez = ""
        if loc_norm in SOLO_CLORO_LOCACIONES_NORM:
            cloro = st.number_input("Cloro Residual (mg/L)", min_value=0.0, step=0.1)
        else:
            ph = st.number_input("pH", min_value=0.0, max_value=14.0, step=0.1)
            turbidez = st.number_input("Turbidez (NTU)", min_value=0.0, step=0.1)
            cloro = st.number_input("Cloro Residual (mg/L)", min_value=0.0, step=0.1)

    observaciones = st.text_area("📝 Observaciones")
    foto = st.file_uploader("📷 Adjuntar foto (opcional)", type=["jpg", "jpeg", "png"])
    hora_registro = now.strftime("%H:%M:%S")   # Hora exacta al guardar

    if st.button("Guardar muestra"):
        nombre_foto = ""
        if foto and getattr(foto, "name", None):
            nombre_foto = f"{fecha.strftime('%Y%m%d')}_{locacion.replace(' ', '_')}_{foto.name}"
        muestra = [
            fecha.strftime("%Y-%m-%d"),         # Fecha
            hora_muestra.strftime("%H:%M"),     # Hora de Toma (la elegida por el usuario)
            hora_registro,                      # Hora de Registro (cuando se presiona el botón)
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
        ultimos_30 = convertir_decimales(ultimos_30, ["pH", "Turbidez (NTU)", "Cloro Residual (mg/L)"])
        x_axis = ultimos_30["Fecha_Hora"]
        if not ultimos_30.empty:
            if loc_norm in SOLO_CLORO_LOCACIONES_NORM:
                st.subheader("Cloro Residual (mg/L)")
                fig_cloro = go.Figure()
                fig_cloro.add_trace(go.Scatter(x=x_axis, y=ultimos_30["Cloro Residual (mg/L)"], mode="lines+markers", name="Cloro"))
                fig_cloro.add_hrect(y0=0.5, y1=1.5, fillcolor="green", opacity=0.15, line_width=0, annotation_text="Rango óptimo", annotation_position="top left")
                fig_cloro.add_hrect(y0=0.2, y1=0.5, fillcolor="yellow", opacity=0.13, line_width=0)
                fig_cloro.add_hrect(y0=1.5, y1=2.0, fillcolor="yellow", opacity=0.13, line_width=0)
                fig_cloro.add_hrect(y0=0, y1=0.2, fillcolor="red", opacity=0.07, line_width=0)
                fig_cloro.add_hrect(y0=2.0, y1=5, fillcolor="red", opacity=0.07, line_width=0)
                fig_cloro.update_layout(yaxis_title="Cloro Residual (mg/L)", xaxis_title="Fecha y hora de muestra", height=300)
                st.plotly_chart(fig_cloro, use_container_width=True)
            else:
                for param, color, rango, subtitulo in [
                    ("pH", "blue", [(6.5, 8.5, "green", 0.15), (6.0, 9.0, "yellow", 0.12), (0, 6.0, "red", 0.07), (9.0, 14.0, "red", 0.07)], "pH"),
                    ("Turbidez (NTU)", "orange", [(0, 5, "green", 0.15), (5, 10, "yellow", 0.13), (10, 100, "red", 0.09)], "Turbidez (NTU)"),
                    ("Cloro Residual (mg/L)", "purple", [(0.5, 1.5, "green", 0.15), (0.2, 0.5, "yellow", 0.13), (1.5, 2.0, "yellow", 0.13), (0, 0.2, "red", 0.07), (2.0, 5, "red", 0.07)], "Cloro Residual (mg/L)")
                ]:
                    st.subheader(subtitulo)
                    fig = go.Figure()
                    fig.add_trace(go.Scatter(x=x_axis, y=ultimos_30[param], mode="lines+markers", name=param))
                    for y0, y1, fc, op in rango:
                        fig.add_hrect(y0=y0, y1=y1, fillcolor=fc, opacity=op, line_width=0)
                    if param == "pH":
                        fig.update_layout(yaxis_title="pH", xaxis_title="Fecha y hora de muestra", height=300)
                    elif param == "Turbidez (NTU)":
                        fig.update_layout(yaxis_title="Turbidez (NTU)", xaxis_title="Fecha y hora de muestra", height=300)
                    else:
                        fig.update_layout(yaxis_title="Cloro Residual (mg/L)", xaxis_title="Fecha y hora de muestra", height=300)
                    st.plotly_chart(fig, use_container_width=True)
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
        
        # --- Manejo robusto de fechas mínimas y máximas ---
        min_fecha_raw = df_filtrado["Fecha"].min()
        max_fecha_raw = df_filtrado["Fecha"].max()

        try:
            min_fecha = pd.to_datetime(min_fecha_raw).date()
        except Exception:
            min_fecha = datetime.now().date()
        try:
            max_fecha = pd.to_datetime(max_fecha_raw).date()
        except Exception:
            max_fecha = datetime.now().date()
        # ---------------------------------------------------

        col1, col2 = st.columns(2)
        with col1:
            fecha_ini = st.date_input("Desde", value=min_fecha)
        with col2:
            fecha_fin = st.date_input("Hasta", value=max_fecha)
        filtrado = df_filtrado[
            (pd.to_datetime(df_filtrado["Fecha"]) >= pd.to_datetime(fecha_ini)) &
            (pd.to_datetime(df_filtrado["Fecha"]) <= pd.to_datetime(fecha_fin))
        ]
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
            columnas = ['Fecha', 'Hora de Toma', 'Hora de Registro', 'Operador', 'Locación', 'Cloro Residual (mg/L)', 'Observaciones', 'Foto']
        else:
            columnas = ['Fecha', 'Hora de Toma', 'Hora de Registro', 'Operador', 'Locación', 'pH', 'Turbidez (NTU)', 'Cloro Residual (mg/L)', 'Observaciones', 'Foto']
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
