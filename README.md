# 🔬 PTAP — Sistema de Control de Calidad de Agua Potable

**PetroTal Corp. · Planta de Tratamiento de Agua Potable**

Sistema de monitoreo en tiempo real para parámetros de calidad de agua (pH, Turbidez, Cloro Residual) con dashboard ejecutivo, alertas automáticas y reportes.

---

## Cambios respecto a la versión anterior

### Arquitectura y código
- Código modular separado en funciones claras (datos, análisis, UI, gráficos, páginas)
- Usuarios con estructura de diccionario que incluye rol (`admin` / `operador`)
- Constantes centralizadas para límites normativos (`LIMITES`)
- Funciones de clasificación reutilizables (`clasificar_valor`, `calcular_cumplimiento`)

### Dashboard ejecutivo (nuevo)
- **4 KPIs principales**: muestras registradas, locaciones activas, cumplimiento de cloro, alertas críticas
- **Sistema de alertas automáticas** (últimas 48h) con clasificación visual
- **Heatmap de cumplimiento diario** por locación (colores verde → rojo)
- **Gráfico de tendencias comparativas** entre locaciones con media móvil
- Selector de período (7, 15, 30 días o histórico completo)

### Interfaz profesional
- CSS personalizado con paleta corporativa (azul oscuro, teal, grises)
- Tarjetas KPI con bordes de color según estado (verde/amarillo/rojo)
- Badges de estado inline (`Óptimo`, `Alerta`, `Crítico`)
- Sidebar oscuro con información de usuario y hora en tiempo real
- Tipografía DM Sans + JetBrains Mono para valores numéricos
- Branding Streamlit oculto (menú hamburguesa, footer)

### Gráficos mejorados
- Template unificado con colores consistentes por parámetro
- Bandas de rango óptimo/alerta/crítico con transparencias
- Líneas de límite punteadas
- Tooltips con formato de fecha legible
- Hover labels con fondo oscuro profesional

### Formulario de ingreso mejorado
- Vista previa de clasificación antes de guardar (badges de estado)
- Formato decimal configurable (`.2f` para cloro y turbidez)
- Confirmación visual con animación (`st.balloons()`)
- Caption informativo para locaciones solo-cloro

### Historial mejorado
- Filtro por operador (nuevo)
- Opción "Todas" las locaciones
- Contador de registros encontrados
- Tabla con altura fija y scroll

### Exportación mejorada
- **Excel multi-hoja** (.xlsx): registros + resumen por locación + alertas
- Descarga CSV para análisis externo
- Nombres de archivo con fecha automática

---

## Estructura de archivos

```
ptap-app/
├── .devcontainer/         # Configuración de dev container
├── .streamlit/
│   └── secrets.toml       # Credenciales de Google (NO subir a GitHub)
├── ptap_dashboard.py      # Aplicación principal
├── ptap_data.csv          # Respaldo de datos (opcional)
├── requirements.txt       # Dependencias Python
└── README.md              # Este archivo
```

---

## Configuración

### 1. Credenciales de Google Sheets

En Streamlit Cloud, configura los secrets con el JSON de tu service account:

```toml
# .streamlit/secrets.toml (local) o Streamlit Cloud > Settings > Secrets
[gcp_service_account]
type = "service_account"
project_id = "tu-proyecto"
private_key_id = "..."
private_key = "-----BEGIN PRIVATE KEY-----\n...\n-----END PRIVATE KEY-----\n"
client_email = "tu-cuenta@tu-proyecto.iam.gserviceaccount.com"
client_id = "..."
auth_uri = "https://accounts.google.com/o/oauth2/auth"
token_uri = "https://oauth2.googleapis.com/token"
auth_provider_x509_cert_url = "https://www.googleapis.com/oauth2/v1/certs"
client_x509_cert_url = "..."
```

### 2. Instalar dependencias

```bash
pip install -r requirements.txt
```

### 3. Ejecutar localmente

```bash
streamlit run ptap_dashboard.py
```

---

## Despliegue en Streamlit Cloud

1. Sube los archivos a tu repositorio GitHub (`fernandocuesta/ptap-app`)
2. En [share.streamlit.io](https://share.streamlit.io), conecta el repositorio
3. En **Settings > Secrets**, pega el contenido de tu `secrets.toml`
4. Deploy automático

---

## Rangos normativos configurados

| Parámetro | Óptimo | Alerta | Referencia |
|-----------|--------|--------|------------|
| pH | 6.5 – 8.5 | 6.0 – 9.0 | DS N° 031-2010-SA |
| Turbidez | 0 – 5 NTU | 0 – 10 NTU | OMS / DS 031 |
| Cloro Residual | 0.5 – 1.5 mg/L | 0.2 – 2.0 mg/L | DS N° 031-2010-SA |

---

## Mejoras futuras sugeridas

- **Base de datos**: Migrar de Google Sheets a PostgreSQL (Supabase) para mayor velocidad con datasets grandes (+5000 registros)
- **Autenticación**: Implementar hash de contraseñas (bcrypt) y tokens JWT
- **Notificaciones**: Alertas por email/WhatsApp cuando un parámetro sale de rango
- **Reportes PDF**: Generación automática de reportes mensuales con gráficos embebidos
- **Roles granulares**: Permisos por locación para cada operador
- **API REST**: Endpoint para integración con otros sistemas de la planta
