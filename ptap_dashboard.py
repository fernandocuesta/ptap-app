import streamlit as st
import pandas as pd
import gspread
import plotly.graph_objects as go
from google.oauth2.service_account import Credentials
from datetime import datetime
import pytz

# --- Configura credenciales aquí ---
USUARIO = "admin"
PASSWORD = "1234"

# --- Google Sheets Authentication ---
scope = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive"
]
try:
    creds = Credentials.from_service_account_info(
        st.secrets["gcp_service_account"], scopes=scope
    )
    gc = gspread.authorize(creds)
    SHEET_URL = "https://docs.google.com/spreadsheets/d/19AZGamcT9AIkV6aR4Xs7CCObgBo8xKFlv4eXfrAUJuU/edit?usp=sharing"
    sh = gc.open_by_url(SHEET_URL)
    worksheet = sh.sheet1
except Exception as e:
    st.error(f"Error conectando a Google Sheets: {e}")
    worksheet = None  # Así la app sigue para ver el login

def leer_datos():
    if worksheet is None:
        return pd.DataFrame()
    data = worksheet.get_all_records()
    df = pd.DataFrame(data)
    if not df.empty and "Fecha" in df.columns:
        df["Fecha"] = pd.to_datetime(df["Fecha"], errors="coerce")
    return df

def guardar_muestra(muestra):
    if worksheet is not None:
        worksheet.append_row(muestra)

tecnicos = ["Fernando Cuesta", "Felix Cuadros"]
locaciones = [
    "L95-AC-SUR-COM2", "L95-AC-SUR-PTAP", "L95-AC-SUR-GC",
    "L95-AC-SUR-HSE-01", "L95-AC-SUR-HSE-02", "L95-AC-SUR-PROD"
]

# --------- LOGIN FUNCTION ----------
def login():
    st.title("Acceso restringido")
    usuario = st.text_input("Usuario")
    password = st.text_input("Contraseña", type="password")
    if st.button("Ingresar"):
        if usuario == USUARIO and password == PASSWORD:
            st.session_state['logueado'] = True
            st.success("Acceso concedido.")
            st.experimental_rerun()
        else:
            st.error("Usuario o contraseña incorrectos.")
    st.stop()

# --------- MENÚ Y CONTROL DE ACCESO ROBUSTO ----------
st.set_page_config(page_title="Control Logístico PTAP", page_icon="🚛", layout="wide")
st.sidebar.header("📂 Navegación")
menu = st.sidebar.radio("Ir a:", ["➕ Ingreso de muestra", "📊 KPIs y Análisis", "📄 Historial", "📥 Exportar"])

# DEBUG (puedes comentar esto luego)
st.write("DEBUG - Menú seleccionado:", menu)
st.write("DEBUG - Logueado:", st.session_state.get("logueado", False))

# Botón de logout SI está logueado
if st.session_state.get("logueado", False):
    if st.sidebar.button("Cerrar sesión"):
        st.session_state['logueado'] = False
        st.success("Sesión cerrada. Puedes seguir accediendo a KPIs o iniciar sesión para módulos privados.")
        st.experimental_rerun()

# Las secciones que requieren login
secciones_privadas = ["➕ Ingreso de muestra", "📄 Historial", "📥 Exportar"]

# --- Control de acceso robusto (solo pide login si hace falta) ---
if menu in secciones_privadas:
    if 'logueado' not in st.session_state or not st.session_state['logueado']:
        login()
        st.stop()

# --------- SECCIÓN INGRESO DE MUESTRA (privada) ----------
if menu == "➕ Ingreso de muestra":
    st.title("➕ Registro de nueva muestra")
    col1, col2 = st.columns(2)
    tz = pytz.timezone("America/Lima")
    now = datetime.now(tz)
    with col1:
        fecha = st.date_input("Fecha", value=now.date(), max_value=now.date())
        hora = now.time().strftime("%H:%M")
        tecnico = st.selectbox("👷 Técnico", tecnicos)
        locacion = st.selectbox("📍 Locación de muestreo", locaciones)
    with col2:
        ph = st.number_input("pH", min_value=0.0, max_value=14.0, step=0.1)
        turbidez = st.number_input("Turbidez (NTU)", min_value=0.0, step=0.1)
        cloro = st.number_input("Cloro Residual (mg/L)", min_value=0.0, step=0.1)
    observaciones = st.text_area("📝 Observaciones")
    foto = st.file_uploader("📷 Adjuntar foto (opcional)", type=["jpg", "jpeg", "png"])

    if st.button("Guardar muestra"):
        nombre_foto = ""
        if foto and hasattr(foto, "name") and isinstance(foto.name, str) and foto.name:
            nombre_foto = f"{fecha.strftime('%Y%m%d')}_{locacion.replace(' ', '_')}_{foto.name}"
        muestra = [
            fecha.strftime("%Y-%m-%d"),
            hora,
            tecnico,
            locacion,
            ph,
            turbidez,
            cloro,
            observaciones,
            nombre_foto
        ]
        guardar_muestra(muestra)
        st.success("✅ Registro guardado en Google Sheets correctamente.")

