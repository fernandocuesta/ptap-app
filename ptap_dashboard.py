"""
╔══════════════════════════════════════════════════════════════════╗
║  PTAP - Sistema de Control de Calidad de Agua Potable          ║
║  PetroTal Corp.                                                ║
║  Versión 2.0 - Dashboard Profesional                           ║
╚══════════════════════════════════════════════════════════════════╝
"""
import streamlit as st
import pandas as pd
import numpy as np
import gspread
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
from google.oauth2.service_account import Credentials
from datetime import datetime, timedelta
import pytz
from io import BytesIO

# ═══════════════════════════════════════════════════════════════
# CONFIGURACIÓN GLOBAL
# ═══════════════════════════════════════════════════════════════
LOGO_URL = "https://hcmpinturas.com/wp-content/uploads/2023/10/PetroTal-logo-star.png"
TIMEZONE = pytz.timezone("America/Lima")
SHEET_URL = "https://docs.google.com/spreadsheets/d/19AZGamcT9AIkV6aR4Xs7CCObgBo8xKFlv4eXfrAUJuU/edit?usp=sharing"
SCOPE = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive"
]

# --- Parámetros normativos (DS N° 031-2010-SA / OMS) ---
LIMITES = {
    "pH":                     {"optimo": (6.5, 8.5), "alerta": (6.0, 9.0), "unidad": ""},
    "Turbidez (NTU)":         {"optimo": (0, 5),     "alerta": (0, 10),    "unidad": "NTU"},
    "Cloro Residual (mg/L)":  {"optimo": (0.5, 1.5), "alerta": (0.2, 2.0), "unidad": "mg/L"},
}

# --- Usuarios y roles ---
USUARIOS = {
    "admin":    {"password": "1234",          "nombre": "Administrador",         "rol": "admin"},
    "jperez":   {"password": "jperez2025",    "nombre": "Jorge Perez Padilla",   "rol": "operador"},
    "lsangama": {"password": "lsangama2025",  "nombre": "Luis Sangama Ricopa",   "rol": "operador"},
    "jsoto":    {"password": "jsoto2025",     "nombre": "Jose Soto Dávila",      "rol": "operador"},
}

# --- Locaciones ---
LOCACIONES = [
    "Planta de Agua Potable", "Cocina", "Equipo Purificador - PTAP",
    "Dispensador - Comedor 2", "Dispensador - Oficina Gerencia",
    "Dispensador - HSE 01", "Dispensador - HSE 02", "Dispensador - Producción"
]
# Locaciones que solo miden cloro residual
SOLO_CLORO = {loc.strip().lower() for loc in [
    "Equipo Purificador - PTAP", "Dispensador - Comedor 2",
    "Dispensador - Oficina Gerencia", "Dispensador - HSE 01",
    "Dispensador - HSE 02", "Dispensador - Producción"
]}

