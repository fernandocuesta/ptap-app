
import streamlit as st
import pandas as pd
from datetime import datetime
import plotly.express as px
import os
import pytz

st.set_page_config(page_title="Control Logístico PTAP", page_icon="🚛", layout="wide")

DATA_FILE = "ptap_data.csv"
FOTOS_DIR = "fotos"
os.makedirs(FOTOS_DIR, exist_ok=True)

def cargar_datos():
    try:
        return pd.read_csv(DATA_FILE)
    except FileNotFoundError:
        return pd.DataFrame(columns=["Fecha", "Hora", "Técnico", "Locación", "pH", "Turbidez (NTU)", "Cloro Residual (mg/L)", "Observaciones", "Foto"])

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

    lima_tz = pytz.timezone("America/Lima")
    now = datetime.now(lima_tz)

    col1, col2 = st.columns(2)
    with col1:
        fecha = st.date_input("📅 Fecha", value=now.date(), max_value=now.date())
        hora = st.time_input("⏰ Hora", value=now.time())
        tecnico = st.selectbox("👷 Técnico", tecnicos)
        locacion = st.selectbox("📍 Locación de muestreo", locaciones)
    with col2:
        ph = st.number_input("pH", min_value=0.0, max_value=14.0, step=0.1)
        turbidez = st.number_input("Turbidez (NTU)", min_value=0.0, step=0.1)
        cloro = st.number_input("Cloro Residual (mg/L)", min_value=0.0, step=0.1)

    observaciones = st.text_area("📝 Observaciones")
    foto = st.file_uploader("📷 Adjuntar foto (opcional)", type=["jpg", "jpeg", "png"])

    alerta = []
    if ph < 6.5 or ph > 8.5:
        alerta.append("⚠️ pH fuera de rango ideal (6.5 - 8.5)")
    if turbidez > 5:
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

elif menu == "📊 KPIs y Análisis":
    st.title("📊 KPIs y Análisis de datos por locación")
    df = st.session_state.data.copy()
    if not df.empty:
        df["Fecha"] = pd.to_datetime(df["Fecha"])

        locacion_seleccionada = st.selectbox("Locación", sorted(df["Locación"].unique()))
        df_filtrado = df[df["Locación"] == locacion_seleccionada]
        ultimos_30 = df_filtrado[df_filtrado["Fecha"] >= datetime.now() - pd.Timedelta(days=30)]

        ph_avg = round(ultimos_30["pH"].mean(), 2)
        tur_avg = round(ultimos_30["Turbidez (NTU)"].mean(), 2)
        clo_avg = round(ultimos_30["Cloro Residual (mg/L)"].mean(), 2)

        ph_color = "🟢" if 6.5 <= ph_avg <= 8.5 else "🔴"
        tur_color = "🟢" if tur_avg <= 5 else "🔴"
        clo_color = "🟢" if 0.5 <= clo_avg <= 1.5 else "🔴"

        k1, k2, k3 = st.columns(3)
        with k1: st.metric(f"{ph_color} Prom. pH", ph_avg)
        with k2: st.metric(f"{tur_color} Prom. Turbidez", tur_avg)
        with k3: st.metric(f"{clo_color} Prom. Cloro", clo_avg)

        for param in ["pH", "Turbidez (NTU)", "Cloro Residual (mg/L)"]:
            fig = px.line(df_filtrado, x="Fecha", y=param, markers=True, title=f"{param} en {locacion_seleccionada}")
            st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("No hay datos para mostrar.")

elif menu == "📄 Historial":
    st.title("📄 Historial de muestras registradas")
    df = st.session_state.data.copy()
    if not df.empty:
        df["Fecha"] = pd.to_datetime(df["Fecha"])
        col1, col2 = st.columns(2)
        with col1:
            fecha_ini = st.date_input("Desde", value=df["Fecha"].min().date())
        with col2:
            fecha_fin = st.date_input("Hasta", value=df["Fecha"].max().date())

        df_filtrado = df[(df["Fecha"] >= pd.to_datetime(fecha_ini)) & (df["Fecha"] <= pd.to_datetime(fecha_fin))]
        for i, row in df_filtrado.iterrows():
            with st.expander(f"📌 {row['Fecha'].date()} - {row['Hora']} - {row['Locación']}"):
                st.write(f"👷 **Técnico:** {row['Técnico']}")
                st.write(f"pH: {row['pH']} | Turbidez: {row['Turbidez (NTU)']} | Cloro: {row['Cloro Residual (mg/L)']}")
                st.write(f"📝 **Observaciones:** {row['Observaciones']}")
                if row['Foto']:
                    path = os.path.join(FOTOS_DIR, row['Foto'])
                    if os.path.exists(path):
                        st.image(path, width=100)
                if st.button(f"🗑️ Eliminar registro {i}"):
                    st.session_state.data.drop(index=i, inplace=True)
                    st.session_state.data.reset_index(drop=True, inplace=True)
                    guardar_datos(st.session_state.data)
                    st.rerun()
    else:
        st.info("No hay datos en el historial.")

elif menu == "📥 Exportar":
    st.title("📥 Exportar registros en Excel")
    df = st.session_state.data.copy()
    if not df.empty:
        st.download_button("⬇️ Descargar Excel", data=df.to_csv(index=False).encode("utf-8"), file_name="ptap_registros.xlsx", mime="text/csv")
    else:
        st.info("No hay datos para exportar.")
