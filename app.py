import streamlit as st
import fitz  # PyMuPDF
import pandas as pd
import re
import io
import zipfile
import unicodedata
from fpdf import FPDF
from datetime import datetime
import plotly.express as px
import numpy as np  # Para dispersión de puntos

# --- CONFIGURACIÓN VISUAL ---
st.set_page_config(page_title="Mapa Logístico V111", layout="wide")
st.title("🗺️ Mapa de Cobertura en Vivo - ITA RADIAN")

# --- ESTILOS ---
st.markdown("""
    <style>
    .stApp { background-color: #f5f7f9; }
    div[data-testid="stExpander"] div[role="button"] p { font-size: 1.1rem; font-weight: bold; }
    </style>
""", unsafe_allow_html=True)

# --- 1. BASE DE DATOS GEOGRÁFICA (COORDENADAS APROXIMADAS) ---
# Definimos el "Corazón" de cada zona en Latitud/Longitud
CENTROIDES_ZONA = {
    "TECNICO 1": {"lat": 10.940, "lon": -74.790, "zona": "Suroriente/Murillo"}, # Ref: Las Nieves/Rebolo sur
    "TECNICO 2": {"lat": 11.015, "lon": -74.825, "zona": "Norte/Villa Santos"}, # Ref: Buenavista
    "TECNICO 3": {"lat": 10.970, "lon": -74.815, "zona": "Silencio/Olaya"},     # Ref: El Silencio
    "TECNICO 4": {"lat": 10.999, "lon": -74.798, "zona": "Prado/Centro"},       # Ref: El Prado
    "TECNICO 5": {"lat": 10.940, "lon": -74.820, "zona": "Bosque/Suroccidente"},# Ref: El Bosque
    "TECNICO 6": {"lat": 10.950, "lon": -74.840, "zona": "Caribe Verde/Paz"},   # Ref: Circunvalar
    "TECNICO 7": {"lat": 10.955, "lon": -74.775, "zona": "Sur/Chinita"},        # Ref: Simón Bolívar
    "TECNICO 8": {"lat": 11.040, "lon": -74.850, "zona": "Flores/Industrial"}   # Ref: Las Flores
}

# --- MAESTRO DE BARRIOS (Tu asignación) ---
MAESTRA_BARRIOS = {
    # TECNICO 1
    "BOYACA": "TECNICO 1", "REBOLO": "TECNICO 1", "SAN JOSE": "TECNICO 1", "LA CHINITA": "TECNICO 1",
    "ALAMEDA DEL RIO": "TECNICO 1", "CARIBE VERDE": "TECNICO 1", "VILLAS DE SAN PABLO": "TECNICO 1",
    # TECNICO 2
    "VILLA SANTOS": "TECNICO 2", "RIOMAR": "TECNICO 2", "ALTOS DE RIOMAR": "TECNICO 2", "EL GOLF": "TECNICO 2",
    # TECNICO 3
    "EL SILENCIO": "TECNICO 3", "LA CUMBRE": "TECNICO 3", "LOS NOGALES": "TECNICO 3", "CIUDAD JARDIN": "TECNICO 3",
    # TECNICO 4
    "EL PRADO": "TECNICO 4", "BOSTON": "TECNICO 4", "BARRIO ABAJO": "TECNICO 4", "MODELO": "TECNICO 4",
    # TECNICO 5
    "EL BOSQUE": "TECNICO 5", "LA PRADERA": "TECNICO 5", "LOS OLIVOS": "TECNICO 5", "LA MANGA": "TECNICO 5",
    # TECNICO 6
    "LA PAZ": "TECNICO 6", "LOS ROSALES": "TECNICO 6", "EL PUEBLO": "TECNICO 6", "CARIBE VERDE": "TECNICO 6",
    # TECNICO 7
    "LAS NIEVES": "TECNICO 7", "SIMON BOLIVAR": "TECNICO 7", "LA LUZ": "TECNICO 7", "LA UNION": "TECNICO 7",
    # TECNICO 8
    "LAS FLORES": "TECNICO 8", "SIAPE": "TECNICO 8", "VILLA FLORENCIA": "TECNICO 8"
}

# --- FUNCIONES ---
def limpiar_texto(txt):
    if not txt: return ""
    txt = str(txt).upper().strip()
    return "".join(c for c in unicodedata.normalize('NFD', txt) if unicodedata.category(c) != 'Mn')

def obtener_geolocalizacion(tecnico):
    """Devuelve lat/lon base según el técnico + un 'ruido' aleatorio para dispersar puntos"""
    if tecnico in CENTROIDES_ZONA:
        base = CENTROIDES_ZONA[tecnico]
        # Jitter: +/- 0.006 grados (aprox 600 metros) para simular distribución barrial
        lat_random = base['lat'] + np.random.uniform(-0.006, 0.006)
        lon_random = base['lon'] + np.random.uniform(-0.006, 0.006)
        return lat_random, lon_random
    return 10.9685, -74.7813  # Centro Barranquilla por defecto

# --- PDF CLASS ---
class PDFListado(FPDF):
    def header(self):
        self.set_fill_color(0, 51, 102) 
        self.rect(0, 0, 297, 20, 'F')
        self.set_font('Arial', 'B', 16)
        self.set_text_color(255, 255, 255)
        self.set_xy(10, 5)
        self.cell(0, 10, 'UT ITA RADIAN - HOJA DE RUTA', 0, 1, 'C')
        self.ln(10)

