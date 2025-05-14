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
    if os.path.exists(DATA_FILE):
        return pd.read_csv(DATA_FILE)
    else:
        return pd.DataFrame(columns=["Fecha", "Hora", "Técnico", "Locación", "pH", "Turbidez (NTU)",
                                     "Cloro Residual (mg/L)", "Observaciones", "Foto"])

def guardar_datos(df):
    df.to_csv(DATA_FILE, index=False)

if "data" not in st.session_state:
    st.session_state.data = cargar_datos()

tecnicos = ["Fernando Cuesta", "Felix Cuadros"]
locaciones = ["L95-AC-SUR-COM2", "L95-AC-SUR-PTAP", "L95-AC-SUR-GC", "L95-AC-SUR-HSE-01", "L95-AC-SUR-HSE-02", "L95-AC-SUR-PROD"]

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

        duplicado = st.session_state.data[
            (st.session_state.data["Fecha"] == nueva["Fecha"]) &
            (st.session_state.data["Hora"] == nueva["Hora"]) &
            (st.session_state.data["Locación"] == nueva["Locación"])
        ]

        if not duplicado.empty:
            st.error("❌ Ya existe un registro con esta fecha, hora y locación.")
        else:
            st.session_state.data = pd.concat([st.session_state.data, pd.DataFrame([nueva])], ignore_index=True)
            guardar_datos(st.session_state.data)
            st.success("✅ Registro guardado correctamente.")

elif menu == "📊 KPIs y Análisis":
    st.title("📊 KPIs y Análisis de datos por locación")
    df = st.session_state.data.copy()
    if df.empty:
        st.info("No hay datos disponibles para mostrar.")
    else:
        df["Fecha"] = pd.to_datetime(df["Fecha"])
        ultimos_30 = df[df["Fecha"] >= datetime.now() - pd.Timedelta(days=30)]

        ph_avg = round(ultimos_30["pH"].mean(), 2)
        tur_avg = round(ultimos_30["Turbidez (NTU)"].mean(), 2)
        clo_avg = round(ultimos_30["Cloro Residual (mg/L)"].mean(), 2)

        ph_color = "🟢" if 6.5 <= ph_avg <= 8.5 else "🔴"
        tur_color = "🟢" if tur_avg <= 5 else "🔴"
        clo_color = "🟢" if 0.5 <= clo_avg <= 1.5 else "🔴"

        kpi1, kpi2, kpi3 = st.columns(3)
        with kpi1: st.metric(f"{ph_color} Prom. pH (30d)", ph_avg)
        with kpi2: st.metric(f"{tur_color} Prom. Turbidez (30d)", tur_avg)
        with kpi3: st.metric(f"{clo_color} Prom. Cloro (30d)", clo_avg)

        locacion_seleccionada = st.selectbox("Locación", sorted(df["Locación"].unique()))
        df_filtrado = df[df["Locación"] == locacion_seleccionada]

        for param in ["pH", "Turbidez (NTU)", "Cloro Residual (mg/L)"]:
            fig = px.line(df_filtrado, x="Fecha", y=param, markers=True, title=f"{param} en {locacion_seleccionada}")
            if param == "pH":
                fig.add_hline(y=6.5, line_dash="dot", line_color="green", annotation_text="pH mínimo")
                fig.add_hline(y=8.5, line_dash="dot", line_color="green", annotation_text="pH máximo")
            elif param == "Turbidez (NTU)":
                fig.add_hline(y=5, line_dash="dot", line_color="orange", annotation_text="Turbidez máx.")
            elif param == "Cloro Residual (mg/L)":
                fig.add_hline(y=0.5, line_dash="dot", line_color="blue", annotation_text="Cloro mín.")
                fig.add_hline(y=1.5, line_dash="dot", line_color="blue", annotation_text="Cloro máx.")
            st.plotly_chart(fig, use_container_width=True)

elif menu == "📄 Historial":
    st.title("📄 Historial de muestras registradas")
    df = st.session_state.data.copy()
    if df.empty:
        st.info("No hay registros.")
    else:
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

        def mostrar_foto(nombre):
            if isinstance(nombre, str) and nombre.strip():
                path = os.path.join(FOTOS_DIR, nombre)
                if os.path.exists(path):
                    st.image(path, width=100)
                else:
                    st.text("📁 Foto no disponible")
            else:
                st.text("📎 Sin foto adjunta")

        for i, row in df.iterrows():
            with st.expander(f"📌 {row['Fecha']} - {row['Hora']} - {row['Locación']}"):
                st.write(f"👷 **Técnico:** {row['Técnico']}")
                st.write(f"pH: {row['pH']} | Turbidez: {row['Turbidez (NTU)']} | Cloro: {row['Cloro Residual (mg/L)']}")
                st.write(f"📝 **Observaciones:** {row['Observaciones']}")
                mostrar_foto(row['Foto'])

                if st.button(f"🗑️ Eliminar registro {i}"):
                    st.session_state.data.drop(index=i, inplace=True)
                    st.session_state.data.reset_index(drop=True, inplace=True)
                    guardar_datos(st.session_state.data)
                    st.experimental_rerun()

elif menu == "📤 Exportar PDF":
    st.title("📤 Generador de reportes PDF")
    df = st.session_state.data.copy()

    if st.button("📥 Generar PDF del resumen actual"):
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

    if st.button("🗑️ Eliminar todo el historial"):
        st.session_state.data = pd.DataFrame(columns=["Fecha", "Hora", "Técnico", "Locación", "pH", "Turbidez (NTU)",
                                                      "Cloro Residual (mg/L)", "Observaciones", "Foto"])
        guardar_datos(st.session_state.data)
        st.success("Historial eliminado correctamente.")