# ═══════════════════════════════════════════════════════════════
# ESTILOS CSS PROFESIONALES
# ═══════════════════════════════════════════════════════════════
CUSTOM_CSS = """
<style>
    /* --- Tipografía y fondo general --- */
    @import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;700&family=JetBrains+Mono:wght@400;500&display=swap');

    .stApp {
        font-family: 'DM Sans', sans-serif;
    }

    /* --- Header bar --- */
    .ptap-header {
        background: linear-gradient(135deg, #0c1829 0%, #1a3a5c 50%, #0d7377 100%);
        padding: 1.5rem 2rem;
        border-radius: 12px;
        margin-bottom: 1.5rem;
        display: flex;
        align-items: center;
        justify-content: space-between;
        box-shadow: 0 4px 24px rgba(0,0,0,0.15);
    }
    .ptap-header h1 {
        color: #ffffff;
        font-size: 1.6rem;
        font-weight: 700;
        margin: 0;
        letter-spacing: -0.02em;
    }
    .ptap-header p {
        color: #94d2bd;
        font-size: 0.85rem;
        margin: 0.2rem 0 0 0;
    }

    /* --- Tarjetas KPI --- */
    .kpi-card {
        background: #ffffff;
        border-radius: 12px;
        padding: 1.2rem 1.4rem;
        border-left: 4px solid #0d7377;
        box-shadow: 0 2px 12px rgba(0,0,0,0.06);
        transition: transform 0.2s, box-shadow 0.2s;
    }
    .kpi-card:hover {
        transform: translateY(-2px);
        box-shadow: 0 6px 20px rgba(0,0,0,0.1);
    }
    .kpi-card .kpi-label {
        font-size: 0.78rem;
        font-weight: 500;
        color: #64748b;
        text-transform: uppercase;
        letter-spacing: 0.06em;
        margin-bottom: 0.3rem;
    }
    .kpi-card .kpi-value {
        font-family: 'JetBrains Mono', monospace;
        font-size: 1.8rem;
        font-weight: 700;
        color: #0f172a;
        line-height: 1.1;
    }
    .kpi-card .kpi-delta {
        font-size: 0.8rem;
        margin-top: 0.25rem;
    }
    .kpi-card .kpi-delta.ok    { color: #059669; }
    .kpi-card .kpi-delta.warn  { color: #d97706; }
    .kpi-card .kpi-delta.crit  { color: #dc2626; }

    /* --- Variantes de borde de KPI --- */
    .kpi-green  { border-left-color: #059669; }
    .kpi-yellow { border-left-color: #d97706; }
    .kpi-red    { border-left-color: #dc2626; }
    .kpi-blue   { border-left-color: #2563eb; }

    /* --- Tarjeta de alerta --- */
    .alert-card {
        background: linear-gradient(135deg, #fef2f2 0%, #fff7ed 100%);
        border: 1px solid #fecaca;
        border-radius: 10px;
        padding: 1rem 1.2rem;
        margin-bottom: 0.5rem;
    }
    .alert-card .alert-title {
        font-weight: 700;
        color: #dc2626;
        font-size: 0.9rem;
    }
    .alert-card .alert-detail {
        color: #78350f;
        font-size: 0.82rem;
        margin-top: 0.2rem;
    }

    /* --- Sección / separador visual --- */
    .section-divider {
        border: none;
        height: 1px;
        background: linear-gradient(90deg, transparent 0%, #cbd5e1 50%, transparent 100%);
        margin: 1.5rem 0;
    }

    /* --- Badge de estado --- */
    .badge {
        display: inline-block;
        padding: 0.2rem 0.65rem;
        border-radius: 100px;
        font-size: 0.72rem;
        font-weight: 600;
        letter-spacing: 0.03em;
    }
    .badge-ok   { background: #d1fae5; color: #065f46; }
    .badge-warn { background: #fef3c7; color: #92400e; }
    .badge-crit { background: #fee2e2; color: #991b1b; }

    /* --- Sidebar custom --- */
    section[data-testid="stSidebar"] {
        background: linear-gradient(180deg, #0c1829 0%, #132f4c 100%);
    }
    section[data-testid="stSidebar"] .stMarkdown,
    section[data-testid="stSidebar"] .stMarkdown p,
    section[data-testid="stSidebar"] label,
    section[data-testid="stSidebar"] .stRadio label,
    section[data-testid="stSidebar"] .stRadio div,
    section[data-testid="stSidebar"] .stRadio p,
    section[data-testid="stSidebar"] [data-testid="stMarkdownContainer"] p,
    section[data-testid="stSidebar"] span,
    section[data-testid="stSidebar"] p {
        color: #e2e8f0 !important;
    }
    section[data-testid="stSidebar"] hr {
        border-color: rgba(255,255,255,0.1);
    }

    /* --- Tablas estilizadas --- */
    .stDataFrame {
        border-radius: 10px;
        overflow: hidden;
    }

    /* --- Ocultar branding Streamlit --- */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
</style>
"""

# ═══════════════════════════════════════════════════════════════
# FUNCIONES DE DATOS
# ═══════════════════════════════════════════════════════════════
@st.cache_resource(show_spinner=False)
def get_worksheet():
    """Conexión autenticada a Google Sheets."""
    creds = Credentials.from_service_account_info(
        st.secrets["gcp_service_account"], scopes=SCOPE
    )
    gc = gspread.authorize(creds)
    sh = gc.open_by_url(SHEET_URL)
    return sh.sheet1


def leer_datos() -> pd.DataFrame:
    """Lee y procesa todos los registros del Google Sheet."""
    try:
        ws = get_worksheet()
        data = ws.get_all_records()
        df = pd.DataFrame(data)
        if df.empty:
            return df

        # Limpieza de tipos numéricos
        num_cols = ["pH", "Turbidez (NTU)", "Cloro Residual (mg/L)"]
        for col in num_cols:
            if col in df.columns:
                df[col] = (
                    df[col].astype(str)
                    .str.replace(",", ".", regex=False)
                    .replace(["", "None", "nan"], np.nan)
                )
                df[col] = pd.to_numeric(df[col], errors="coerce")

        # Datetime combinado
        if "Fecha" in df.columns and "Hora de Toma" in df.columns:
            df["Fecha_dt"] = pd.to_datetime(df["Fecha"], errors="coerce")
            df["Fecha_Hora"] = pd.to_datetime(
                df["Fecha"].astype(str) + " " + df["Hora de Toma"].astype(str),
                errors="coerce"
            )
        return df
    except Exception as e:
        st.error(f"⚠️ Error al conectar con Google Sheets: {e}")
        return pd.DataFrame()


def guardar_muestra(muestra: list):
    """Agrega una fila al Google Sheet."""
    try:
        ws = get_worksheet()
        ws.append_row(muestra)
        return True
    except Exception as e:
        st.error(f"⚠️ Error guardando: {e}")
        return False


# ═══════════════════════════════════════════════════════════════
# FUNCIONES DE ANÁLISIS
# ═══════════════════════════════════════════════════════════════
def clasificar_valor(valor: float, param: str) -> str:
    """Clasifica un valor como 'ok', 'warn' o 'crit' según límites normativos."""
    if pd.isna(valor):
        return "ok"
    lim = LIMITES.get(param)
    if lim is None:
        return "ok"
    lo_opt, hi_opt = lim["optimo"]
    lo_alr, hi_alr = lim["alerta"]
    if lo_opt <= valor <= hi_opt:
        return "ok"
    elif lo_alr <= valor <= hi_alr:
        return "warn"
    else:
        return "crit"


