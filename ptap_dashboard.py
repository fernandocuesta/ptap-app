
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

# Inicializa el CSV vacío con la nueva estructura
def inicializar_datos():
    columnas = ["Fecha", "Hora", "Técnico", "Locación", "pH", "Turbidez (NTU)",
                "Cloro Residual (mg/L)", "Observaciones", "Foto"]
    df = pd.DataFrame(columns=columnas)
    df.to_csv(DATA_FILE, index=False)
    return df

def cargar_datos():
    if not os.path.exists(DATA_FILE):
        return inicializar_datos()
    return pd.read_csv(DATA_FILE)

def guardar_datos(df):
    df.to_csv(DATA_FILE, index=False)

if "data" not in st.session_state:
    st.session_state.data = cargar_datos()

tecnicos = ["Fernando Cuesta", "Felix Cuadros"]
locaciones = [
    "L95-AC-SUR-COM2",
    "L95-AC-SUR-PTAP",
    "L95-AC-SUR-GC",
    "L95-AC-SUR-HSE-01",
    "L95-AC-SUR-HSE-02",
    "L95-AC-SUR-PROD"
]

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
        if locacion == "L95-AC-SUR-PTAP":
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
        st.session_state.data = pd.concat([df, pd.DataFrame([nueva])], ignore_index=True)
        guardar_datos(st.session_state.data)
        st.success("✅ Registro guardado correctamente.")

elif menu == "📊 KPIs y Análisis":
    st.title("📊 KPIs y Análisis de datos por locación")
    df = st.session_state.data.copy()
    if not df.empty:
        df["Fecha"] = pd.to_datetime(df["Fecha"])
        locacion_seleccionada = st.selectbox("Locación", sorted(df["Locación"].unique()))
        df_loc = df[df["Locación"] == locacion_seleccionada]

        if not df_loc.empty:
            ultimos_30 = df_loc[df_loc["Fecha"] >= datetime.now() - pd.Timedelta(days=30)]
            ph_avg = round(ultimos_30["pH"].mean(), 2)
            tur_avg = round(ultimos_30["Turbidez (NTU)"].mean(), 2)
            clo_avg = round(ultimos_30["Cloro Residual (mg/L)"].mean(), 2)

            k1, k2, k3 = st.columns(3)
            k1.metric("Prom. pH", ph_avg)
            k2.metric("Prom. Turbidez", tur_avg)
            k3.metric("Prom. Cloro", clo_avg)

            for param in ["pH", "Turbidez (NTU)", "Cloro Residual (mg/L)"]:
                fig = px.line(df_loc, x="Fecha", y=param, markers=True, title=f"{param} en {locacion_seleccionada}")
                st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No hay datos para esta locación.")

elif menu == "📄 Historial":
    st.title("📄 Historial de muestras registradas")
    df = st.session_state.data.copy()
    if not df.empty:
        df["Fecha"] = pd.to_datetime(df["Fecha"])
        colf1, colf2, colf3 = st.columns(3)
        with colf1:
            fecha_ini = st.date_input("Desde", value=df["Fecha"].min())
        with colf2:
            fecha_fin = st.date_input("Hasta", value=df["Fecha"].max())
        with colf3:
            loc_fil = st.selectbox("Locación", ["Todas"] + sorted(df["Locación"].unique()))

        df = df[(df["Fecha"] >= pd.to_datetime(fecha_ini)) & (df["Fecha"] <= pd.to_datetime(fecha_fin))]
        if loc_fil != "Todas":
            df = df[df["Locación"] == loc_fil]

        for i, row in df.iterrows():
            with st.expander(f"📌 {row['Fecha']} - {row['Hora']} - {row['Locación']}"):
                st.write(f"👷 **Técnico:** {row['Técnico']}")
                st.write(f"pH: {row['pH']} | Turbidez: {row['Turbidez (NTU)']} | Cloro: {row['Cloro Residual (mg/L)']}")
                st.write(f"📝 **Observaciones:** {row['Observaciones']}")
                if isinstance(row['Foto'], str) and row['Foto'].strip():
                    path = os.path.join(FOTOS_DIR, row['Foto'])
                    if os.path.exists(path):
                        st.image(path, width=100)
        if st.button("⬇️ Descargar Excel"):
            df.to_excel("historial_ptap.xlsx", index=False)
            with open("historial_ptap.xlsx", "rb") as file:
                st.download_button("📥 Descargar archivo Excel", data=file, file_name="historial_ptap.xlsx")

elif menu == "📤 Exportar PDF":
    st.title("📤 Generador de reportes PDF")
    df = st.session_state.data.copy()
    if not df.empty and st.button("📥 Generar PDF del resumen actual"):
        pdf = FPDF()
        pdf.add_page()
        pdf.set_font("Arial", size=12)
        pdf.cell(200, 10, txt="Reporte de Muestras PTAP", ln=True, align="C")
        pdf.ln(5)
        for i, row in df.tail(10).iterrows():
            pdf.set_font("Arial", style="B", size=10)
            pdf.cell(0, 10, txt=f"{row['Fecha']} {row['Hora']} - {row['Locación']}", ln=True)
            pdf.set_font("Arial", size=10)
            pdf.cell(0, 10, txt=f"Técnico: {row['Técnico']}", ln=True)
            pdf.cell(0, 10, txt=f"pH: {row['pH']} | Turbidez: {row['Turbidez (NTU)']} | Cloro: {row['Cloro Residual (mg/L)']}", ln=True)
            pdf.multi_cell(0, 10, txt=f"Observaciones: {row['Observaciones']}")
            pdf.ln(5)
        pdf.output("reporte_ptap.pdf")
        with open("reporte_ptap.pdf", "rb") as f:
            st.download_button("📄 Descargar PDF", data=f, file_name="reporte_ptap.pdf")
