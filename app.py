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
import plotly.graph_objects as go

# --- CONFIGURACIÓN VISUAL ---
st.set_page_config(page_title="Logística Exacta V114", layout="wide")

# ESTILOS MODO OSCURO (PROFESIONAL)
st.markdown("""
    <style>
    .stApp { background-color: #0E1117; color: #FAFAFA; }
    .stTabs [data-baseweb="tab-list"] { gap: 8px; }
    .stTabs [data-baseweb="tab"] { height: 50px; background-color: #262730; color: white; border-radius: 5px; border: 1px solid #41444C; }
    .stTabs [aria-selected="true"] { background-color: #004080; color: white; border: 2px solid #00A8E8; }
    div[data-testid="stDataFrame"] { background-color: #262730; border-radius: 10px; }
    </style>
""", unsafe_allow_html=True)

st.title("🎯 Logística ITA: Asignación Exacta y Balanceo")

# --- 1. CEREBRO MAESTRO (Basado en tu archivo 'tecnicos y barrios.xlsx') ---
# Prioridad: EXACTITUD.
MAESTRA_DEFAULT = {
    # TECNICO 1
    "BOYACA": "TECNICO 1", "REBOLO": "TECNICO 1", "SAN JOSE": "TECNICO 1", "SANTA MONICA": "TECNICO 1",
    "BELLARENA": "TECNICO 1", "EL PARQUE": "TECNICO 1", "LA ALBORAYA": "TECNICO 1", "EL CAMPITO": "TECNICO 1",
    "LA MAGDALENA": "TECNICO 1", "PASADENA": "TECNICO 1", "EL LIMON": "TECNICO 1", "LA CHINITA": "TECNICO 1",
    "LA LUZ": "TECNICO 1", "LAS NIEVES": "TECNICO 1", "LA UNION": "TECNICO 1", "LAS PALMAS": "TECNICO 1",
    "VILLA DEL CARMEN": "TECNICO 1", "LOS TRUPILLOS": "TECNICO 1", "SAN NICOLAS": "TECNICO 1",
    "SIMON BOLIVAR": "TECNICO 1", "TAYRONA": "TECNICO 1", "UNIVERSAL": "TECNICO 1", "EL MILAGRO": "TECNICO 1",
    
    # TECNICO 2
    "COLOMBIA": "TECNICO 2", "EL PORVENIR": "TECNICO 2", "LA FLORIDA": "TECNICO 2", "SAN FELIPE": "TECNICO 2",
    "NUEVA GRANADA": "TECNICO 2", "SAN FRANCISCO": "TECNICO 2", "VILLA SANTOS": "TECNICO 2", "RIOMAR": "TECNICO 2",
    "ALTOS DE RIOMAR": "TECNICO 2", "EL GOLF": "TECNICO 2", "SAN VICENTE": "TECNICO 2", "EL POBLADO": "TECNICO 2",
    "GRANADILLO": "TECNICO 2", "VILLA CAROLINA": "TECNICO 2", "PARAISO": "TECNICO 2", "LAS FLORES": "TECNICO 2",
    "SIAPE": "TECNICO 2", "SAN SALVADOR": "TECNICO 2", "CIA": "TECNICO 2", "AMERICA": "TECNICO 2",

    # TECNICO 3
    "EL SILENCIO": "TECNICO 3", "LA CUMBRE": "TECNICO 3", "LOS NOGALES": "TECNICO 3", "CAMPO ALEGRE": "TECNICO 3",
    "LAS ESTRELLAS": "TECNICO 3", "CIUDAD JARDIN": "TECNICO 3", "MERCEDES": "TECNICO 3", "LOS ALPES": "TECNICO 3",
    "LAS TERRAZAS": "TECNICO 3", "PORVENIR": "TECNICO 3", "LA LIBERTAD": "TECNICO 3",
    
    # TECNICO 4
    "EL PRADO": "TECNICO 4", "BOSTON": "TECNICO 4", "BARRIO ABAJO": "TECNICO 4", "MODELO": "TECNICO 4",
    "MONTECRISTO": "TECNICO 4", "BELLAVISTA": "TECNICO 4", "SANTA ANA": "TECNICO 4", "LA CONCEPCION": "TECNICO 4",
    "CENTRO": "TECNICO 4", "ROSARIO": "TECNICO 4", "BARLOVENTO": "TECNICO 4", "VILLANUEVA": "TECNICO 4",

    # TECNICO 5
    "LA PRADERA": "TECNICO 5", "LOS OLIVOS": "TECNICO 5", "LA MANGA": "TECNICO 5", "MEQUEJO": "TECNICO 5",
    "POR FIN": "TECNICO 5", "LA ESMERALDA": "TECNICO 5", "VILLA SAN PEDRO": "TECNICO 5", "LOS ANGELES": "TECNICO 5",
    "7 DE AGOSTO": "TECNICO 5", "EVARISTO SOURDIS": "TECNICO 5", "LIPAYA": "TECNICO 5",

    # TECNICO 6 (Expansión y Suroccidente segun tu archivo)
    "EL BOSQUE": "TECNICO 6", "CALIFORNIA": "TECNICO 6", "VILLAS DE LA CORDIALIDAD": "TECNICO 6", "METRO PARQUE": "TECNICO 6",
    "LA PAZ": "TECNICO 6", "LOS ROSALES": "TECNICO 6", "VILLA DEL ROSARIO": "TECNICO 6", "CARIBE VERDE": "TECNICO 6",
    "EL PUEBLO": "TECNICO 6", "EL ROMANCE": "TECNICO 6", "VILLA DE SAN PABLO": "TECNICO 6", "CIUDAD MODESTO": "TECNICO 6",
    "LAS MALVINAS": "TECNICO 6", "LA GLORIA": "TECNICO 6", "LA CORDIALIDAD": "TECNICO 6", "ALAMEDA DEL RIO": "TECNICO 6",
    
    # TECNICO 7
    "ATLANTICO": "TECNICO 7", "BOYACA SUR": "TECNICO 7", "CHIQUINQUIRA": "TECNICO 7", "SAN ROQUE": "TECNICO 7",
    "TRES AVE MARIAS": "TECNICO 7", "SAN ISIDRO": "TECNICO 7", "LOMA FRESCA": "TECNICO 7", "LUCERO": "TECNICO 7",
    
    # TECNICO 8
    "VILLA FLORENCIA": "TECNICO 8", "VILLA DEL ESTE": "TECNICO 8", "FLORENCIA": "TECNICO 8"
}

