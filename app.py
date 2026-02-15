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
import numpy as np

# --- CONFIGURACIÓN VISUAL ---
st.set_page_config(page_title="Logística Dark V113", layout="wide")

# --- ESTILOS CSS (MODO OSCURO CORPORATIVO) ---
st.markdown("""
    <style>
    /* Fondo General - Gris Oscuro Azulado */
    .stApp {
        background-color: #0E1117;
        color: #FAFAFA;
    }
    
    /* Pestañas */
    .stTabs [data-baseweb="tab-list"] { gap: 8px; }
    .stTabs [data-baseweb="tab"] {
        height: 50px;
        background-color: #262730;
        color: white;
        border-radius: 5px;
        padding: 10px;
        border: 1px solid #41444C;
    }
    .stTabs [aria-selected="true"] {
        background-color: #003366; /* Azul Corporativo */
        color: white;
        border: 2px solid #00A8E8;
    }

    /* Tablas y Dataframes */
    div[data-testid="stDataFrame"] {
        background-color: #262730;
        border-radius: 10px;
        padding: 10px;
    }

    /* Expanders */
    .streamlit-expanderHeader {
        background-color: #262730;
        color: white;
    }
    
    /* Métricas */
    div[data-testid="metric-container"] {
        background-color: #1F2937;
        border: 1px solid #374151;
        padding: 10px;
        border-radius: 8px;
        color: white;
    }
    </style>
""", unsafe_allow_html=True)

st.title("🚛 Logística ITA RADIAN: Panel de Control")

# --- 1. CEREBRO DE ASIGNACIÓN (Tu Excel Original) ---
MAESTRA_DEFAULT = {
    # TECNICO 1
    "BOYACA": "TECNICO 1", "REBOLO": "TECNICO 1", "SAN JOSE": "TECNICO 1", "LA CHINITA": "TECNICO 1",
    "LA LUZ": "TECNICO 1", "LAS NIEVES": "TECNICO 1", "SIMON BOLIVAR": "TECNICO 1", "ALAMEDA DEL RIO": "TECNICO 1",
    "CARIBE VERDE": "TECNICO 1", "VILLAS DE SAN PABLO": "TECNICO 1", "EL PUEBLO": "TECNICO 1",
    "LA ALBORAYA": "TECNICO 1", "EL CAMPITO": "TECNICO 1", "LA MAGDALENA": "TECNICO 1", "PASADENA": "TECNICO 1",
    
    # TECNICO 2
    "VILLA SANTOS": "TECNICO 2", "RIOMAR": "TECNICO 2", "ALTOS DE RIOMAR": "TECNICO 2", "EL GOLF": "TECNICO 2",
    "SAN VICENTE": "TECNICO 2", "EL POBLADO": "TECNICO 2", "GRANADILLO": "TECNICO 2", "VILLA CAROLINA": "TECNICO 2",
    "PARAISO": "TECNICO 2", "LAS FLORES": "TECNICO 2", "SIAPE": "TECNICO 2", "SAN SALVADOR": "TECNICO 2",

    # TECNICO 3
    "EL SILENCIO": "TECNICO 3", "LA CUMBRE": "TECNICO 3", "LOS NOGALES": "TECNICO 3", "CIUDAD JARDIN": "TECNICO 3",
    "MERCEDES": "TECNICO 3", "LOS ALPES": "TECNICO 3", "LAS ESTRELLAS": "TECNICO 3", "CAMPO ALEGRE": "TECNICO 3",

    # TECNICO 4
    "EL PRADO": "TECNICO 4", "BOSTON": "TECNICO 4", "BARRIO ABAJO": "TECNICO 4", "MODELO": "TECNICO 4",
    "MONTECRISTO": "TECNICO 4", "SAN FRANCISCO": "TECNICO 4", "BELLAVISTA": "TECNICO 4", "LA CONCEPCION": "TECNICO 4",
    "SANTA ANA": "TECNICO 4",

    # TECNICO 5
    "EL BOSQUE": "TECNICO 5", "LA PRADERA": "TECNICO 5", "LOS OLIVOS": "TECNICO 5", "LA MANGA": "TECNICO 5",
    "MEQUEJO": "TECNICO 5", "POR FIN": "TECNICO 5", "LA ESMERALDA": "TECNICO 5", "VILLA SAN PEDRO": "TECNICO 5",

    # TECNICO 6
    "LA PAZ": "TECNICO 6", "CIUDAD MODESTO": "TECNICO 6", "LOS ROSALES": "TECNICO 6", "LA GLORIA": "TECNICO 6",
    "LA CORDIALIDAD": "TECNICO 6", "VILLA DEL ROSARIO": "TECNICO 6", "EL ROMANCE": "TECNICO 6", "METRO PARQUE": "TECNICO 6",

    # TECNICO 7
    "CHIQUINQUIRA": "TECNICO 7", "SAN ROQUE": "TECNICO 7", "ATLANTICO": "TECNICO 7", "LA VICTORIA": "TECNICO 7",
    "LAS PALMAS": "TECNICO 7", "EL MILAGRO": "TECNICO 7", "TAYRONA": "TECNICO 7",
    
    # TECNICO 8
    "VILLA FLORENCIA": "TECNICO 8"
}

