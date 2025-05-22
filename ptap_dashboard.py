import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime
import pytz

# --- Google Sheets Authentication ---
scope = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive"
]
creds = Credentials.from_service_account_info(
    st.secrets["gcp_service_account"], scopes=scope
)
gc = gspread.authorize(creds)
SHEET_URL = "https://docs.google.com/spreadsheets/d/19AZGamcT9AIkV6aR4Xs7CCObgBo8xKFlv4eXfrAUJuU/edit?usp=sharing"
sh = gc.open_by_url(SHEET_URL)
worksheet = sh.sheet1

def leer_datos():
    data = worksheet.get_all_records()
    df = pd.DataFrame(data)
    # Ajuste: convierte la columna Fecha a datetime para filtrar y analizar
    if not df.empty and "Fecha" in df.columns:
        df["Fecha"] = pd.to_datetime(df["Fecha"], errors="coerce")
    return df

def guardar_muestra(muestra):
    worksheet.append_row(muestra)

tecnicos = ["Fernando Cuesta", "Felix Cuadros"]
locaciones = [
    "L95-AC-SUR-COM2", "L95-AC-SUR-PTAP", "L95-AC-SUR-GC",
    "L95-AC-SUR-HSE-01", "L95-AC-SUR-HSE-02", "L95-AC-SUR-PROD"
]

st.set_page_config(page_title="Control Logístico PTAP", page_icon="🚛", layout="wide")
st.sidebar.header("📂 Navegación")
menu = st.sidebar.radio("Ir a:", ["➕ Ingreso de muestra", "📊 KPIs y Análisis", "📄 Historial", "📥 Exportar"])

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
    # Foto: sólo se registra el nombre en la sheet, NO se guarda archivo
    foto = st.file_uploader("📷 Adjuntar foto (opcional)", type=["jpg", "jpeg", "png"])

    if st.button("Guardar muestra"):
        nombre_foto = ""
        if foto and hasattr(foto, "name") and isinstance(foto.name, str) and foto.name:
            nombre_foto = f"{fecha.strftime('%Y%m%d')}_{locacion.replace(' ', '_')}_{foto.name}"
            # El archivo NO se almacena, solo el nombre para referencia
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

elif menu == "📊 KPIs y Análisis":
    st.title("📊 KPIs y Análisis de datos por locación")
    df = leer_datos()
    if not df.empty:
        locacion_seleccionada = st.selectbox("Locación", sorted(df["Locación"].dropna().unique()))
        df_filtrado = df[df["Locación"] == locacion_seleccionada]
        ultimos_30 = df_filtrado[df_filtrado["Fecha"] >= datetime.now() - pd.Timedelta(days=30)]
        ph_avg = round(ultimos_30["pH"].mean(), 2)
        tur_avg = round(ultimos_30["Turbidez (NTU)"].mean(), 2)
        clo_avg = round(ultimos_30["Cloro Residual (mg/L)"].mean(), 2)
        k1, k2, k3 = st.columns(3)
        k1.metric("Prom. pH (30d)", ph_avg)
        k2.metric("Prom. Turbidez (30d)", tur_avg)
        k3.metric("Prom. Cloro (30d)", clo_avg)
    else:
        st.info("No hay datos registrados.")

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

elif menu == "📥 Exportar":
    st.title("📥 Exportar registros en Excel")
    df = leer_datos()
    if not df.empty:
        st.download_button("📄 Descargar Excel", data=df.to_csv(index=False).encode("utf-8"), file_name="ptap_registros.csv", mime="text/csv")
    else:
        st.info("No hay datos para exportar.")
