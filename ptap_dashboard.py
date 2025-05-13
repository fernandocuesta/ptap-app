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
        return pd.DataFrame(columns=["Fecha", "Hora", "Supervisor", "Locación", "pH", "Turbidez (NTU)",
                                     "Cloro Residual (mg/L)", "Observaciones", "Foto"])

def guardar_datos(df):
    df.to_csv(DATA_FILE, index=False)

if "data" not in st.session_state:
    st.session_state.data = cargar_datos()

supervisores = ["Fernando Cuesta", "Felix Cuadros"]
locaciones = ["Cocina", "Bebedero 1", "Bebedero 2", "Bebedero 3"]

st.sidebar.header("📂 Navegación")
menu = st.sidebar.radio("Ir a:", ["➕ Ingreso de muestra", "📊 KPIs y Análisis", "📄 Historial", "📤 Exportar PDF"])