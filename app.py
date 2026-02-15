import streamlit as st
import fitz  # PyMuPDF
import pandas as pd
import re
import io
import zipfile
import unicodedata
from fpdf import FPDF
from datetime import datetime
import math
import plotly.express as px

# --- CONFIGURACIÓN VISUAL ---
st.set_page_config(page_title="Gestor Zonas V121", layout="wide")

st.markdown("""
    <style>
    .stApp { background-color: #0E1117; color: #FAFAFA; }
    .stTabs [data-baseweb="tab-list"] { gap: 8px; }
    .stTabs [data-baseweb="tab"] { height: 50px; background-color: #262730; color: white; border-radius: 5px; border: 1px solid #41444C; }
    .stTabs [aria-selected="true"] { background-color: #004080; color: white; border: 2px solid #00A8E8; }
    
    /* Estilo para las tarjetas de técnicos */
    .tech-card {
        background-color: #1F2937;
        padding: 15px;
        border-radius: 8px;
        border: 1px solid #374151;
        margin-bottom: 10px;
    }
    .big-number { font-size: 24px; font-weight: bold; color: #00A8E8; }
    </style>
""", unsafe_allow_html=True)

st.title("🗺️ Logística ITA: Gestor de Zonas y Barrios")

# --- 1. ESTADO INICIAL ---
MAESTRA_GENERICA = {
    "BOYACA": "TECNICO 1", "REBOLO": "TECNICO 1", "SAN JOSE": "TECNICO 1", 
    "VILLA SANTOS": "TECNICO 2", "RIOMAR": "TECNICO 2", 
    "EL SILENCIO": "TECNICO 3", "LA CUMBRE": "TECNICO 3",
    "EL PRADO": "TECNICO 4", "BOSTON": "TECNICO 4",
    "EL BOSQUE": "TECNICO 5", "LA PRADERA": "TECNICO 5",
    "LA PAZ": "TECNICO 6", "CARIBE VERDE": "TECNICO 6",
    "LAS NIEVES": "TECNICO 7", "SIMON BOLIVAR": "TECNICO 7",
    "VILLA FLORENCIA": "TECNICO 8", "SIAPE": "TECNICO 8"
}

# --- FUNCIONES ---
def limpiar_estricto(txt):
    if not txt: return ""
    txt = str(txt).upper().strip()
    txt = "".join(c for c in unicodedata.normalize('NFD', txt) if unicodedata.category(c) != 'Mn')
    return txt

def limpiar_flexible(txt):
    txt = limpiar_estricto(txt)
    txt = re.sub(r'\b(BARRIO|URB|URBANIZACION|SECTOR|ETAPA|ZONA|BRR)\b', '', txt).strip()
    return txt

def buscar_tecnico_exacto(barrio_input, mapa_barrios):
    if not barrio_input: return "SIN_ASIGNAR"
    b_raw = limpiar_estricto(barrio_input)
    if b_raw in mapa_barrios: return mapa_barrios[b_raw]
    b_flex = limpiar_flexible(barrio_input)
    if b_flex in mapa_barrios: return mapa_barrios[b_flex]
    for k, v in mapa_barrios.items():
        if k == b_flex: return v
        if len(k) > 4 and k in b_raw: return v
    return "SIN_ASIGNAR"

def cargar_maestro_dinamico(file):
    mapa = {}
    try:
        if file.name.endswith('.csv'): df = pd.read_csv(file, sep=None, engine='python')
        else: df = pd.read_excel(file)
        c_b, c_t = df.columns[0], df.columns[1]
        for _, row in df.iterrows():
            b = limpiar_estricto(str(row[c_b]))
            t = str(row[c_t]).upper().strip()
            if t and t != "NAN": mapa[b] = t
    except: return MAESTRA_GENERICA
    return mapa