# --- 2. COORDENADAS (Para Mapa) ---
COORDENADAS_REF = {
    "VILLA SANTOS": [11.015, -74.825], "RIOMAR": [11.020, -74.830], "LAS FLORES": [11.040, -74.850],
    "EL PRADO": [10.999, -74.798], "EL SILENCIO": [10.970, -74.815], "EL BOSQUE": [10.940, -74.820],
    "CARIBE VERDE": [10.945, -74.860], "REBOLO": [10.960, -74.780], "SIMON BOLIVAR": [10.950, -74.770]
}
CENTROIDES_GENERICOS = {
    "TECNICO 1": [10.940, -74.790], "TECNICO 2": [11.015, -74.825], "TECNICO 3": [10.970, -74.815],
    "TECNICO 4": [10.999, -74.798], "TECNICO 5": [10.940, -74.820], "TECNICO 6": [10.950, -74.840],
    "TECNICO 7": [10.955, -74.775], "TECNICO 8": [11.040, -74.850]
}

# --- FUNCIONES ---
def limpiar_y_estandarizar(txt):
    if not txt: return ""
    txt = str(txt).upper().strip()
    txt = "".join(c for c in unicodedata.normalize('NFD', txt) if unicodedata.category(c) != 'Mn')
    txt = re.sub(r'\b(URB|URBANIZACION|BARRIO|BRR|SECTOR|ETAPA|II|III|I)\b', '', txt).strip()
    return txt

def obtener_coords(barrio, tecnico):
    b_clean = limpiar_y_estandarizar(barrio)
    lat_base, lon_base = None, None
    for k, coords in COORDENADAS_REF.items():
        if k in b_clean: lat_base, lon_base = coords; break
    if not lat_base:
        lat_base, lon_base = CENTROIDES_GENERICOS.get(tecnico, [10.968, -74.781])
    
    lat_final = lat_base + np.random.uniform(-0.003, 0.003)
    lon_final = lon_base + np.random.uniform(-0.003, 0.003)
    return lat_final, lon_final

def cargar_cerebro(file):
    mapa = MAESTRA_DEFAULT.copy()
    try:
        if file.name.endswith('.csv'): df = pd.read_csv(file, sep=None, engine='python')
        else: df = pd.read_excel(file)
        for _, row in df.iterrows():
            b = limpiar_y_estandarizar(str(row.iloc[0]))
            t = str(row.iloc[1]).upper().strip()
            mapa[b] = t
    except: pass
    return mapa

# --- PDF ---
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
    pdf.set_fill_color(200, 200, 200) # Gris claro PDF
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

# --- ESTADO DE SESIÓN ---
if 'mapa_barrios' not in st.session_state: st.session_state['mapa_barrios'] = MAESTRA_DEFAULT
if 'df_procesado' not in st.session_state: st.session_state['df_procesado'] = None
if 'zip_final' not in st.session_state: st.session_state['zip_final'] = None

# --- UI TABS ---
tab1, tab2 = st.tabs(["🚀 Operación Diaria", "⚙️ Configuración & Maestros"])

# --- TAB 2: CONFIG ---
with tab2:
    st.header("Gestión de Maestros")
    maestro_up = st.file_uploader("Actualizar Listado Barrios (Excel)", type=["xlsx", "csv"])
    if maestro_up:
        st.session_state['mapa_barrios'] = cargar_cerebro(maestro_up)
        st.success("✅ Base de datos actualizada")
    st.info("Nota: Sube un archivo con columnas: BARRIO | TECNICO para sobreescribir la lógica.")