# --- 2. VECINDAD LÓGICA (Para Desbordes) ---
# Si T1 se llena (Suroriente), ¿quién está cerca? -> T7 (Murillo) o T6 (Suroccidente)
VECINOS = {
    "TECNICO 1": ["TECNICO 7", "TECNICO 6", "TECNICO 4"],
    "TECNICO 2": ["TECNICO 4", "TECNICO 3", "TECNICO 8"],
    "TECNICO 3": ["TECNICO 2", "TECNICO 5", "TECNICO 4"],
    "TECNICO 4": ["TECNICO 2", "TECNICO 7", "TECNICO 1"],
    "TECNICO 5": ["TECNICO 6", "TECNICO 3", "TECNICO 5"],
    "TECNICO 6": ["TECNICO 5", "TECNICO 1", "TECNICO 3"], # El Bosque apoya a Caribe Verde
    "TECNICO 7": ["TECNICO 1", "TECNICO 4", "TECNICO 6"],
    "TECNICO 8": ["TECNICO 2", "TECNICO 4", "TECNICO 1"]
}

# --- FUNCIONES DE LIMPIEZA AVANZADA ---
def limpiar_estricto(txt):
    """Limpieza para búsqueda exacta."""
    if not txt: return ""
    txt = str(txt).upper().strip()
    txt = "".join(c for c in unicodedata.normalize('NFD', txt) if unicodedata.category(c) != 'Mn')
    return txt