def crear_pdf_horizontal(df, tecnico, col_map):
    pdf = PDFListado(orientation='L', unit='mm', format='A4')
    pdf.add_page()
    pdf.set_font('Arial', 'B', 12)
    pdf.set_text_color(0, 0, 0)
    pdf.cell(0, 10, f"GESTOR: {tecnico} | FECHA: {datetime.now().strftime('%d/%m/%Y')}", 0, 1)
    
    headers = ['CUENTA', 'MEDIDOR', 'BARRIO', 'DIRECCION', 'CLIENTE']
    widths = [30, 30, 60, 90, 60]
    pdf.set_fill_color(220, 220, 220)
    pdf.set_font('Arial', 'B', 10)
    for h, w in zip(headers, widths): pdf.cell(w, 8, h, 1, 0, 'C', 1)
    pdf.ln()
    pdf.set_font('Arial', '', 9)
    for _, row in df.iterrows():
        for h, w in zip(headers, widths):
            col_real = col_map.get(h)
            val = str(row[col_real])[:45] if col_real else ""
            try: val = val.encode('latin-1', 'replace').decode('latin-1')
            except: pass
            pdf.cell(w, 8, val, 1, 0, 'L')
        pdf.ln()
    return pdf.output(dest='S').encode('latin-1')

# --- APP LAYOUT ---
col_u1, col_u2 = st.columns([1, 2])
with col_u1:
    st.subheader("📂 Carga de Archivos")
    pdf_file = st.file_uploader("1. PDF Pólizas", type="pdf")
    excel_file = st.file_uploader("2. Base Diaria", type=["xlsx", "csv"])
    MAX_CUPO = st.number_input("Tope Tareas/Técnico", value=35)

if excel_file:
    # 1. PROCESAMIENTO INICIAL
    try:
        if excel_file.name.endswith('.csv'): df = pd.read_csv(excel_file, sep=None, engine='python', encoding='utf-8-sig')
        else: df = pd.read_excel(excel_file)
        df.columns = [limpiar_texto(c) for c in df.columns]

        # Detectar columnas
        def find_col(k_list):
            for k in k_list:
                for c in df.columns:
                    if k in c: return c
            return None
        
        col_barrio = find_col(['BARRIO', 'SECTOR'])
        col_cta = find_col(['CUENTA', 'POLIZA', 'NRO'])
        col_dir = find_col(['DIRECCION', 'DIR'])

        if col_barrio:
            # Asignar Técnico
            def asignar(b):
                clean = limpiar_texto(str(b))
                if clean in MAESTRA_BARRIOS: return MAESTRA_BARRIOS[clean]
                for k, v in MAESTRA_BARRIOS.items():
                    if k in clean: return v
                return "SIN_ASIGNAR"
            
            df['TECNICO_PREVIO'] = df[col_barrio].apply(asignar)
            
            # --- GENERAR COORDENADAS PARA EL MAPA ---
            lat_list = []
            lon_list = []
            for t in df['TECNICO_PREVIO']:
                lat, lon = obtener_geolocalizacion(t)
                lat_list.append(lat)
                lon_list.append(lon)
            
            df['lat'] = lat_list
            df['lon'] = lon_list

            # --- VISUALIZADOR DE MAPA ---
            with col_u2:
                st.subheader("🗺️ Mapa de Cobertura Barranquilla")
                # Gráfico de Mapa con Plotly
                fig = px.scatter_mapbox(
                    df, 
                    lat="lat", 
                    lon="lon", 
                    color="TECNICO_PREVIO",
                    hover_name=col_barrio,
                    hover_data=[col_cta, 'TECNICO_PREVIO'],
                    zoom=10.5,
                    center={"lat": 10.98, "lon": -74.80}, # Centro BQ
                    height=500,
                    size_max=15
                )
                fig.update_layout(mapbox_style="open-street-map") # Mapa real gratuito
                fig.update_layout(margin={"r":0,"t":0,"l":0,"b":0})
                st.plotly_chart(fig, use_container_width=True)
                
                # Alerta de Sin Asignar
                sin_asignar = df[df['TECNICO_PREVIO'] == "SIN_ASIGNAR"]
                if not sin_asignar.empty:
                    st.error(f"⚠️ Hay {len(sin_asignar)} órdenes en barrios desconocidos (Puntos Rojos en el centro).")

            # --- BOTÓN DE ACCIÓN ---
            st.divider()
            if pdf_file:
                if st.button("🚀 Confirmar Distribución y Descargar", type="primary"):
                    with st.spinner("Generando rutas..."):
                        # (LÓGICA DE PROCESAMIENTO Y ZIP IGUAL QUE V110)
                        # ... Aquí pegas la lógica de generación del ZIP ...
                        # ... Para no hacer el código infinito, asumo que usas la lógica V110 ...
                        
                        # SIMULACIÓN DE ZIP (Para que funcione el ejemplo visual)
                        zip_buffer = io.BytesIO()
                        with zipfile.ZipFile(zip_buffer, "w") as zf:
                            zf.writestr("info.txt", "Rutas generadas.")
                        
                        st.success("✅ ¡Rutas Listas!")
                        st.download_button("⬇️ Bajar ZIP", zip_buffer.getvalue(), "Logistica_Mapa.zip", "application/zip")
            else:
                st.warning("Sube el PDF para continuar.")

    except Exception as e:
        st.error(f"Error: {e}")
