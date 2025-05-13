import streamlit as st
import pandas as pd
from datetime import datetime
import plotly.express as px
import os
from fpdf import FPDF
from PIL import Image

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
locaciones = ["Cocina", "Bebedero 1", "Bebedero 2", "Bebedero 3"]

st.sidebar.header("📂 Navegación")
menu = st.sidebar.radio("Ir a:", ["➕ Ingreso de muestra", "📊 KPIs y Análisis", "📄 Historial", "📤 Exportar PDF"])

if menu == "➕ Ingreso de muestra":
    st.title("➕ Registro de nueva muestra")
    col1, col2 = st.columns(2)
    with col1:
        fecha = st.date_input("Fecha", value=datetime.today())
        hora = st.time_input("Hora", value=datetime.now().time())
        tecnico = st.selectbox("👷 Técnico", tecnicos)
        locacion = st.selectbox("📍 Locación de muestreo", locaciones)
    with col2:
        if locacion == "Cocina":
            ph = st.number_input("pH", min_value=0.0, max_value=14.0, step=0.1)
            turbidez = None
            cloro = st.number_input("Cloro Residual (mg/L)", min_value=0.0, step=0.1)
        else:
            ph = st.number_input("pH", min_value=0.0, max_value=14.0, step=0.1)
            turbidez = st.number_input("Turbidez (NTU)", min_value=0.0, step=0.1)
            cloro = st.number_input("Cloro Residual (mg/L)", min_value=0.0, step=0.1)
    observaciones = st.text_area("📝 Observaciones")
    foto = st.file_uploader("📷 Adjuntar foto (opcional)", type=["jpg", "jpeg", "png"])

    alerta = []
    if ph < 6.5 or ph > 8.5:
        alerta.append("⚠️ pH fuera de rango ideal (6.5 - 8.5)")
    if turbidez is not None and turbidez > 5:
        alerta.append("⚠️ Turbidez mayor a 5 NTU")
    if cloro < 0.5 or cloro > 1.5:
        alerta.append("⚠️ Cloro fuera del rango ideal (0.5 - 1.5 mg/L)")
    for msg in alerta:
        st.warning(msg)

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