def limpiar_flexible(txt):
    """Quita palabras comunes para intentar coincidencia si la exacta falla."""
    txt = limpiar_estricto(txt)
    # Quitamos prefijos comunes en Barranquilla
    txt = re.sub(r'\b(BARRIO|URB|URBANIZACION|SECTOR|ETAPA|ZONA|BRR)\b', '', txt).strip()
    return txt

def buscar_tecnico_exacto(barrio_input, mapa_barrios):
    if not barrio_input: return "SIN_ASIGNAR"
    
    # 1. Búsqueda Exacta (Prioridad Máxima)
    b_raw = limpiar_estricto(barrio_input)
    if b_raw in mapa_barrios: return mapa_barrios[b_raw]
    
    # 2. Búsqueda Flexible (Sin 'Urb', 'Sector')
    b_flex = limpiar_flexible(barrio_input)
    if b_flex in mapa_barrios: return mapa_barrios[b_flex]
    
    # 3. Búsqueda Contenida (Solo si es muy evidente)
    # Ej: "EL SILENCIO SECTOR 2" contiene "EL SILENCIO"
    for k_maestro, tecnico in mapa_barrios.items():
        if k_maestro == b_flex: return tecnico # Match inverso
        # Cuidado con matches cortos. Solo si la clave maestra tiene longitud > 4
        if len(k_maestro) > 4 and k_maestro in b_raw: 
            return tecnico
            
    return "SIN_ASIGNAR"

def cargar_cerebro_excel(file):
    mapa = {} # Empezamos vacío para dar prioridad al Excel subido
    try:
        if file.name.endswith('.csv'): df = pd.read_csv(file, sep=None, engine='python')
        else: df = pd.read_excel(file)
        
        # Detectar columnas
        col_barrio = df.columns[0] # Asumimos 1ra columna
        col_tec = df.columns[1]    # Asumimos 2da columna
        
        for _, row in df.iterrows():
            b = limpiar_estricto(str(row[col_barrio]))
            t = str(row[col_tec]).upper().strip()
            mapa[b] = t
    except Exception as e:
        st.error(f"Error en archivo maestro: {e}")
        return MAESTRA_DEFAULT
    return mapa

# --- ALGORITMO ORDENAMIENTO JS ADAPTADO ---
VALOR_SUFIJOS = {'A': 0.1, 'B': 0.2, 'C': 0.3, 'D': 0.4, 'BIS': 0.05}
def calcular_peso_js(txt):
    clean = limpiar_estricto(txt)
    # Penalizar SUR
    penalidad = 5000 if "SUR" in clean else 0
    # Extraer primer número
    nums = re.findall(r'(\d+)', clean)
    ref = int(nums[0]) if nums else 0
    
    # Logica ZigZag: Calles Bajan, Carreras Suben (Aprox)
    if "CL" in clean or "CALLE" in clean:
        peso = (110 - ref) * 1000
    else:
        peso = ref * 1000
        
    secundario = int(nums[1]) if len(nums) > 1 else 0
    return peso + secundario + penalidad

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

# --- SESSION ---
if 'mapa_actual' not in st.session_state: st.session_state['mapa_actual'] = MAESTRA_DEFAULT
if 'zip_listo' not in st.session_state: st.session_state['zip_listo'] = None

# --- UI TABS ---
tab1, tab2, tab3 = st.tabs(["🚀 Operación Diaria", "📊 Matriz de Balanceo", "⚙️ Configuración & Barrios"])

# --- TAB 3: CONFIG ---
with tab3:
    st.header("Base de Datos de Barrios")
    st.info("Para máxima exactitud, sube tu archivo 'tecnicos y barrios.xlsx' aquí siempre.")
    maestro_file = st.file_uploader("Actualizar Maestro (Excel)", type=["xlsx", "csv"])
    if maestro_file:
        st.session_state['mapa_actual'] = cargar_cerebro_excel(maestro_file)
        st.success(f"✅ ¡Cerebro actualizado con {len(st.session_state['mapa_actual'])} barrios exactos!")
    
    with st.expander("Ver lista de barrios cargada actualmente"):
        df_m = pd.DataFrame(list(st.session_state['mapa_actual'].items()), columns=['Barrio', 'Técnico'])
        st.dataframe(df_m, use_container_width=True)