# Peso Dirección
def calcular_peso_js(txt):
    clean = limpiar_estricto(txt)
    penalidad = 5000 if "SUR" in clean else 0
    nums = re.findall(r'(\d+)', clean)
    ref = int(nums[0]) if nums else 0
    if "CL" in clean or "CALLE" in clean: peso = (110 - ref) * 1000
    else: peso = ref * 1000
    return peso + penalidad + (int(nums[1]) if len(nums)>1 else 0)

# PDF
class PDFListado(FPDF):
    def header(self):
        self.set_fill_color(0, 51, 102) 
        self.rect(0, 0, 297, 20, 'F')
        self.set_font('Arial', 'B', 16)
        self.set_text_color(255, 255, 255)
        self.set_xy(10, 5)
        self.cell(0, 10, 'UT ITA RADIAN - HOJA DE RUTA', 0, 1, 'C')
        self.ln(10)

def crear_pdf(df, tecnico, col_map):
    pdf = PDFListado(orientation='L', unit='mm', format='A4')
    pdf.add_page()
    pdf.set_font('Arial', 'B', 12)
    pdf.set_text_color(0, 0, 0)
    pdf.cell(0, 10, f"GESTOR: {tecnico} | FECHA: {datetime.now().strftime('%d/%m/%Y')}", 0, 1)
    headers = ['CUENTA', 'MEDIDOR', 'BARRIO', 'DIRECCION', 'CLIENTE']
    widths = [30, 30, 60, 90, 60]
    pdf.set_fill_color(200, 200, 200)
    pdf.set_font('Arial', 'B', 10)
    for h, w in zip(headers, widths): pdf.cell(w, 8, h, 1, 0, 'C', 1)
    pdf.ln()
    pdf.set_font('Arial', '', 9)
    for _, row in df.iterrows():
        for h, w in zip(headers, widths):
            val = str(row[col_map.get(h)])[:45] if col_map.get(h) else ""
            try: val = val.encode('latin-1', 'replace').decode('latin-1')
            except: pass
            pdf.cell(w, 8, val, 1, 0, 'L')
        pdf.ln()
    return pdf.output(dest='S').encode('latin-1')

# --- SESSION ---
if 'mapa_actual' not in st.session_state: st.session_state['mapa_actual'] = MAESTRA_GENERICA
if 'df_simulado' not in st.session_state: st.session_state['df_simulado'] = None
if 'zip_listo' not in st.session_state: st.session_state['zip_listo'] = None

# --- SIDEBAR: CUADRILLA ---
st.sidebar.header("👷 Cuadrilla")
lista_tecnicos = sorted(list(set(st.session_state['mapa_actual'].values())))
TECNICOS_ACTIVOS = []
for tec in lista_tecnicos:
    if st.sidebar.toggle(f"✅ {tec}", value=True): TECNICOS_ACTIVOS.append(tec)

# --- TABS ---
tab_carga, tab_zonas, tab_maestro = st.tabs(["📂 1. Cargar Datos", "🌍 2. Gestor de Zonas (Simulador)", "⚙️ 3. Operarios"])

# --- TAB 3: MAESTRO ---
with tab_maestro:
    st.header("Actualizar Base de Operarios")
    maestro_file = st.file_uploader("Subir Maestro (Barrio | Técnico)", type=["xlsx", "csv"])
    if maestro_file:
        st.session_state['mapa_actual'] = cargar_maestro_dinamico(maestro_file)
        st.success("✅ Base Actualizada")