def calcular_cumplimiento(df: pd.DataFrame, param: str) -> float:
    """Porcentaje de valores dentro del rango óptimo."""
    series = df[param].dropna()
    if series.empty:
        return 100.0
    lim = LIMITES[param]
    lo, hi = lim["optimo"]
    en_rango = ((series >= lo) & (series <= hi)).sum()
    return round(en_rango / len(series) * 100, 1)


def generar_alertas(df: pd.DataFrame) -> list:
    """Genera lista de alertas para las últimas 48 horas."""
    alertas = []
    ahora = datetime.now()
    recientes = df[df["Fecha_Hora"] >= ahora - timedelta(hours=48)].copy()
    if recientes.empty:
        return alertas

    for _, row in recientes.iterrows():
        loc = row.get("Locación", "")
        fecha_hora = row.get("Fecha_Hora", "")
        loc_norm = str(loc).strip().lower()

        params_a_revisar = ["Cloro Residual (mg/L)"]
        if loc_norm not in SOLO_CLORO:
            params_a_revisar = ["pH", "Turbidez (NTU)", "Cloro Residual (mg/L)"]

        for param in params_a_revisar:
            val = row.get(param)
            estado = clasificar_valor(val, param)
            if estado in ("warn", "crit"):
                emoji = "🟡" if estado == "warn" else "🔴"
                lim = LIMITES[param]
                lo, hi = lim["optimo"]
                alertas.append({
                    "emoji": emoji,
                    "estado": estado,
                    "locacion": loc,
                    "parametro": param,
                    "valor": val,
                    "rango_optimo": f"{lo} – {hi}",
                    "fecha_hora": fecha_hora,
                })
    return alertas


def resumen_ejecutivo(df: pd.DataFrame, dias: int = 7) -> dict:
    """Calcula KPIs globales para el dashboard ejecutivo."""
    ahora = datetime.now()
    reciente = df[df["Fecha_Hora"] >= ahora - timedelta(days=dias)].copy()
    total_muestras = len(reciente)
    locaciones_activas = reciente["Locación"].nunique()

    # Cumplimiento por parámetro
    cumplimiento = {}
    for param in ["pH", "Turbidez (NTU)", "Cloro Residual (mg/L)"]:
        series = reciente[param].dropna()
        if not series.empty:
            lo, hi = LIMITES[param]["optimo"]
            en_rango = ((series >= lo) & (series <= hi)).sum()
            cumplimiento[param] = round(en_rango / len(series) * 100, 1)
        else:
            cumplimiento[param] = None

    # Alertas críticas
    alertas = generar_alertas(reciente)
    criticas = [a for a in alertas if a["estado"] == "crit"]

    return {
        "total_muestras": total_muestras,
        "locaciones_activas": locaciones_activas,
        "cumplimiento": cumplimiento,
        "alertas_criticas": len(criticas),
        "alertas_total": len(alertas),
        "alertas_detalle": alertas[:10],  # últimas 10
    }


# ═══════════════════════════════════════════════════════════════
# COMPONENTES UI
# ═══════════════════════════════════════════════════════════════
def render_header():
    """Header principal con branding."""
    st.markdown(CUSTOM_CSS, unsafe_allow_html=True)
    st.markdown("""
    <div class="ptap-header">
        <div>
            <h1>🔬 Control de Calidad — Agua Potable</h1>
            <p>Sistema de Monitoreo PTAP · PetroTal Corp.</p>
        </div>
    </div>
    """, unsafe_allow_html=True)


def render_kpi_card(label: str, value: str, delta: str = "", estado: str = "ok", variante: str = ""):
    """Renderiza una tarjeta KPI."""
    color_class = {"ok": "kpi-green", "warn": "kpi-yellow", "crit": "kpi-red"}.get(estado, "kpi-blue")
    if variante:
        color_class = variante
    delta_class = {"ok": "ok", "warn": "warn", "crit": "crit"}.get(estado, "ok")
    delta_html = f'<div class="kpi-delta {delta_class}">{delta}</div>' if delta else ""
    st.markdown(f"""
    <div class="kpi-card {color_class}">
        <div class="kpi-label">{label}</div>
        <div class="kpi-value">{value}</div>
        {delta_html}
    </div>
    """, unsafe_allow_html=True)


def render_badge(estado: str, texto: str = "") -> str:
    """Retorna HTML de un badge de estado."""
    cls = {"ok": "badge-ok", "warn": "badge-warn", "crit": "badge-crit"}.get(estado, "badge-ok")
    label = texto or {"ok": "Óptimo", "warn": "Alerta", "crit": "Crítico"}.get(estado, "—")
    return f'<span class="badge {cls}">{label}</span>'


# ═══════════════════════════════════════════════════════════════
# GRÁFICOS
# ═══════════════════════════════════════════════════════════════
CHART_TEMPLATE = dict(
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(248,250,252,1)",
    font=dict(family="DM Sans, sans-serif", color="#334155"),
    margin=dict(l=50, r=20, t=40, b=50),
    hoverlabel=dict(bgcolor="#1e293b", font_color="#f8fafc", font_size=12),
    xaxis=dict(gridcolor="rgba(203,213,225,0.4)", showgrid=True),
    yaxis=dict(gridcolor="rgba(203,213,225,0.4)", showgrid=True),
)

