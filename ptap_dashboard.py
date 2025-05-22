import streamlit as st
import pandas as pd
import gspread
import plotly.graph_objects as go
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
    df = leer_datos() if 'leer_datos' in globals() else st.session_state.data.copy()
    if not df.empty:
        locacion_seleccionada = st.selectbox("Locación", sorted(df["Locación"].dropna().unique()))
        df_filtrado = df[df["Locación"] == locacion_seleccionada]
        ultimos_30 = df_filtrado[df_filtrado["Fecha"] >= datetime.now() - pd.Timedelta(days=30)].sort_values("Fecha")

        # --- Funciones de semáforo para KPIs individuales ---
        def color_ph(val):
            if 6.5 <= val <= 8.5:
                return "#2ecc40"  # verde
            elif 6.0 <= val < 6.5 or 8.5 < val <= 9.0:
                return "#ffdc00"  # amarillo
            else:
                return "#ff4136"  # rojo

        def color_turbidez(val):
            if val < 5:
                return "#2ecc40"
            elif 5 <= val < 10:
                return "#ffdc00"
            else:
                return "#ff4136"

        def color_cloro(val):
            if 0.5 <= val <= 1.5:
                return "#2ecc40"  # verde
            elif (0.2 <= val < 0.5) or (1.5 < val <= 2.0):
                return "#ffdc00"  # amarillo
            else:
                return "#ff4136"  # rojo

        if not ultimos_30.empty:
            st.subheader("Valores individuales últimos 30 días")
            # Crea tabla auxiliar con colores
            tabla_aux = ultimos_30[["Fecha", "pH", "Turbidez (NTU)", "Cloro Residual (mg/L)"]].copy()
            tabla_aux["pH Color"] = tabla_aux["pH"].apply(color_ph)
            tabla_aux["Turbidez Color"] = tabla_aux["Turbidez (NTU)"].apply(color_turbidez)
            tabla_aux["Cloro Color"] = tabla_aux["Cloro Residual (mg/L)"].apply(color_cloro)

            def style_row(row):
                return [
                    '',  # Fecha
                    f'background-color: {row["pH Color"]}; color: white;',
                    f'background-color: {row["Turbidez Color"]}; color: white;',
                    f'background-color: {row["Cloro Color"]}; color: white;',
                ]

            # Aplica el styling solo sobre las columnas visibles
            tabla_final = tabla_aux[["Fecha", "pH", "Turbidez (NTU)", "Cloro Residual (mg/L)"]].copy()
            tabla_final.columns = ["Fecha", "pH", "Turbidez (NTU)", "Cloro Residual (mg/L)"]  # nombres exactos

            st.dataframe(
                tabla_final.style.apply(style_row, axis=1)
            )

            # --- Gráficos (idéntico a antes) ---
            st.subheader("Histórico de pH (con rangos)")
            fig_ph = go.Figure()
            fig_ph.add_trace(go.Scatter(x=ultimos_30["Fecha"], y=ultimos_30["pH"], mode="lines+markers", name="pH", line=dict(color="blue")))
            fig_ph.add_hrect(y0=6.5, y1=8.5, fillcolor="green", opacity=0.15, line_width=0, annotation_text="Rango óptimo", annotation_position="top left")
            fig_ph.add_hrect(y0=6.0, y1=9.0, fillcolor="yellow", opacity=0.12, line_width=0)
            fig_ph.add_hrect(y0=0, y1=6.0, fillcolor="red", opacity=0.07, line_width=0)
            fig_ph.add_hrect(y0=9.0, y1=14.0, fillcolor="red", opacity=0.07, line_width=0)
            fig_ph.update_layout(yaxis_title="pH", xaxis_title="Fecha", height=300)
            st.plotly_chart(fig_ph, use_container_width=True)

            st.subheader("Histórico de Turbidez (NTU) (con rango)")
            fig_turb = go.Figure()
            fig_turb.add_trace(go.Scatter(x=ultimos_30["Fecha"], y=ultimos_30["Turbidez (NTU)"], mode="lines+markers", name="Turbidez", line=dict(color="orange")))
            fig_turb.add_hrect(y0=0, y1=5, fillcolor="green", opacity=0.15, line_width=0, annotation_text="Rango óptimo (<5)", annotation_position="top left")
            fig_turb.add_hrect(y0=5, y1=10, fillcolor="yellow", opacity=0.13, line_width=0)
            fig_turb.add_hrect(y0=10, y1=100, fillcolor="red", opacity=0.09, line_width=0)
            fig_turb.update_layout(yaxis_title="Turbidez (NTU)", xaxis_title="Fecha", height=300)
            st.plotly_chart(fig_turb, use_container_width=True)

            st.subheader("Histórico de Cloro Residual (mg/L) (con rango)")
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
