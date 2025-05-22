
import streamlit as st
import pandas as pd
import os
from datetime import datetime
import pytz
from io import BytesIO

st.set_page_config(page_title="Control Logístico PTAP", page_icon="🚛", layout="wide")

DATA_FILE = "ptap_data.csv"
FOTOS_DIR = "fotos"
os.makedirs(FOTOS_DIR, exist_ok=True)

def cargar_datos():
    try:
        return pd.read_csv(DATA_FILE)
    except FileNotFoundError:
        return pd.DataFrame(columns=["Fecha", "Hora", "Técnico", "Locación", "pH", "Turbidez (NTU)",
                                     "Cloro Residual (mg/L)", "Observaciones", "Foto"])

def guardar_datos(df):
    df.to_csv(DATA_FILE, index=False)

if "data" not in st.session_state:
    st.session_state.data = cargar_datos()

tecnicos = ["Fernando Cuesta", "Felix Cuadros"]
locaciones = ["L95-AC-SUR-COM2", "L95-AC-SUR-PTAP", "L95-AC-SUR-GC", "L95-AC-SUR-HSE-01", "L95-AC-SUR-HSE-02", "L95-AC-SUR-PROD"]

st.sidebar.header("📂 Navegación")
menu = st.sidebar.radio("Ir a:", ["➕ Ingreso de muestra", "📊 KPIs y Análisis", "📄 Historial", "📥 Exportar"])

if menu == "➕ Ingreso de muestra":
    st.title("➕ Registro de nueva muestra")
    tz = pytz.timezone('America/Lima')
    now = datetime.now(tz)
    col1, col2 = st.columns(2)
    with col1:
        fecha = st.date_input("Fecha", value=now.date(), max_value=now.date())
        hora = now.time()
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
        if foto:
            nombre_foto = f"{fecha.strftime('%Y%m%d')}_{hora.strftime('%H%M')}_{locacion.replace(' ', '_')}_{foto.name}"
            with open(os.path.join(FOTOS_DIR, nombre_foto), "wb") as f:
                f.write(foto.read())
        nueva = {
            "Fecha": fecha.strftime("%Y-%m-%d"),
            "Hora": hora.strftime("%H:%M"),
            "Técnico": tecnico,
            "Locación": locacion,
            "pH": ph,
            "Turbidez (NTU)": turbidez,
            "Cloro Residual (mg/L)": cloro,
            "Observaciones": observaciones,
            "Foto": nombre_foto
        }
        df = st.session_state.data
        duplicado = df[(df["Fecha"] == nueva["Fecha"]) & (df["Hora"] == nueva["Hora"]) & (df["Locación"] == nueva["Locación"])]
        if not duplicado.empty:
            st.error("❌ Ya existe un registro con esta fecha, hora y locación.")
        else:
            st.session_state.data = pd.concat([df, pd.DataFrame([nueva])], ignore_index=True)
            guardar_datos(st.session_state.data)
            st.success("✅ Registro guardado correctamente.")

elif menu == "📊 KPIs y Análisis":
    st.title("📊 KPIs y Análisis de datos por locación")
    df = st.session_state.data.copy()
    df["Fecha"] = pd.to_datetime(df["Fecha"])
    locacion_seleccionada = st.selectbox("Locación", sorted(df["Locación"].unique()))
    df_filtrado = df[df["Locación"] == locacion_seleccionada]
    ultimos_30 = df_filtrado[df_filtrado["Fecha"] >= datetime.now() - pd.Timedelta(days=30)]
    ph_avg = round(ultimos_30["pH"].mean(), 2)
    tur_avg = round(ultimos_30["Turbidez (NTU)"].mean(), 2)
    clo_avg = round(ultimos_30["Cloro Residual (mg/L)"].mean(), 2)
    k1, k2, k3 = st.columns(3)
    with k1: st.metric("Prom. pH", ph_avg)
    with k2: st.metric("Prom. Turbidez", tur_avg)
    with k3: st.metric("Prom. Cloro", clo_avg)

elif menu == "📄 Historial":
    st.title("📄 Historial de muestras registradas")
    df = st.session_state.data.copy()
    df["Fecha"] = pd.to_datetime(df["Fecha"])
    if df.empty:
        st.info("No hay registros para mostrar.")
    else:
        fecha_ini = st.date_input("Desde", value=df["Fecha"].min().date())
        fecha_fin = st.date_input("Hasta", value=df["Fecha"].max().date())
        df_filtrado = df[(df["Fecha"] >= pd.to_datetime(fecha_ini)) & (df["Fecha"] <= pd.to_datetime(fecha_fin))]
        for i, row in df_filtrado.iterrows():
            st.write(f"{row['Fecha']} - {row['Hora']} - {row['Técnico']} - {row['Locación']} - pH: {row['pH']} - Turbidez: {row['Turbidez (NTU)']} - Cloro: {row['Cloro Residual (mg/L)']}")
            if st.button(f"🗑️ Eliminar registro {i}", key=f"del_{i}"):
                st.session_state.data.drop(index=i, inplace=True)
                st.session_state.data.reset_index(drop=True, inplace=True)
                guardar_datos(st.session_state.data)
                st.experimental_rerun()

elif menu == "📥 Exportar":
    st.title("📥 Exportar registros en Excel")
    df = st.session_state.data.copy()
    if not df.empty:
        st.download_button("📄 Descargar Excel", data=df.to_csv(index=False).encode("utf-8"),
                           file_name="ptap_registros.csv", mime="text/csv")
    else:
        st.info("No hay datos para exportar.")