# --- TAB 1: OPERACIÓN ---
with tab1:
    col_u1, col_u2 = st.columns(2)
    with col_u1: pdf_file = st.file_uploader("1. Subir PDF Pólizas", type="pdf")
    with col_u2: excel_file = st.file_uploader("2. Subir Base Diaria", type=["xlsx", "csv"])

    if excel_file:
        try:
            if excel_file.name.endswith('.csv'): df = pd.read_csv(excel_file, sep=None, engine='python', encoding='utf-8-sig')
            else: df = pd.read_excel(excel_file)
            
            # Limpieza Columnas
            df.columns = [str(c).upper().strip() for c in df.columns]

            # Detectar Columnas
            def find_col(k_list):
                for k in k_list:
                    for c in df.columns:
                        if k in c: return c
                return None
            col_barrio = find_col(['BARRIO', 'SECTOR'])
            col_cta = find_col(['CUENTA', 'POLIZA', 'NRO'])
            col_dir = find_col(['DIRECCION', 'DIR'])

            if col_barrio and col_cta:
                # 1. Asignación
                def asignar(b):
                    b_std = limpiar_y_estandarizar(str(b))
                    if b_std in st.session_state['mapa_barrios']: return st.session_state['mapa_barrios'][b_std]
                    for k, v in st.session_state['mapa_barrios'].items():
                        if k in b_std: return v
                    return "SIN_ASIGNAR"
                
                df['TECNICO_ASIGNADO'] = df[col_barrio].apply(asignar)

                # 2. Geolocalización
                lat_l, lon_l = [], []
                for idx, row in df.iterrows():
                    lat, lon = obtener_coords(str(row[col_barrio]), row['TECNICO_ASIGNADO'])
                    lat_l.append(lat)
                    lon_l.append(lon)
                df['lat'] = lat_l
                df['lon'] = lon_l
                
                st.session_state['df_procesado'] = df

                # --- NUEVO: TABLA RESUMEN POR TÉCNICO ---
                st.divider()
                st.subheader("📋 Resumen de Asignación")
                
                # Agrupar datos para la tabla resumen
                # Agrupamos por Tecnico y hacemos una lista única de barrios
                resumen = df.groupby('TECNICO_ASIGNADO').agg(
                    Ordenes=('TECNICO_ASIGNADO', 'count'),
                    Barrios_Asignados=(col_barrio, lambda x: ', '.join(sorted(list(set(x)))))
                ).reset_index()
                
                st.dataframe(resumen, use_container_width=True)

                # --- MAPA INTERACTIVO ---
                st.subheader("🗺️ Cobertura Geográfica")
                fig = px.scatter_mapbox(
                    df, lat="lat", lon="lon", color="TECNICO_ASIGNADO",
                    hover_name="TECNICO_ASIGNADO", hover_data=[col_barrio, col_cta],
                    zoom=11, center={"lat": 10.98, "lon": -74.80}, height=500, size_max=15
                )
                fig.update_layout(mapbox_style="carto-darkmatter") # Mapa Oscuro
                fig.update_layout(margin={"r":0,"t":0,"l":0,"b":0})
                st.plotly_chart(fig, use_container_width=True)

                # --- BOTÓN FINAL ---
                if pdf_file:
                    if st.button("🚀 CONFIRMAR Y GENERAR ZIP", type="primary"):
                        with st.spinner("Procesando..."):
                            df['CARPETA'] = df['TECNICO_ASIGNADO']
                            
                            # Procesar PDF
                            doc = fitz.open(stream=pdf_file.read(), filetype="pdf")
                            mapa_pdfs = {}
                            i = 0
                            while i < len(doc):
                                txt = doc[i].get_text()
                                match = re.search(r"Póliza\s*No:?\s*(\d+)", txt, re.IGNORECASE)
                                if match:
                                    pid = match.group(1)
                                    pgs = [i]
                                    while i+1 < len(doc):
                                        if "Póliza No" not in doc[i+1].get_text(): pgs.append(i+1); i+=1
                                        else: break
                                    sub = fitz.open()
                                    for p in pgs: sub.insert_pdf(doc, from_page=p, to_page=p)
                                    mapa_pdfs[pid] = sub.tobytes()
                                    sub.close()
                                i += 1

                            # ZIP
                            zip_buffer = io.BytesIO()
                            with zipfile.ZipFile(zip_buffer, "w") as zf:
                                out_tot = io.BytesIO()
                                with pd.ExcelWriter(out_tot, engine='xlsxwriter') as w: df.to_excel(w, index=False)
                                zf.writestr("0_BASE_TOTAL.xlsx", out_tot.getvalue())
                                
                                col_map = {'CUENTA': col_cta, 'MEDIDOR': find_col(['MEDIDOR']), 'BARRIO': col_barrio, 'DIRECCION': col_dir, 'CLIENTE': find_col(['CLIENTE'])}
                                
                                for tec in df['CARPETA'].unique():
                                    if "SIN_" in tec: continue
                                    safe = str(tec).replace(" ","_")
                                    df_t = df[df['CARPETA'] == tec].copy()
                                    
                                    # PDF Horizontal
                                    pdf_h = crear_pdf_horizontal(df_t, tec, col_map)
                                    zf.writestr(f"{safe}/1_LISTADO.pdf", pdf_h)
                                    
                                    # Excel
                                    out_t = io.BytesIO()
                                    with pd.ExcelWriter(out_t, engine='xlsxwriter') as w: df_t.to_excel(w, index=False)
                                    zf.writestr(f"{safe}/2_DIGITAL.xlsx", out_t.getvalue())
                                    
                                    # Impresion
                                    m = fitz.open()
                                    f = False
                                    for _, r in df_t.iterrows():
                                        c = str(r[col_cta])
                                        d = None
                                        for k,v in mapa_pdfs.items():
                                            if k in c: d=v; break
                                        if d:
                                            f=True
                                            zf.writestr(f"{safe}/POLIZAS/Poliza_{c}.pdf", d)
                                            with fitz.open(stream=d, filetype="pdf") as t: m.insert_pdf(t)
                                    if f: zf.writestr(f"{safe}/3_IMPRESION.pdf", m.tobytes())
                                    m.close()
                            
                            st.session_state['zip_final'] = zip_buffer.getvalue()
                            st.success("✅ ¡Proceso Terminado!")

            else: st.error("Faltan columnas (Barrio/Cuenta).")
        except Exception as e: st.error(f"Error: {e}")

    if st.session_state['zip_final']:
        st.download_button("⬇️ Descargar ZIP Final", st.session_state['zip_final'], "Logistica_Dark.zip", "application/zip", type="primary")