# --------- SECCIÓN KPIs y ANÁLISIS (PÚBLICA) ----------
elif menu == "📊 KPIs y Análisis":
    st.title("📊 KPIs y Análisis de datos por locación")
    df = leer_datos()
    if not df.empty:
        locacion_seleccionada = st.selectbox("Locación", sorted(df["Locación"].dropna().unique()))
        df_filtrado = df[df["Locación"] == locacion_seleccionada]
        ultimos_30 = df_filtrado[df_filtrado["Fecha"] >= datetime.now() - pd.Timedelta(days=30)].sort_values("Fecha")

        if not ultimos_30.empty:
            # --- Gráficos ---
            st.subheader("pH")
            fig_ph = go.Figure()
            fig_ph.add_trace(go.Scatter(x=ultimos_30["Fecha"], y=ultimos_30["pH"], mode="lines+markers", name="pH", line=dict(color="blue")))
            fig_ph.add_hrect(y0=6.5, y1=8.5, fillcolor="green", opacity=0.15, line_width=0, annotation_text="Rango óptimo", annotation_position="top left")
            fig_ph.add_hrect(y0=6.0, y1=9.0, fillcolor="yellow", opacity=0.12, line_width=0)
            fig_ph.add_hrect(y0=0, y1=6.0, fillcolor="red", opacity=0.07, line_width=0)
            fig_ph.add_hrect(y0=9.0, y1=14.0, fillcolor="red", opacity=0.07, line_width=0)
            fig_ph.update_layout(yaxis_title="pH", xaxis_title="Fecha", height=300)
            st.plotly_chart(fig_ph, use_container_width=True)

            st.subheader("Turbidez (NTU)")
            fig_turb = go.Figure()
            fig_turb.add_trace(go.Scatter(x=ultimos_30["Fecha"], y=ultimos_30["Turbidez (NTU)"], mode="lines+markers", name="Turbidez", line=dict(color="orange")))
            fig_turb.add_hrect(y0=0, y1=5, fillcolor="green", opacity=0.15, line_width=0, annotation_text="Rango óptimo (<5)", annotation_position="top left")
            fig_turb.add_hrect(y0=5, y1=10, fillcolor="yellow", opacity=0.13, line_width=0)
            fig_turb.add_hrect(y0=10, y1=100, fillcolor="red", opacity=0.09, line_width=0)
            fig_turb.update_layout(yaxis_title="Turbidez (NTU)", xaxis_title="Fecha", height=300)
            st.plotly_chart(fig_turb, use_container_width=True)

            st.subheader("Cloro Residual (mg/L)")
            fig_cloro = go.Figure()
            fig_cloro.add_trace(go.Scatter(x=ultimos_30["Fecha"], y=ultimos_30["Cloro Residual (mg/L)"], mode="lines+markers", name="Cloro", line=dict(color="purple")))
            fig_cloro.add_hrect(y0=0.5, y1=1.5, fillcolor="green", opacity=0.15, line_width=0, annotation_text="Rango óptimo", annotation_position="top left")
            fig_cloro.add_hrect(y0=0.2, y1=0.5, fillcolor="yellow", opacity=0.13, line_width=0)
            fig_cloro.add_hrect(y0=1.5, y1=2.0, fillcolor="yellow", opacity=0.13, line_width=0)
            fig_cloro.add_hrect(y0=0, y1=0.2, fillcolor="red", opacity=0.07, line_width=0)
            fig_cloro.add_hrect(y0=2.0, y1=5, fillcolor="red", opacity=0.07, line_width=0)
            fig_cloro.update_layout(yaxis_title="Cloro Residual (mg/L)", xaxis_title="Fecha", height=300)
            st.plotly_chart(fig_cloro, use_container_width=True)
        else:
            st.info("No hay registros de los últimos 30 días para graficar ni mostrar.")
    else:
        st.info("No hay datos registrados.")

# --------- SECCIÓN HISTORIAL (privada) ----------
elif menu == "📄 Historial":
    st.title("📄 Historial de muestras registradas")
    df = leer_datos()
    if not df.empty:
        col1, col2 = st.columns(2)
        min_fecha = df["Fecha"].min()
        max_fecha = df["Fecha"].max()
        if pd.isnull(min_fecha):
            min_fecha = datetime.now().date()
        else:
            min_fecha = min_fecha.date()
        if pd.isnull(max_fecha):
            max_fecha = datetime.now().date()
        else:
            max_fecha = max_fecha.date()
        with col1:
            fecha_ini = st.date_input("Desde", value=min_fecha)
        with col2:
            fecha_fin = st.date_input("Hasta", value=max_fecha)
        filtrado = df[(df["Fecha"] >= pd.to_datetime(fecha_ini)) & (df["Fecha"] <= pd.to_datetime(fecha_fin))]
        st.dataframe(filtrado)
    else:
        st.warning("No hay registros para mostrar.")

# --------- SECCIÓN EXPORTAR (privada) ----------
elif menu == "📥 Exportar":
    st.title("📥 Exportar registros en Excel")
    df = leer_datos()
    if not df.empty:
        st.download_button("📄 Descargar Excel", data=df.to_csv(index=False).encode("utf-8"), file_name="ptap_registros.csv", mime="text/csv")
    else:
        st.info("No hay datos para exportar.")
