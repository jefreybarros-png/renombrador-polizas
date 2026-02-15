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
st.set_page_config(page_title="Logística Comandante V120", layout="wide")

st.markdown("""
    <style>
    .stApp { background-color: #0E1117; color: #FAFAFA; }
    .stTabs [data-baseweb="tab-list"] { gap: 8px; }
    .stTabs [data-baseweb="tab"] { height: 50px; background-color: #262730; color: white; border-radius: 5px; border: 1px solid #41444C; }
    .stTabs [aria-selected="true"] { background-color: #004080; color: white; border: 2px solid #00A8E8; }
    div[data-testid="stDataFrame"] { background-color: #262730; border-radius: 10px; }
    .metric-card { background-color: #1F2937; padding: 15px; border-radius: 8px; border: 1px solid #374151; text-align: center; }
    </style>
""", unsafe_allow_html=True)

st.title("🎯 Logística ITA: Simulador y Control Total")

# --- 1. ESTADO INICIAL ---
MAESTRA_GENERICA = {
    "BOYACA": "TECNICO 1", "REBOLO": "TECNICO 1", "SAN JOSE": "TECNICO 1", 
    "VILLA SANTOS": "TECNICO 2", "RIOMAR": "TECNICO 2", "LAS FLORES": "TECNICO 2",
    "EL SILENCIO": "TECNICO 3", "LA CUMBRE": "TECNICO 3", "LOS NOGALES": "TECNICO 3",
    "EL PRADO": "TECNICO 4", "BOSTON": "TECNICO 4", "BARRIO ABAJO": "TECNICO 4",
    "EL BOSQUE": "TECNICO 5", "LA PRADERA": "TECNICO 5", "LOS OLIVOS": "TECNICO 5",
    "LA PAZ": "TECNICO 6", "CARIBE VERDE": "TECNICO 6", "VILLAS DE SAN PABLO": "TECNICO 6",
    "LAS NIEVES": "TECNICO 7", "SIMON BOLIVAR": "TECNICO 7", "LA CHINITA": "TECNICO 7",
    "VILLA FLORENCIA": "TECNICO 8", "SIAPE": "TECNICO 8"
}

# --- FUNCIONES DE LIMPIEZA ---
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
    for k_maestro, tecnico in mapa_barrios.items():
        if k_maestro == b_flex: return tecnico
        if len(k_maestro) > 4 and k_maestro in b_raw: return tecnico
    return "SIN_ASIGNAR"

def cargar_maestro_dinamico(file):
    mapa = {}
    try:
        if file.name.endswith('.csv'): df = pd.read_csv(file, sep=None, engine='python')
        else: df = pd.read_excel(file)
        col_barrio, col_tec = df.columns[0], df.columns[1]
        for _, row in df.iterrows():
            b = limpiar_estricto(str(row[col_barrio]))
            t = str(row[col_tec]).upper().strip()
            if t and t != "NAN": mapa[b] = t
    except Exception as e:
        st.error(f"Error: {e}")
        return MAESTRA_GENERICA
    return mapa

# --- ALGORITMO PESO ---
VALOR_SUFIJOS = {'A': 0.1, 'B': 0.2, 'C': 0.3, 'D': 0.4, 'BIS': 0.05}
def calcular_peso_js(txt):
    clean = limpiar_estricto(txt)
    penalidad = 5000 if "SUR" in clean else 0
    nums = re.findall(r'(\d+)', clean)
    ref = int(nums[0]) if nums else 0
    if "CL" in clean or "CALLE" in clean: peso = (110 - ref) * 1000
    else: peso = ref * 1000
    secundario = int(nums[1]) if len(nums) > 1 else 0
    return peso + secundario + penalidad

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
            col_real = col_map.get(h)
            val = str(row[col_real])[:45] if col_real else ""
            try: val = val.encode('latin-1', 'replace').decode('latin-1')
            except: pass
            pdf.cell(w, 8, val, 1, 0, 'L')
        pdf.ln()
    return pdf.output(dest='S').encode('latin-1')

# --- SESSION STATE ---
if 'mapa_actual' not in st.session_state: st.session_state['mapa_actual'] = MAESTRA_GENERICA
if 'df_simulado' not in st.session_state: st.session_state['df_simulado'] = None
if 'zip_listo' not in st.session_state: st.session_state['zip_listo'] = None