PARAM_COLORS = {
    "pH":                     "#2563eb",
    "Turbidez (NTU)":         "#d97706",
    "Cloro Residual (mg/L)":  "#0d7377",
}

RANGE_COLORS = {
    "ok":   dict(fillcolor="rgba(5,150,105,0.10)", line_width=0),
    "warn": dict(fillcolor="rgba(217,119,6,0.08)", line_width=0),
    "crit": dict(fillcolor="rgba(220,38,38,0.06)", line_width=0),
}


def crear_grafico_parametro(df: pd.DataFrame, param: str, height: int = 320) -> go.Figure:
    """Crea un gráfico de línea profesional para un parámetro."""
    fig = go.Figure()
    color = PARAM_COLORS.get(param, "#6366f1")
    lim = LIMITES[param]

    # Línea principal
    fig.add_trace(go.Scatter(
        x=df["Fecha_Hora"], y=df[param],
        mode="lines+markers",
        name=param,
        line=dict(color=color, width=2.5),
        marker=dict(size=5, color=color, line=dict(width=1, color="#ffffff")),
        hovertemplate=f"<b>{param}</b><br>Valor: %{{y:.2f}}<br>%{{x|%d %b %Y %H:%M}}<extra></extra>"
    ))

    # Bandas de rango
    lo_opt, hi_opt = lim["optimo"]
    lo_alr, hi_alr = lim["alerta"]

    fig.add_hrect(y0=lo_opt, y1=hi_opt, annotation_text="Rango óptimo",
                  annotation_position="top left", annotation_font_size=10,
                  annotation_font_color="rgba(5,150,105,0.7)",
                  **RANGE_COLORS["ok"])

    # Alertas amarillas
    if param == "Cloro Residual (mg/L)":
        fig.add_hrect(y0=lo_alr, y1=lo_opt, **RANGE_COLORS["warn"])
        fig.add_hrect(y0=hi_opt, y1=hi_alr, **RANGE_COLORS["warn"])
        fig.add_hrect(y0=0, y1=lo_alr, **RANGE_COLORS["crit"])
        fig.add_hrect(y0=hi_alr, y1=hi_alr + 1, **RANGE_COLORS["crit"])
    elif param == "pH":
        fig.add_hrect(y0=lo_alr, y1=lo_opt, **RANGE_COLORS["warn"])
        fig.add_hrect(y0=hi_opt, y1=hi_alr, **RANGE_COLORS["warn"])
        fig.add_hrect(y0=0, y1=lo_alr, **RANGE_COLORS["crit"])
        fig.add_hrect(y0=hi_alr, y1=14, **RANGE_COLORS["crit"])
    elif param == "Turbidez (NTU)":
        fig.add_hrect(y0=5, y1=10, **RANGE_COLORS["warn"])
        fig.add_hrect(y0=10, y1=15, **RANGE_COLORS["crit"])

    # Líneas de límite
    fig.add_hline(y=lo_opt, line=dict(color="rgba(5,150,105,0.3)", width=1, dash="dot"))
    fig.add_hline(y=hi_opt, line=dict(color="rgba(5,150,105,0.3)", width=1, dash="dot"))

    fig.update_layout(
        **CHART_TEMPLATE,
        height=height,
        yaxis_title=param,
        xaxis_title="",
        showlegend=False,
    )
    return fig


def crear_grafico_tendencia_global(df: pd.DataFrame, param: str) -> go.Figure:
    """Gráfico de tendencia con media móvil por locación."""
    fig = go.Figure()
    locaciones = df["Locación"].unique()
    colores = px.colors.qualitative.Set2

    for i, loc in enumerate(sorted(locaciones)):
        sub = df[df["Locación"] == loc].sort_values("Fecha_Hora")
        if sub[param].dropna().empty:
            continue
        fig.add_trace(go.Scatter(
            x=sub["Fecha_Hora"], y=sub[param].rolling(5, min_periods=1).mean(),
            mode="lines", name=loc,
            line=dict(color=colores[i % len(colores)], width=2),
            hovertemplate=f"<b>{loc}</b><br>{param}: %{{y:.2f}}<extra></extra>"
        ))

    lo, hi = LIMITES[param]["optimo"]
    fig.add_hrect(y0=lo, y1=hi, **RANGE_COLORS["ok"])
    fig.update_layout(
        **CHART_TEMPLATE,
        height=350,
        yaxis_title=param,
        legend=dict(orientation="h", yanchor="bottom", y=-0.35, xanchor="center", x=0.5, font_size=11),
    )
    return fig