# --- TAB 1: CARGA ---
with tab_carga:
    c1, c2 = st.columns(2)
    with c1: pdf_in = st.file_uploader("1. PDF Pólizas", type="pdf")
    with c2: excel_in = st.file_uploader("2. Base Diaria", type=["xlsx", "csv"])
    
    if excel_in and pdf_in:
        if st.button("🚀 ANALIZAR DATOS", type="primary"):
            try:
                if excel_in.name.endswith('.csv'): df = pd.read_csv(excel_in, sep=None, engine='python', encoding='utf-8-sig')
                else: df = pd.read_excel(excel_in)
                df.columns = [limpiar_estricto(c) for c in df.columns]
                
                # Columnas
                def find(k):
                    for x in k:
                        for c in df.columns: 
                            if x in c: return c
                    return None
                
                c_barrio = find(['BARRIO', 'SECTOR'])
                c_cta = find(['CUENTA', 'POLIZA', 'NRO'])
                
                if c_barrio and c_cta:
                    # Asignación Inicial
                    df['TECNICO_ASIGNADO'] = df[c_barrio].apply(lambda x: buscar_tecnico_exacto(str(x), st.session_state['mapa_actual']))
                    
                    st.session_state['df_simulado'] = df
                    st.session_state['col_barrio'] = c_barrio
                    st.session_state['col_cta'] = c_cta
                    st.session_state['col_dir'] = find(['DIRECCION', 'DIR'])
                    st.session_state['col_med'] = find(['MEDIDOR', 'SERIE'])
                    st.session_state['col_cli'] = find(['CLIENTE', 'NOMBRE'])
                    
                    st.success("✅ Datos listos. Ve a la pestaña 'Gestor de Zonas'.")
                else: st.error("Faltan columnas clave.")
            except Exception as e: st.error(f"Error: {e}")