# --- TAB 1: OPERACIÓN ---
with tab1:
    c1, c2 = st.columns(2)
    with c1: pdf_in = st.file_uploader("1. PDF Pólizas", type="pdf")
    with c2: 
        excel_in = st.file_uploader("2. Base Diaria", type=["xlsx", "csv"])
        TOPE = st.number_input("Tope Máximo por Técnico", value=35)

    if excel_in:
        try:
            if excel_in.name.endswith('.csv'): df = pd.read_csv(excel_in, sep=None, engine='python', encoding='utf-8-sig')
            else: df = pd.read_excel(excel_in)
            df.columns = [limpiar_estricto(c) for c in df.columns]

            def find(k):
                for x in k:
                    for c in df.columns: 
                        if x in c: return c
                return None
            
            c_barrio = find(['BARRIO', 'SECTOR'])
            c_cta = find(['CUENTA', 'POLIZA', 'NRO'])
            c_dir = find(['DIRECCION', 'DIR'])

            if c_barrio and c_cta:
                # 1. ASIGNACIÓN INICIAL (IDEAL)
                df['TECNICO_IDEAL'] = df[c_barrio].apply(lambda x: buscar_tecnico_exacto(str(x), st.session_state['mapa_actual']))
                
                # Resumen Inicial
                st.divider()
                st.subheader("1️⃣ Pre-Asignación (Sin Balanceo)")
                col_m1, col_m2 = st.columns([1, 2])
                with col_m1:
                    conteo_init = df['TECNICO_IDEAL'].value_counts().reset_index()
                    conteo_init.columns = ['Técnico', 'Carga Inicial']
                    st.dataframe(conteo_init, use_container_width=True, height=250)
                with col_m2:
                    # Alerta de Sin Asignar
                    sin_asig = df[df['TECNICO_IDEAL'] == "SIN_ASIGNAR"]
                    if not sin_asig.empty:
                        st.error(f"⚠️ ATENCIÓN: Hay {len(sin_asig)} órdenes con barrios desconocidos.")
                        st.dataframe(sin_asig[[c_barrio, c_dir]].drop_duplicates(subset=[c_barrio]), height=200)
                    else:
                        st.success("✅ Todos los barrios reconocidos correctamente.")

                # BOTÓN PROCESAR
                if pdf_in:
                    if st.button("🚀 BALANCEAR CARGAS Y GENERAR ZIP", type="primary"):
                        with st.spinner("Aplicando lógica de desbordes..."):
                            # 2. ALGORITMO DE BALANCEO
                            # Ordenamos para llenar primero los barrios más "importantes" o alfabéticamente
                            df = df.sort_values(by=['TECNICO_IDEAL', c_barrio])
                            
                            conteo_real = {}
                            asignacion_final = []
                            log_cambios = [] # Para el reporte
                            
                            for _, row in df.iterrows():
                                ideal = row['TECNICO_IDEAL']
                                bar = row[c_barrio]
                                final = "SIN_ASIGNAR"
                                
                                if "SIN_ASIGNAR" in ideal:
                                    final = "SIN_ASIGNAR"
                                else:
                                    if ideal not in conteo_real: conteo_real[ideal] = 0
                                    
                                    if conteo_real[ideal] < TOPE:
                                        final = ideal
                                        conteo_real[ideal] += 1
                                    else:
                                        # DESBORDE
                                        vecinos = VECINOS.get(ideal, [])
                                        encontrado = False
                                        for v in vecinos:
                                            if v not in conteo_real: conteo_real[v] = 0
                                            if conteo_real[v] < TOPE:
                                                final = f"{v} (APOYO)"
                                                conteo_real[v] += 1
                                                encontrado = True
                                                log_cambios.append({"Cuenta": row[c_cta], "Barrio": bar, "Original": ideal, "Nuevo": v})
                                                break
                                        if not encontrado:
                                            final = f"{ideal} (EXTRA)" # Nadie tiene cupo, se sobrecarga
                                
                                asignacion_final.append(final)
                            
                            df['TECNICO_REAL'] = asignacion_final
                            df['CARPETA'] = df['TECNICO_REAL'].apply(lambda x: x.split(" (")[0])
                            
                            # Guardar Log de cambios para mostrar en Tab 2
                            st.session_state['log_cambios'] = pd.DataFrame(log_cambios)
                            st.session_state['conteo_final'] = pd.DataFrame(list(conteo_real.items()), columns=['Técnico', 'Carga Final'])

                            # 3. GENERAR ZIP
                            # (Lógica estándar de ZIP)
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
                                out_base = io.BytesIO()
                                with pd.ExcelWriter(out_base, engine='xlsxwriter') as w: df.to_excel(w, index=False)
                                zf.writestr("0_CONSOLIDADO.xlsx", out_base.getvalue())
                                
                                c_map = {'CUENTA': c_cta, 'MEDIDOR': find(['MEDIDOR']), 'BARRIO': c_barrio, 'DIRECCION': c_dir, 'CLIENTE': find(['CLIENTE'])}
                                
                                for tec in df['CARPETA'].unique():
                                    if "SIN_" in tec: continue
                                    safe = str(tec).replace(" ","_")
                                    df_t = df[df['CARPETA'] == tec].copy()
                                    if c_dir:
                                        df_t['P'] = df_t[c_dir].astype(str).apply(calcular_peso_js)
                                        df_t = df_t.sort_values('P')
                                    
                                    pdf_h = crear_pdf(df_t, tec, c_map)
                                    zf.writestr(f"{safe}/1_LISTADO.pdf", pdf_h)
                                    
                                    out_t = io.BytesIO()
                                    with pd.ExcelWriter(out_t, engine='xlsxwriter') as w: df_t.to_excel(w, index=False)
                                    zf.writestr(f"{safe}/2_DIGITAL.xlsx", out_t.getvalue())
                                    
                                    m = fitz.open()
                                    f = False
                                    for _, r in df_t.iterrows():
                                        c = str(r[c_cta])
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
                            st.success("✅ ¡Proceso Terminado!")

            else: st.warning("Sube los archivos para comenzar.")
        except Exception as e: st.error(f"Error: {e}")