# --- SIDEBAR: CUADRILLA ---
st.sidebar.header("👷 Gestión de Cuadrilla")
lista_tecnicos_detectados = sorted(list(set(st.session_state['mapa_actual'].values())))
TECNICOS_ACTIVOS = []
for tec in lista_tecnicos_detectados:
    if st.sidebar.toggle(f"✅ {tec}", value=True):
        TECNICOS_ACTIVOS.append(tec)

# --- TABS ---
tab_carga, tab_simulador, tab_maestro = st.tabs(["📂 1. Cargar Datos", "🎛️ 2. Simulador & Balanceo", "⚙️ 3. Operarios"])

# --- TAB 3: MAESTRO ---
with tab_maestro:
    st.header("Actualizar Base de Operarios")
    maestro_file = st.file_uploader("Subir Maestro (Barrio | Técnico)", type=["xlsx", "csv"])
    if maestro_file:
        st.session_state['mapa_actual'] = cargar_maestro_dinamico(maestro_file)
        st.success("✅ Base Actualizada")

# --- TAB 1: CARGA INICIAL ---
with tab_carga:
    col_in1, col_in2 = st.columns(2)
    with col_in1: pdf_in = st.file_uploader("1. PDF Pólizas", type="pdf")
    with col_in2: excel_in = st.file_uploader("2. Base Diaria", type=["xlsx", "csv"])
    
    if excel_in and pdf_in:
        if st.button("🚀 INICIAR SIMULACIÓN", type="primary"):
            try:
                if excel_in.name.endswith('.csv'): df = pd.read_csv(excel_in, sep=None, engine='python', encoding='utf-8-sig')
                else: df = pd.read_excel(excel_in)
                df.columns = [limpiar_estricto(c) for c in df.columns]
                
                # Detectar columnas
                c_barrio = next((c for c in df.columns if 'BARRIO' in c or 'SECTOR' in c), None)
                c_cta = next((c for c in df.columns if 'CUENTA' in c or 'POLIZA' in c), None)
                
                if c_barrio and c_cta:
                    # 1. Asignación Inicial
                    df['TECNICO_ASIGNADO'] = df[c_barrio].apply(lambda x: buscar_tecnico_exacto(str(x), st.session_state['mapa_actual']))
                    
                    # 2. Guardar en Sesión para Simular
                    st.session_state['df_simulado'] = df
                    st.session_state['col_barrio'] = c_barrio
                    st.session_state['col_cta'] = c_cta
                    st.session_state['col_dir'] = next((c for c in df.columns if 'DIR' in c), None)
                    st.session_state['col_med'] = next((c for c in df.columns if 'MED' in c), None)
                    st.session_state['col_cli'] = next((c for c in df.columns if 'CLI' in c or 'NOM' in c), None)
                    
                    st.success("✅ Datos cargados. Ve a la pestaña 'Simulador & Balanceo' para ajustar.")
                else:
                    st.error("No se encontraron columnas Barrio/Cuenta.")
            except Exception as e: st.error(f"Error: {e}")