def crear_heatmap_cumplimiento(df: pd.DataFrame, dias: int = 30) -> go.Figure:
    """Heatmap de cumplimiento diario por locación."""
    ahora = datetime.now()
    reciente = df[df["Fecha_Hora"] >= ahora - timedelta(days=dias)].copy()
    if reciente.empty:
        return go.Figure()

    reciente["Dia"] = reciente["Fecha_dt"].dt.strftime("%Y-%m-%d")
    params = ["Cloro Residual (mg/L)"]  # cloro aplica a todas

    resultados = []
    for loc in sorted(reciente["Locación"].unique()):
        sub = reciente[reciente["Locación"] == loc]
        for dia in sorted(sub["Dia"].unique()):
            dia_data = sub[sub["Dia"] == dia]
            cumpl_vals = []
            for p in params:
                s = dia_data[p].dropna()
                if not s.empty:
                    lo, hi = LIMITES[p]["optimo"]
                    cumpl_vals.append(((s >= lo) & (s <= hi)).mean() * 100)
            if cumpl_vals:
                resultados.append({"Locación": loc, "Día": dia, "Cumplimiento": np.mean(cumpl_vals)})

    if not resultados:
        return go.Figure()

    df_heat = pd.DataFrame(resultados)
    pivot = df_heat.pivot_table(index="Locación", columns="Día", values="Cumplimiento", aggfunc="mean")

    fig = go.Figure(data=go.Heatmap(
        z=pivot.values,
        x=pivot.columns,
        y=pivot.index,
        colorscale=[
            [0, "#dc2626"], [0.5, "#fbbf24"], [0.75, "#34d399"], [1, "#059669"]
        ],
        zmin=0, zmax=100,
        hovertemplate="<b>%{y}</b><br>%{x}<br>Cumplimiento: %{z:.0f}%<extra></extra>",
        colorbar=dict(title="% Cumpl.", ticksuffix="%", len=0.6),
    ))
    chart_cfg = dict(CHART_TEMPLATE)
    chart_cfg.pop("xaxis", None)
    chart_cfg.pop("yaxis", None)
    fig.update_layout(
        **chart_cfg,
        height=max(300, len(pivot) * 45 + 100),
        yaxis=dict(gridcolor="rgba(203,213,225,0.4)", showgrid=True, autorange="reversed"),
        xaxis=dict(gridcolor="rgba(203,213,225,0.4)", showgrid=True, tickangle=-45, tickfont_size=10),
    )
    return fig


# ═══════════════════════════════════════════════════════════════
# GENERACIÓN DE REPORTES
# ═══════════════════════════════════════════════════════════════
def generar_reporte_excel(df: pd.DataFrame) -> BytesIO:
    """Genera reporte Excel con múltiples hojas."""
    output = BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        # Hoja 1: Datos crudos
        df_export = df.drop(columns=["Fecha_dt", "Fecha_Hora"], errors="ignore")
        df_export.to_excel(writer, sheet_name="Registros", index=False)

        # Hoja 2: Resumen por locación
        resumen_rows = []
        for loc in df["Locación"].unique():
            sub = df[df["Locación"] == loc]
            row = {"Locación": loc, "Total Muestras": len(sub)}
            for param in ["pH", "Turbidez (NTU)", "Cloro Residual (mg/L)"]:
                s = sub[param].dropna()
                if not s.empty:
                    row[f"{param} - Promedio"] = round(s.mean(), 3)
                    row[f"{param} - Mín"] = round(s.min(), 3)
                    row[f"{param} - Máx"] = round(s.max(), 3)
                    lo, hi = LIMITES[param]["optimo"]
                    row[f"{param} - % Cumpl."] = round(((s >= lo) & (s <= hi)).mean() * 100, 1)
            resumen_rows.append(row)
        pd.DataFrame(resumen_rows).to_excel(writer, sheet_name="Resumen", index=False)

        # Hoja 3: Alertas
        alertas = generar_alertas(df)
        if alertas:
            pd.DataFrame(alertas).to_excel(writer, sheet_name="Alertas", index=False)

    output.seek(0)
    return output