# --- TAB 2: MATRIZ DE BALANCEO ---
with tab2:
    st.header("📊 Resultado del Balanceo de Cargas")
    if st.session_state['zip_listo']:
        c1, c2 = st.columns(2)
        with c1:
            st.subheader("Carga Final por Técnico")
            # Gráfico de barras simple
            if 'conteo_final' in st.session_state:
                fig = px.bar(st.session_state['conteo_final'], x='Técnico', y='Carga Final', text='Carga Final', color='Carga Final')
                # Línea de tope
                fig.add_hline(y=TOPE, line_dash="dash", line_color="red", annotation_text="Tope Máximo")
                st.plotly_chart(fig, use_container_width=True)
        
        with c2:
            st.subheader("📋 Log de Reasignaciones (Desbordes)")
            if 'log_cambios' in st.session_state and not st.session_state['log_cambios'].empty:
                st.dataframe(st.session_state['log_cambios'], use_container_width=True)
                st.caption("Estos son los barrios que se movieron porque el técnico titular estaba lleno.")
            else:
                st.success("No hubo desbordes. Todos los técnicos estaban dentro del cupo.")
    else:
        st.info("Procesa el archivo en la Pestaña 1 para ver los resultados aquí.")

# --- DESCARGA ---
if st.session_state['zip_listo']:
    st.sidebar.divider()
    st.sidebar.download_button("⬇️ BAJAR ZIP FINAL", st.session_state['zip_listo'], "Logistica_Exacta.zip", "application/zip", type="primary")