# --- TAB 2: GESTOR DE ZONAS (NUEVO DISEÑO) ---
with tab_zonas:
    if st.session_state['df_simulado'] is not None:
        df = st.session_state['df_simulado']
        c_barrio = st.session_state['col_barrio']
        
        # --- SECCIÓN A: REASIGNACIÓN RÁPIDA ---
        st.markdown("### 🔄 Mover Barrios Completos")
        st.info("Selecciona el técnico de origen, elige el barrio que quieres quitarle y pásalo a otro.")
        
        col_move1, col_move2, col_move3, col_move4 = st.columns([1.5, 1.5, 1.5, 1])
        
        with col_move1:
            # Filtramos solo técnicos que tienen algo asignado
            tecnicos_con_carga = sorted(df['TECNICO_ASIGNADO'].unique())
            origen = st.selectbox("1. Desde (Origen):", options=["SELECCIONAR"] + tecnicos_con_carga)
        
        with col_move2:
            # Mostrar solo barrios del origen seleccionado
            if origen != "SELECCIONAR":
                barrios_origen = df[df['TECNICO_ASIGNADO'] == origen][c_barrio].value_counts()
                # Formato: "BARRIO (Cant)"
                opciones_barrio = [f"{idx} ({val})" for idx, val in barrios_origen.items()]
                barrio_seleccionado_str = st.selectbox("2. Barrio a Mover:", options=opciones_barrio)
            else:
                st.selectbox("2. Barrio a Mover:", ["---"])
                barrio_seleccionado_str = None
        
        with col_move3:
            destino = st.selectbox("3. Hacia (Destino):", options=["SELECCIONAR"] + TECNICOS_ACTIVOS)
            
        with col_move4:
            st.write("")
            st.write("")
            if st.button("🔀 MOVER", type="primary"):
                if origen != "SELECCIONAR" and destino != "SELECCIONAR" and barrio_seleccionado_str:
                    # Extraer nombre limpio del barrio (quitando la cantidad entre parentesis)
                    barrio_real = barrio_seleccionado_str.rsplit(' (', 1)[0]
                    
                    # Aplicar cambio
                    mask = (df['TECNICO_ASIGNADO'] == origen) & (df[c_barrio] == barrio_real)
                    count_moved = mask.sum()
                    df.loc[mask, 'TECNICO_ASIGNADO'] = destino
                    
                    st.session_state['df_simulado'] = df
                    st.toast(f"✅ Se movieron {count_moved} órdenes de {barrio_real} a {destino}", icon="🎉")
                    st.rerun()
                else:
                    st.error("Completa los campos.")

        st.divider()

        # --- SECCIÓN B: VISOR DE CARTERA (DETALLE) ---
        st.subheader("📋 Estado Actual de la Cartera")
        
        # Calcular resumen global
        resumen_global = df['TECNICO_ASIGNADO'].value_counts()
        
        # Grid layout para las tarjetas
        # Hacemos filas de 3 columnas
        cols_display = st.columns(3)
        
        # Recorremos técnicos
        tecnicos_presentes = sorted(df['TECNICO_ASIGNADO'].unique())
        
        for i, tec in enumerate(tecnicos_presentes):
            col_idx = i % 3
            with cols_display[col_idx]:
                total_tec = resumen_global.get(tec, 0)
                
                # Crear tarjeta visual con expander
                with st.expander(f"👷 **{tec}** |  📦 Total: {total_tec}", expanded=False):
                    # Tabla de barrios de este técnico
                    sub_df = df[df['TECNICO_ASIGNADO'] == tec]
                    conteo_barrios = sub_df[c_barrio].value_counts().reset_index()
                    conteo_barrios.columns = ['Barrio', 'Cant']
                    st.dataframe(conteo_barrios, hide_index=True, use_container_width=True)

        # --- BOTÓN FINAL ---
        st.divider()
        if st.button("✅ CONFIRMAR DISTRIBUCIÓN Y GENERAR ZIP", type="primary"):
            with st.spinner("Empaquetando..."):
                # ZIP Logic
                df['CARPETA'] = df['TECNICO_ASIGNADO']
                pdf_in.seek(0)
                doc = fitz.open(stream=pdf_in.read(), filetype="pdf")
                mapa_p = {}
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
                        mapa_p[pid] = sub.tobytes()
                        sub.close()
                    i += 1
                
                zip_buffer = io.BytesIO()
                with zipfile.ZipFile(zip_buffer, "w") as zf:
                    out_b = io.BytesIO()
                    with pd.ExcelWriter(out_b, engine='xlsxwriter') as w: df.to_excel(w, index=False)
                    zf.writestr("01_CONSOLIDADO.xlsx", out_b.getvalue())
                    
                    c_map = {'CUENTA': st.session_state['col_cta'], 'MEDIDOR': st.session_state['col_med'], 'BARRIO': c_barrio, 'DIRECCION': st.session_state['col_dir'], 'CLIENTE': st.session_state['col_cli']}
                    
                    for tec in df['CARPETA'].unique():
                        if "SIN_" in tec: continue
                        safe = str(tec).replace(" ","_")
                        df_t = df[df['CARPETA'] == tec].copy()
                        if st.session_state['col_dir']:
                            df_t['P'] = df_t[st.session_state['col_dir']].astype(str).apply(calcular_peso_js)
                            df_t = df_t.sort_values('P')
                        
                        pdf_h = crear_pdf(df_t, tec, c_map)
                        zf.writestr(f"{safe}/1_LISTADO.pdf", pdf_h)
                        out_t = io.BytesIO()
                        with pd.ExcelWriter(out_t, engine='xlsxwriter') as w: df_t.to_excel(w, index=False)
                        zf.writestr(f"{safe}/2_DIGITAL.xlsx", out_t.getvalue())
                        
                        m = fitz.open()
                        f = False
                        for _, r in df_t.iterrows():
                            c = str(r[st.session_state['col_cta']])
                            d = None
                            for k,v in mapa_p.items():
                                if k in c: d=v; break
                            if d:
                                f=True
                                zf.writestr(f"{safe}/POLIZAS/Poliza_{c}.pdf", d)
                                with fitz.open(stream=d, filetype="pdf") as t: m.insert_pdf(t)
                        if f: zf.writestr(f"{safe}/3_IMPRESION.pdf", m.tobytes())
                        m.close()
                
                st.session_state['zip_listo'] = zip_buffer.getvalue()
                st.success("✅ Listo para descargar")

    else:
        st.info("Carga los archivos en la Pestaña 1.")

# --- DESCARGA ---
if st.session_state['zip_listo']:
    st.sidebar.divider()
    st.sidebar.download_button("⬇️ DESCARGAR ZIP", st.session_state['zip_listo'], "Logistica_Final.zip", "application/zip", type="primary")