# ═══════════════════════════════════════════════════════════════
# PÁGINAS / SECCIONES
# ═══════════════════════════════════════════════════════════════
def pagina_dashboard(df: pd.DataFrame):
    """Dashboard ejecutivo con KPIs y gráficos."""
    st.markdown('<hr class="section-divider">', unsafe_allow_html=True)

    # --- Selector de período ---
    col_periodo, col_loc, _ = st.columns([1, 1, 2])
    with col_periodo:
        periodo = st.selectbox("📅 Período", ["Últimos 7 días", "Últimos 15 días", "Últimos 30 días", "Todo"], index=2)
    dias_map = {"Últimos 7 días": 7, "Últimos 15 días": 15, "Últimos 30 días": 30, "Todo": 9999}
    dias = dias_map[periodo]
    ahora = datetime.now()
    df_periodo = df[df["Fecha_Hora"] >= ahora - timedelta(days=dias)].copy() if dias < 9999 else df.copy()

    # --- KPIs ejecutivos ---
    resumen = resumen_ejecutivo(df, dias)
    k1, k2, k3, k4 = st.columns(4)
    with k1:
        render_kpi_card("Muestras Registradas", str(resumen["total_muestras"]),
                        f"Últimos {dias} días" if dias < 9999 else "Total histórico",
                        variante="kpi-blue")
    with k2:
        render_kpi_card("Locaciones Activas", f"{resumen['locaciones_activas']}/{len(LOCACIONES)}",
                        "Con registros en el período", variante="kpi-blue")
    with k3:
        cumpl_cloro = resumen["cumplimiento"].get("Cloro Residual (mg/L)")
        est_cloro = "ok" if cumpl_cloro and cumpl_cloro >= 90 else ("warn" if cumpl_cloro and cumpl_cloro >= 70 else "crit")
        render_kpi_card("Cumpl. Cloro Residual",
                        f"{cumpl_cloro}%" if cumpl_cloro is not None else "—",
                        "Dentro de rango óptimo", est_cloro)
    with k4:
        est_alertas = "ok" if resumen["alertas_criticas"] == 0 else "crit"
        render_kpi_card("Alertas Críticas (48h)",
                        str(resumen["alertas_criticas"]),
                        f"{resumen['alertas_total']} alertas totales", est_alertas)

    st.markdown('<hr class="section-divider">', unsafe_allow_html=True)

    # --- Alertas activas ---
    if resumen["alertas_detalle"]:
        with st.expander(f"⚠️ **Alertas recientes** ({resumen['alertas_total']})", expanded=resumen["alertas_criticas"] > 0):
            for a in resumen["alertas_detalle"]:
                fh = a["fecha_hora"]
                fh_str = fh.strftime("%d/%m %H:%M") if hasattr(fh, "strftime") else str(fh)
                st.markdown(f"""
                <div class="alert-card">
                    <div class="alert-title">{a['emoji']} {a['parametro']} — {a['locacion']}</div>
                    <div class="alert-detail">
                        Valor: <b>{a['valor']:.2f}</b> (Rango óptimo: {a['rango_optimo']}) · {fh_str}
                    </div>
                </div>
                """, unsafe_allow_html=True)

    # --- Gráficos por locación ---
    st.markdown("### 📍 Análisis por Locación")
    with col_loc:
        locaciones_disp = sorted(df_periodo["Locación"].dropna().unique())
        if locaciones_disp:
            loc_sel = st.selectbox("Locación", locaciones_disp, label_visibility="collapsed")
        else:
            st.info("Sin datos para el período.")
            return

    df_loc = df_periodo[df_periodo["Locación"] == loc_sel].sort_values("Fecha_Hora")
    loc_norm = loc_sel.strip().lower()

    if df_loc.empty:
        st.info("No hay registros para esta locación en el período seleccionado.")
        return

    # Determinar parámetros a mostrar
    if loc_norm in SOLO_CLORO:
        params = ["Cloro Residual (mg/L)"]
    else:
        params = ["pH", "Turbidez (NTU)", "Cloro Residual (mg/L)"]

    # KPIs de la locación
    cols_kpi = st.columns(len(params))
    for i, param in enumerate(params):
        s = df_loc[param].dropna()
        with cols_kpi[i]:
            if not s.empty:
                ultimo = s.iloc[-1]
                prom = s.mean()
                estado = clasificar_valor(ultimo, param)
                render_kpi_card(
                    param,
                    f"{ultimo:.2f}",
                    f"Promedio: {prom:.2f} · {render_badge(estado)}",
                    estado
                )
            else:
                render_kpi_card(param, "—", "Sin datos")

    # Gráficos
    for param in params:
        if df_loc[param].dropna().empty:
            continue
        st.plotly_chart(
            crear_grafico_parametro(df_loc, param),
            use_container_width=True,
            key=f"chart_{loc_sel}_{param}"
        )

    # --- Heatmap global ---
    st.markdown('<hr class="section-divider">', unsafe_allow_html=True)
    st.markdown("### 🗓️ Mapa de Cumplimiento Diario (Cloro Residual)")
    fig_heat = crear_heatmap_cumplimiento(df_periodo, dias if dias < 9999 else 60)
    if fig_heat.data:
        st.plotly_chart(fig_heat, use_container_width=True)
    else:
        st.info("Sin datos suficientes para generar el heatmap.")

    # --- Tendencias globales ---
    st.markdown('<hr class="section-divider">', unsafe_allow_html=True)
    st.markdown("### 📈 Tendencia Comparativa por Locación")
    param_tend = st.selectbox("Parámetro", list(LIMITES.keys()), key="tendencia_param")
    fig_tend = crear_grafico_tendencia_global(df_periodo, param_tend)
    if fig_tend.data:
        st.plotly_chart(fig_tend, use_container_width=True)
    else:
        st.info("Sin datos para mostrar.")