# --- TAB 2: SIMULADOR (EL COMANDANTE) ---
with tab_simulador:
    if st.session_state['df_simulado'] is not None:
        df = st.session_state['df_simulado']
        c_barrio = st.session_state['col_barrio']
        
        # --- A. PANEL DE MÉTRICAS (VISUAL) ---
        st.subheader("📊 Tablero de Comando")
        conteo = df['TECNICO_ASIGNADO'].value_counts().reset_index()
        conteo.columns = ['Técnico', 'Carga']
        
        # Gráfico de Barras Interactivo
        fig = px.bar(conteo, x='Técnico', y='Carga', text='Carga', color='Técnico', title="Balance de Cargas Actual")
        st.plotly_chart(fig, use_container_width=True)
        
        # --- B. HERRAMIENTA DE REASIGNACIÓN MASIVA (TU "DESLIZAR") ---
        st.divider()
        st.markdown("### 🛠️ Reasignación Masiva")
        c_tool1, c_tool2, c_tool3 = st.columns([2, 1, 1])
        
        with c_tool1:
            # Selector de Barrios para Mover
            barrios_unicos = sorted(df[c_barrio].unique().astype(str))
            barrios_mover = st.multiselect("1. Selecciona Barrios a mover:", options=barrios_unicos)
        
        with c_tool2:
            # Selector de Destino
            destino = st.selectbox("2. Mover a:", options=["SELECCIONAR"] + TECNICOS_ACTIVOS)
            
        with c_tool3:
            st.write("") # Espacio
            st.write("") 
            if st.button("🔄 APLICAR CAMBIO"):
                if barrios_mover and destino != "SELECCIONAR":
                    # Aplicar cambio en memoria
                    mask = df[c_barrio].astype(str).isin(barrios_mover)
                    df.loc[mask, 'TECNICO_ASIGNADO'] = destino
                    st.session_state['df_simulado'] = df # Guardar cambio
                    st.rerun() # Refrescar gráficos
                else:
                    st.warning("Selecciona barrios y un destino válido.")

        # --- C. VISOR DE DISTRIBUCIÓN (QUÉ TIENE CADA UNO) ---
        st.divider()
        with st.expander("📋 Ver Detalle: ¿Qué barrios tiene cada técnico?", expanded=False):
            for tec in sorted(df['TECNICO_ASIGNADO'].unique()):
                sub_df = df[df['TECNICO_ASIGNADO'] == tec]
                barrios_tec = sub_df[c_barrio].unique()
                st.write(f"**{tec} ({len(sub_df)} órdenes):** {', '.join(map(str, barrios_tec))}")

        # --- D. EDICIÓN FINA (TABLA EDITABLE) ---
        st.markdown("### ✍️ Edición Fina (Póliza por Póliza)")
        df_editado = st.data_editor(
            df[[c_barrio, 'TECNICO_ASIGNADO', st.session_state['col_cta']]],
            key="editor_datos",
            num_rows="fixed",
            height=300
        )
        
        # --- E. BOTÓN FINAL (GENERAR ZIP) ---
        st.divider()
        if st.button("✅ CONFIRMAR Y DESCARGAR ZIP FINAL", type="primary"):
            # Actualizar DF con la tabla editada
            # Nota: Streamlit data_editor devuelve el DF modificado si se asigna así, pero por seguridad fusionamos
            # En esta implementación simple, usaremos el df_editado como fuente de verdad para esas columnas
            df.update(df_editado)
            st.session_state['df_simulado'] = df
            
            with st.spinner("Generando paquete final..."):
                # LOGICA DE GENERACIÓN (ZIP)
                df['CARPETA'] = df['TECNICO_ASIGNADO']
                
                # Leer PDF original desde el uploader (requiere seek 0 si se leyó antes, pero aquí está fresco)
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
                    # Backup PDF
                    for k, v in mapa_p.items(): zf.writestr(f"00_TODOS_PDFS/Poliza_{k}.pdf", v)
                    
                    # Excel Global
                    out_b = io.BytesIO()
                    with pd.ExcelWriter(out_b, engine='xlsxwriter') as w: df.to_excel(w, index=False)
                    zf.writestr("01_CONSOLIDADO.xlsx", out_b.getvalue())
                    
                    c_map = {'CUENTA': st.session_state['col_cta'], 'MEDIDOR': st.session_state['col_med'], 
                             'BARRIO': c_barrio, 'DIRECCION': st.session_state['col_dir'], 'CLIENTE': st.session_state['col_cli']}
                    
                    for tec in df['CARPETA'].unique():
                        if "SIN_" in tec: continue
                        safe = str(tec).replace(" ","_")
                        df_t = df[df['CARPETA'] == tec].copy()
                        # Ordenamiento
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
                            for k, v in mapa_p.items():
                                if k in c: d=v; break
                            if d:
                                f=True
                                zf.writestr(f"{safe}/POLIZAS/Poliza_{c}.pdf", d)
                                with fitz.open(stream=d, filetype="pdf") as t: m.insert_pdf(t)
                        if f: zf.writestr(f"{safe}/3_IMPRESION.pdf", m.tobytes())
                        m.close()
                
                st.session_state['zip_listo'] = zip_buffer.getvalue()
                st.success("✅ ¡Descarga Lista!")
    else:
        st.info("Carga los archivos en la Pestaña 1 para activar el simulador.")

# --- DESCARGA ---
if st.session_state['zip_listo']:
    st.sidebar.divider()
    st.sidebar.download_button("⬇️ DESCARGAR ZIP", st.session_state['zip_listo'], "Logistica_Final.zip", "application/zip", type="primary")