def pagina_ingreso():
    """Formulario de ingreso de muestras."""
    st.markdown("### ➕ Registro de Nueva Muestra")
    st.markdown('<hr class="section-divider">', unsafe_allow_html=True)

    now = datetime.now(TIMEZONE)
    usuario = st.session_state.get("usuario", "")
    user_info = USUARIOS.get(usuario, {})
    is_admin = user_info.get("rol") == "admin"

    col1, col2 = st.columns(2)
    with col1:
        if is_admin:
            nombres = [u["nombre"] for u in USUARIOS.values() if u["rol"] == "operador"]
            tecnico = st.selectbox("👷 Operador", nombres)
        else:
            tecnico = user_info.get("nombre", usuario)
            st.markdown(f"**👷 Operador:** `{tecnico}`")

        fecha = st.date_input("📅 Fecha de muestreo", value=now.date(), max_value=now.date())

        if "hora_toma_muestra" not in st.session_state:
            st.session_state["hora_toma_muestra"] = now.time()
        hora_muestra = st.time_input("🕐 Hora de toma", value=st.session_state["hora_toma_muestra"],
                                     key="hora_toma_muestra")

        locacion = st.selectbox("📍 Locación", LOCACIONES)

    with col2:
        loc_norm = locacion.strip().lower()
        ph = turbidez = ""

        st.markdown("**📊 Parámetros medidos**")
        if loc_norm in SOLO_CLORO:
            st.caption("Esta locación solo requiere medición de Cloro Residual.")
            cloro = st.number_input("Cloro Residual (mg/L)", min_value=0.0, step=0.01, format="%.2f")
        else:
            ph = st.number_input("pH", min_value=0.0, max_value=14.0, step=0.1, format="%.1f")
            turbidez = st.number_input("Turbidez (NTU)", min_value=0.0, step=0.01, format="%.2f")
            cloro = st.number_input("Cloro Residual (mg/L)", min_value=0.0, step=0.01, format="%.2f")

    observaciones = st.text_area("📝 Observaciones (opcional)", max_chars=500)
    foto = st.file_uploader("📷 Adjuntar evidencia fotográfica", type=["jpg", "jpeg", "png"])

    # Preview de clasificación antes de guardar
    if loc_norm not in SOLO_CLORO and ph and turbidez:
        st.markdown("**Vista previa de clasificación:**")
        prev_cols = st.columns(3)
        for i, (param, val) in enumerate([("pH", ph), ("Turbidez (NTU)", turbidez), ("Cloro Residual (mg/L)", cloro)]):
            with prev_cols[i]:
                est = clasificar_valor(val, param)
                st.markdown(f"{param}: **{val}** {render_badge(est)}", unsafe_allow_html=True)
    elif loc_norm in SOLO_CLORO and cloro:
        est = clasificar_valor(cloro, "Cloro Residual (mg/L)")
        st.markdown(f"Cloro Residual: **{cloro}** {render_badge(est)}", unsafe_allow_html=True)

    st.markdown("")
    if st.button("💾 Guardar muestra", type="primary", use_container_width=True):
        hora_registro = now.strftime("%H:%M:%S")
        nombre_foto = ""
        if foto and getattr(foto, "name", None):
            nombre_foto = f"{fecha.strftime('%Y%m%d')}_{locacion.replace(' ', '_')}_{foto.name}"

        muestra = [
            fecha.strftime("%Y-%m-%d"),
            hora_muestra.strftime("%H:%M"),
            hora_registro,
            tecnico,
            locacion,
            ph, turbidez, cloro,
            observaciones,
            nombre_foto
        ]
        if guardar_muestra(muestra):
            st.success("✅ Muestra registrada exitosamente.")
            st.balloons()


def pagina_historial(df: pd.DataFrame):
    """Historial filtrable con tabla estilizada."""
    st.markdown("### 📄 Historial de Muestras")
    st.markdown('<hr class="section-divider">', unsafe_allow_html=True)

    if df.empty:
        st.warning("No hay registros.")
        return

    # Filtros
    col_f1, col_f2, col_f3, col_f4 = st.columns(4)
    with col_f1:
        locs_disp = sorted(df["Locación"].dropna().unique())
        loc_hist = st.selectbox("📍 Locación", ["Todas"] + locs_disp)
    with col_f2:
        operadores = sorted(df["Operador"].dropna().unique())
        op_hist = st.selectbox("👷 Operador", ["Todos"] + list(operadores))

    df_f = df.copy()
    if loc_hist != "Todas":
        df_f = df_f[df_f["Locación"] == loc_hist]
    if op_hist != "Todos":
        df_f = df_f[df_f["Operador"] == op_hist]

    min_fecha = df_f["Fecha_dt"].min()
    max_fecha = df_f["Fecha_dt"].max()
    try:
        min_date = min_fecha.date()
        max_date = max_fecha.date()
    except Exception:
        min_date = max_date = datetime.now().date()

    with col_f3:
        fecha_ini = st.date_input("Desde", value=min_date)
    with col_f4:
        fecha_fin = st.date_input("Hasta", value=max_date)

    df_f = df_f[
        (df_f["Fecha_dt"] >= pd.to_datetime(fecha_ini)) &
        (df_f["Fecha_dt"] <= pd.to_datetime(fecha_fin))
    ]

    # Columnas según locación
    loc_norm = loc_hist.strip().lower() if loc_hist != "Todas" else ""
    if loc_norm in SOLO_CLORO:
        cols_show = ["Fecha", "Hora de Toma", "Operador", "Locación", "Cloro Residual (mg/L)", "Observaciones"]
    else:
        cols_show = ["Fecha", "Hora de Toma", "Operador", "Locación", "pH", "Turbidez (NTU)", "Cloro Residual (mg/L)", "Observaciones"]
    cols_show = [c for c in cols_show if c in df_f.columns]

    st.markdown(f"**{len(df_f)} registros encontrados**")
    st.dataframe(
        df_f[cols_show].sort_values("Fecha", ascending=False),
        use_container_width=True,
        height=500,
    )


def pagina_exportar(df: pd.DataFrame):
    """Exportación de datos en múltiples formatos."""
    st.markdown("### 📥 Exportar Datos")
    st.markdown('<hr class="section-divider">', unsafe_allow_html=True)

    if df.empty:
        st.info("No hay datos para exportar.")
        return

    col1, col2 = st.columns(2)
    with col1:
        st.markdown("**📊 Reporte Excel completo**")
        st.caption("Incluye: registros, resumen por locación y alertas.")
        excel_data = generar_reporte_excel(df)
        st.download_button(
            "⬇️ Descargar Excel (.xlsx)",
            data=excel_data,
            file_name=f"PTAP_Reporte_{datetime.now().strftime('%Y%m%d')}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            type="primary"
        )

    with col2:
        st.markdown("**📋 Datos crudos CSV**")
        st.caption("Archivo plano para análisis externo.")
        csv_data = df.drop(columns=["Fecha_dt", "Fecha_Hora"], errors="ignore").to_csv(index=False).encode("utf-8")
        st.download_button(
            "⬇️ Descargar CSV",
            data=csv_data,
            file_name=f"PTAP_Datos_{datetime.now().strftime('%Y%m%d')}.csv",
            mime="text/csv"
        )


# ═══════════════════════════════════════════════════════════════
# SIDEBAR Y NAVEGACIÓN
# ═══════════════════════════════════════════════════════════════
def render_sidebar():
    """Sidebar con navegación y estado de sesión."""
    with st.sidebar:
        st.image(LOGO_URL, width=180)
        st.markdown("---")

        # Menú según autenticación
        if st.session_state.get("logueado"):
            usuario = st.session_state.get("usuario", "")
            nombre = USUARIOS.get(usuario, {}).get("nombre", usuario)
            rol = USUARIOS.get(usuario, {}).get("rol", "")
            st.markdown(f"👤 **{nombre}**")
            st.caption(f"Rol: {rol.capitalize()}")
            st.markdown("---")
            opciones = ["📊 Dashboard", "➕ Ingreso de Muestra", "📄 Historial", "📥 Exportar"]
        else:
            opciones = ["📊 Dashboard"]

        menu = st.radio("Navegación", opciones, label_visibility="collapsed")

        st.markdown("---")
        if st.session_state.get("logueado"):
            if st.button("🚪 Cerrar sesión", use_container_width=True):
                st.session_state["logueado"] = False
                st.session_state["show_login"] = False
                st.session_state["usuario"] = ""
                st.session_state["menu"] = "📊 Dashboard"
                st.rerun()
        else:
            if st.button("🔐 Iniciar sesión", use_container_width=True):
                st.session_state["show_login"] = True
                st.session_state["menu"] = "login"
                st.rerun()

        # Timestamp
        st.markdown("---")
        now = datetime.now(TIMEZONE)
        st.caption(f"🕐 {now.strftime('%d/%m/%Y %H:%M')} (Lima)")

    return menu


def pagina_login():
    """Login profesional."""
    st.markdown(CUSTOM_CSS, unsafe_allow_html=True)
    col_l, col_c, col_r = st.columns([1, 1.5, 1])
    with col_c:
        st.image(LOGO_URL, width=200)
        st.markdown("### 🔐 Acceso al Sistema")
        with st.form("login_form"):
            usuario = st.text_input("Usuario", placeholder="Ingresa tu usuario")
            password = st.text_input("Contraseña", type="password", placeholder="••••••••")
            col_btn1, col_btn2 = st.columns(2)
            with col_btn1:
                login_btn = st.form_submit_button("Ingresar", type="primary", use_container_width=True)
            with col_btn2:
                volver_btn = st.form_submit_button("Volver", use_container_width=True)

        if login_btn:
            if usuario in USUARIOS and password == USUARIOS[usuario]["password"]:
                st.session_state["logueado"] = True
                st.session_state["show_login"] = False
                st.session_state["usuario"] = usuario
                st.session_state["menu"] = "➕ Ingreso de Muestra"
                st.rerun()
            else:
                st.error("❌ Credenciales incorrectas.")
        if volver_btn:
            st.session_state["show_login"] = False
            st.session_state["menu"] = "📊 Dashboard"
            st.rerun()


# ═══════════════════════════════════════════════════════════════
# APP PRINCIPAL
# ═══════════════════════════════════════════════════════════════
def main():
    st.set_page_config(
        page_title="PTAP · Control de Calidad de Agua",
        page_icon="🔬",
        layout="wide",
        initial_sidebar_state="expanded"
    )

    # Inicializar session state
    defaults = {"logueado": False, "show_login": False, "menu": "📊 Dashboard", "usuario": ""}
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v

    # Login intercept
    if st.session_state.get("show_login"):
        pagina_login()
        st.stop()

    # Sidebar
    menu = render_sidebar()

    # Header
    render_header()

    # Cargar datos
    df = leer_datos()

    # Router
    if menu == "📊 Dashboard":
        if df.empty:
            st.info("No hay datos registrados aún.")
        else:
            pagina_dashboard(df)

    elif menu == "➕ Ingreso de Muestra":
        if st.session_state.get("logueado"):
            pagina_ingreso()
        else:
            st.warning("Inicia sesión para registrar muestras.")

    elif menu == "📄 Historial":
        if st.session_state.get("logueado"):
            pagina_historial(df)

    elif menu == "📥 Exportar":
        if st.session_state.get("logueado"):
            pagina_exportar(df)


if __name__ == "__main__":
    main()
